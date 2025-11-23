"""Main FastAPI application."""
from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
import io

from backend.config import settings
from backend.database import init_db, get_db, SessionLocal
from backend.models import Paste, User
from backend.schemas import (
    PasteCreate, PasteResponse, PasteListResponse, PasteEdit,
    PasteFork, DiffResponse, UserCreate, UserResponse
)
from backend.storage import storage_service
from backend.utils import generate_paste_id, parse_expiry_string, is_expired, hash_password
from backend.processors import process_content


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and storage on startup."""
    init_db()
    storage_service.ensure_bucket()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ==================== Paste Operations ====================

@app.post("/api/v1/pastes", response_model=dict)
async def create_paste(
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = None,
    content_type: Optional[str] = None,
    language_hint: Optional[str] = None,
    access_level: str = "public",
    expires_in: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new paste.

    Accepts either file upload or raw content in body.
    """
    try:
        # Read file content
        if file:
            content = await file.read()
            if not content_type:
                content_type = file.content_type or "application/octet-stream"
            if not name:
                name = file.filename
        else:
            raise HTTPException(status_code=400, detail="No content provided")

        # Check size limit
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large")

        # Generate paste ID
        paste_id = generate_paste_id()

        # Process content
        metadata, preview = await process_content(content, content_type, language_hint)

        # Upload to storage
        s3_key = f"pastes/{paste_id}"
        await storage_service.upload(s3_key, content, content_type)

        # Parse expiry
        expires_at = parse_expiry_string(expires_in)

        # Create paste record
        paste = Paste(
            id=paste_id,
            user_id=user_id,
            name=name,
            content_type=content_type,
            language_hint=language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            access_level=access_level,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            processing_metadata={"processed_metadata": metadata, "preview": preview}
        )

        db.add(paste)
        db.commit()
        db.refresh(paste)

        return {
            "id": paste.id,
            "url": f"/{paste.id}",
            "created_at": paste.created_at,
            "version": paste.version_number,
            "size_bytes": paste.size_bytes
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/pastes/{paste_id}", response_model=PasteResponse)
async def get_paste(paste_id: str, password: Optional[str] = None, db: Session = Depends(get_db)):
    """Get paste metadata."""
    paste = db.query(Paste).filter(Paste.id == paste_id).first()

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    if paste.deleted_at:
        raise HTTPException(status_code=404, detail="Paste not found")

    if is_expired(paste.expires_at):
        raise HTTPException(status_code=410, detail="Paste has expired")

    if paste.access_level == "private" and not password:  # TODO: Check user ownership
        raise HTTPException(status_code=403, detail="Access denied")

    if paste.password_hash and password:
        if hash_password(password) != paste.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")

    # Increment access count
    paste.access_count += 1
    db.commit()

    return paste


@app.get("/{paste_id}/raw")
async def get_paste_raw(paste_id: str, db: Session = Depends(get_db)):
    """Get raw paste content."""
    paste = db.query(Paste).filter(Paste.id == paste_id).first()

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    if paste.deleted_at:
        raise HTTPException(status_code=404, detail="Paste not found")

    if is_expired(paste.expires_at):
        raise HTTPException(status_code=410, detail="Paste has expired")

    try:
        content = await storage_service.download(paste.s3_key)
        return StreamingResponse(
            iter([content]),
            media_type=paste.content_type,
            headers={"Content-Disposition": f"inline; filename={paste.name or paste.id}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/pastes/{paste_id}/edit", response_model=dict)
async def edit_paste(
    paste_id: str,
    file: UploadFile = File(...),
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Edit a paste (create new version).

    Creates a new paste with parent_id pointing to the original.
    """
    parent = db.query(Paste).filter(Paste.id == paste_id).first()

    if not parent:
        raise HTTPException(status_code=404, detail="Paste not found")

    if parent.deleted_at:
        raise HTTPException(status_code=404, detail="Paste not found")

    # TODO: Check ownership

    try:
        content = await file.read()

        # Generate new ID
        new_id = generate_paste_id()

        # Process content
        metadata, preview = await process_content(content, parent.content_type, parent.language_hint)

        # Upload to storage
        s3_key = f"pastes/{new_id}"
        await storage_service.upload(s3_key, content, parent.content_type)

        # Create new paste as child
        new_paste = Paste(
            id=new_id,
            user_id=user_id,
            name=name or parent.name,
            content_type=parent.content_type,
            language_hint=parent.language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            parent_id=paste_id,
            root_id=parent.root_id or parent.id,
            version_number=parent.version_number + 1,
            access_level=parent.access_level,
            expires_at=parent.expires_at,
            processing_metadata={"processed_metadata": metadata, "preview": preview}
        )

        db.add(new_paste)
        db.commit()
        db.refresh(new_paste)

        return {
            "id": new_paste.id,
            "url": f"/{new_paste.id}",
            "parent_id": new_paste.parent_id,
            "version": new_paste.version_number,
            "created_at": new_paste.created_at
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/pastes/{paste_id}/fork", response_model=dict)
async def fork_paste(
    paste_id: str,
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Fork a paste (create new independent lineage).

    Creates a new paste with fork_of pointing to the original.
    """
    original = db.query(Paste).filter(Paste.id == paste_id).first()

    if not original:
        raise HTTPException(status_code=404, detail="Paste not found")

    if original.deleted_at:
        raise HTTPException(status_code=404, detail="Paste not found")

    try:
        # If no new content provided, fork with same content
        if file:
            content = await file.read()
            content_type = file.content_type or original.content_type
        else:
            content = await storage_service.download(original.s3_key)
            content_type = original.content_type

        # Generate new ID
        new_id = generate_paste_id()

        # Process content
        metadata, preview = await process_content(content, content_type, original.language_hint)

        # Upload to storage
        s3_key = f"pastes/{new_id}"
        await storage_service.upload(s3_key, content, content_type)

        # Create fork with version 1
        fork = Paste(
            id=new_id,
            user_id=user_id,
            name=name or original.name,
            content_type=content_type,
            language_hint=original.language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            fork_of=paste_id,
            root_id=new_id,  # Fork creates new root
            version_number=1,  # Reset to version 1
            access_level=original.access_level,
            processing_metadata={"processed_metadata": metadata, "preview": preview}
        )

        db.add(fork)
        db.commit()
        db.refresh(fork)

        return {
            "id": fork.id,
            "url": f"/{fork.id}",
            "fork_of": fork.fork_of,
            "version": fork.version_number,
            "created_at": fork.created_at
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/pastes/{paste_id}")
async def delete_paste(paste_id: str, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Delete a paste (soft delete).

    Only owner can delete.
    """
    paste = db.query(Paste).filter(Paste.id == paste_id).first()

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    # TODO: Check user ownership
    if paste.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this paste")

    paste.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "Paste deleted successfully"}


# ==================== Version & Lineage ====================

@app.get("/api/v1/pastes/{paste_id}/history", response_model=dict)
async def get_paste_history(paste_id: str, db: Session = Depends(get_db)):
    """Get full version history of a paste."""
    paste = db.query(Paste).filter(Paste.id == paste_id).first()

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    root_id = paste.root_id or paste.id
    versions = []

    # Walk the chain
    current = paste
    while current:
        versions.insert(0, {
            "id": current.id,
            "version": current.version_number,
            "created_at": current.created_at,
            "size_bytes": current.size_bytes,
            "name": current.name
        })
        if current.parent_id:
            current = db.query(Paste).filter(Paste.id == current.parent_id).first()
        else:
            break

    return {
        "root_id": root_id,
        "current_id": paste.id,
        "current_version": paste.version_number,
        "versions": versions
    }


@app.get("/api/v1/pastes/{paste_id}/parent")
async def get_parent(paste_id: str, db: Session = Depends(get_db)):
    """Get parent paste of a version."""
    paste = db.query(Paste).filter(Paste.id == paste_id).first()

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    if not paste.parent_id:
        raise HTTPException(status_code=404, detail="No parent version")

    parent = db.query(Paste).filter(Paste.id == paste.parent_id).first()
    return parent


@app.get("/api/v1/pastes/{paste_id}/children")
async def get_children(paste_id: str, db: Session = Depends(get_db)):
    """Get child pastes of a version."""
    children = db.query(Paste).filter(Paste.parent_id == paste_id, Paste.deleted_at == None).all()

    return {
        "children": [
            {
                "id": child.id,
                "version": child.version_number,
                "created_at": child.created_at,
                "name": child.name
            }
            for child in children
        ]
    }


# ==================== Diff ====================

@app.get("/api/v1/diff")
async def diff_pastes(from_id: str, to_id: str, db: Session = Depends(get_db)):
    """Compare two pastes."""
    from_paste = db.query(Paste).filter(Paste.id == from_id).first()
    to_paste = db.query(Paste).filter(Paste.id == to_id).first()

    if not from_paste or not to_paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    try:
        from_content = await storage_service.download(from_paste.s3_key)
        to_content = await storage_service.download(to_paste.s3_key)

        # For text content, generate diff
        if "text" in from_paste.content_type or "text" in to_paste.content_type:
            import difflib

            from_lines = from_content.decode('utf-8', errors='replace').split('\n')
            to_lines = to_content.decode('utf-8', errors='replace').split('\n')

            diff = '\n'.join(difflib.unified_diff(from_lines, to_lines, lineterm=''))
            additions = sum(1 for line in diff.split('\n') if line.startswith('+'))
            deletions = sum(1 for line in diff.split('\n') if line.startswith('-'))

            return {
                "from_id": from_id,
                "to_id": to_id,
                "diff": diff,
                "additions": additions,
                "deletions": deletions
            }
        else:
            # For binary, just compare metadata
            return {
                "from_id": from_id,
                "to_id": to_id,
                "diff": "Binary content - metadata comparison",
                "additions": 0,
                "deletions": 0,
                "from_size": from_paste.size_bytes,
                "to_size": to_paste.size_bytes
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/pastes/{paste_id}/diff")
async def diff_with_parent(paste_id: str, db: Session = Depends(get_db)):
    """Compare paste with its parent."""
    paste = db.query(Paste).filter(Paste.id == paste_id).first()

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    if not paste.parent_id:
        raise HTTPException(status_code=404, detail="No parent version to compare")

    return await diff_pastes(paste.parent_id, paste_id, db)


# ==================== Listing & Search ====================

@app.get("/api/v1/pastes", response_model=PasteListResponse)
async def list_pastes(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List recent pastes."""
    query = db.query(Paste).filter(
        Paste.deleted_at == None,
        Paste.access_level == "public"
    ).order_by(Paste.created_at.desc())

    total = query.count()
    pastes = query.offset(offset).limit(limit).all()

    return {
        "pastes": pastes,
        "total": total
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
