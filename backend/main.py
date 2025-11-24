"""Main FastAPI application."""
from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
import io

from backend.config import settings
from backend.database import init_db, get_db, SessionLocal
from backend.models import Relic, User
from backend.schemas import (
    RelicCreate, RelicResponse, RelicListResponse, RelicEdit,
    RelicFork, DiffResponse, UserCreate, UserResponse
)
from backend.storage import storage_service
from backend.utils import generate_relic_id, parse_expiry_string, is_expired, hash_password
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


# ==================== Helper Functions ====================

def generate_unique_relic_id(db: Session, max_retries: int = 5) -> str:
    """
    Generate a unique relic ID with collision handling.

    Attempts to generate a unique ID by checking the database for existing IDs.
    With 128-bit entropy (32 hex chars), collisions are astronomically rare,
    but this provides defensive handling just in case.

    Args:
        db: Database session for checking existing IDs
        max_retries: Maximum number of generation attempts (default: 5)

    Returns:
        A unique relic ID guaranteed not to exist in the database

    Raises:
        HTTPException: If unable to generate unique ID after max_retries
    """
    for attempt in range(max_retries):
        relic_id = generate_relic_id()

        # Check if ID already exists
        existing = db.query(Relic).filter(Relic.id == relic_id).first()
        if not existing:
            return relic_id

    # This should virtually never happen with 128-bit IDs
    raise HTTPException(
        status_code=500,
        detail="Failed to generate unique relic ID after multiple attempts"
    )


# ==================== Relic Operations ====================
@app.post("/api/v1/relics", response_model=dict)
async def create_relic(
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    language_hint: Optional[str] = Form(None),
    access_level: str = Form("public"),
    expires_in: Optional[str] = Form(None),
    tags: Optional[List[str]] = Form(None),
    user_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Create a new relic.

    Accepts either file upload or raw content in body.
    """
    # Validate access_level
    if access_level not in ("public", "private"):
        raise HTTPException(
            status_code=400,
            detail="Invalid access_level. Must be 'public' or 'private'."
        )

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

        # Generate unique relic ID with collision handling
        relic_id = generate_unique_relic_id(db)

        # Process content
        metadata, preview = await process_content(content, content_type, language_hint)

        # Upload to storage
        s3_key = f"relics/{relic_id}"
        await storage_service.upload(s3_key, content, content_type)

        # Parse expiry
        expires_at = parse_expiry_string(expires_in)

        # Create relic record
        relic = Relic(
            id=relic_id,
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

        db.add(relic)
        db.commit()
        db.refresh(relic)

        return {
            "id": relic.id,
            "url": f"/{relic.id}",
            "created_at": relic.created_at,
            "version": relic.version_number,
            "size_bytes": relic.size_bytes
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/relics/{relic_id}", response_model=RelicResponse)
async def get_relic(relic_id: str, password: Optional[str] = None, db: Session = Depends(get_db)):
    """Get relic metadata."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if relic.deleted_at:
        raise HTTPException(status_code=404, detail="Relic not found")
    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")

    # Check optional password protection (independent of access_level)
    # access_level only affects listing in recents:
    # - public: listed and discoverable
    # - private: not listed (URL serves as access token)
    if relic.password_hash:
        if not password:
            raise HTTPException(status_code=403, detail="This relic requires a password")
        if hash_password(password) != relic.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")

    # Increment access count
    relic.access_count += 1
    db.commit()

    return relic

@app.get("/{relic_id}/raw")
async def get_relic_raw(relic_id: str, db: Session = Depends(get_db)):
    """Get raw relic content."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if relic.deleted_at:
        raise HTTPException(status_code=404, detail="Relic not found")

    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")    
    try:
        content = await storage_service.download(relic.s3_key)
        return StreamingResponse(
            iter([content]),
            media_type=relic.content_type,
            headers={"Content-Disposition": f"inline; filename={relic.name or relic.id}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/relics/{relic_id}/edit", response_model=dict)
async def edit_relic(
    relic_id: str,
    file: UploadFile = File(...),
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Edit a relic (create new version).

    Creates a new relic with parent_id pointing to the original.
    """
    parent = db.query(Relic).filter(Relic.id == relic_id).first()

    if not parent:
        raise HTTPException(status_code=404, detail="Relic` not found")

    if parent.deleted_at:
        raise HTTPException(status_code=404, detail="Relic not found")

    # TODO: Check ownership

    try:
        content = await file.read()

        # Generate unique new ID with collision handling
        new_id = generate_unique_relic_id(db)

        # Process content
        metadata, preview = await process_content(content, parent.content_type, parent.language_hint)

        # Upload to storage
        s3_key = f"relics/{new_id}"
        await storage_service.upload(s3_key, content, parent.content_type)

        # Create new relic as child
        new_relic = Relic(
            id=new_id,
            user_id=user_id,
            name=name or parent.name,
            content_type=parent.content_type,
            language_hint=parent.language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            parent_id=relic_id,
            root_id=parent.root_id or parent.id,
            version_number=parent.version_number + 1,
            access_level=parent.access_level,
            expires_at=parent.expires_at,
            processing_metadata={"processed_metadata": metadata, "preview": preview}
        )

        db.add(new_relic)
        db.commit()
        db.refresh(new_relic)

        return {
            "id": new_relic.id,
            "url": f"/{new_relic.id}",
            "parent_id": new_relic.parent_id,
            "version": new_relic.version_number,
            "created_at": new_relic.created_at
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/relics/{relic_id}/fork", response_model=dict)
async def fork_relic(
    relic_id: str,
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Fork a relic (create new independent lineage).

    Creates a new relic with fork_of pointing to the original.
    """
    original = db.query(Relic).filter(Relic.id == relic_id).first()

    if not original:
        raise HTTPException(status_code=404, detail="Relic not found")

    if original.deleted_at:
        raise HTTPException(status_code=404, detail="Relic not found")

    try:
        # If no new content provided, fork with same content
        if file:
            content = await file.read()
            content_type = file.content_type or original.content_type
        else:
            content = await storage_service.download(original.s3_key)
            content_type = original.content_type

        # Generate unique new ID with collision handling
        new_id = generate_unique_relic_id(db)

        # Process content
        metadata, preview = await process_content(content, content_type, original.language_hint)

        # Upload to storage
        s3_key = f"relics/{new_id}"
        await storage_service.upload(s3_key, content, content_type)

        # Create fork with version 1
        fork = Relic(
            id=new_id,
            user_id=user_id,
            name=name or original.name,
            content_type=content_type,
            language_hint=original.language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            fork_of=relic_id,
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


@app.delete("/api/v1/relics/{relic_id}")
async def delete_relic(relic_id: str, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Delete a relic (soft delete).

    Only owner can delete.
    """
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # TODO: Check user ownership
    if relic.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this relic")

    relic.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "Relic deleted successfully"}

# ==================== Version & Lineage ====================

@app.get("/api/v1/relics/{relic_id}/history", response_model=dict)
async def get_relic_history(relic_id: str, db: Session = Depends(get_db)):
    """Get full version history of a relic."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    root_id = relic.root_id or relic.id
    versions = []

    # Walk the chain
    current = relic
    while current:
        versions.insert(0, {
            "id": current.id,
            "version": current.version_number,
            "created_at": current.created_at,
            "size_bytes": current.size_bytes,
            "name": current.name
        })
        if current.parent_id:
            current = db.query(Relic).filter(Relic.id == current.parent_id).first()
        else:
            break

    return {
        "root_id": root_id,
        "current_id": relic.id,
        "current_version": relic.version_number,
        "versions": versions
    }


@app.get("/api/v1/relics/{relic_id}/parent")
async def get_parent(relic_id: str, db: Session = Depends(get_db)):
    """Get parent relic of a version."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not relic.parent_id:
        raise HTTPException(status_code=404, detail="No parent version")

    parent = db.query(Relic).filter(Relic.id == relic.parent_id).first()
    return parent


@app.get("/api/v1/relics/{relic_id}/children")
async def get_children(relic_id: str, db: Session = Depends(get_db)):
    """Get child relics of a version."""
    children = db.query(Relic).filter(Relic.parent_id == relic_id, Relic.deleted_at == None).all()

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
async def diff_relics(from_id: str, to_id: str, db: Session = Depends(get_db)):
    """Compare two relics."""
    from_relic = db.query(Relic).filter(Relic.id == from_id).first()
    to_relic = db.query(Relic).filter(Relic.id == to_id).first()

    if not from_relic or not to_relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    try:
        from_content = await storage_service.download(from_relic.s3_key)
        to_content = await storage_service.download(to_relic.s3_key)
        # For text content, generate diff
        if "text" in from_relic.content_type or "text" in to_relic.content_type:
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
                "from_size": from_relic.size_bytes,
                "to_size": to_relic.size_bytes
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/relics/{relic_id}/diff")
async def diff_with_parent(relic_id: str, db: Session = Depends(get_db)):
    """Compare relic with its parent."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not relic.parent_id:
        raise HTTPException(status_code=404, detail="No parent version to compare")

    return await diff_relics(relic.parent_id, relic_id, db)

# ==================== Listing & Search ====================

@app.get("/api/v1/relics", response_model=RelicListResponse)
async def list_relics(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List recent relics."""
    query = db.query(Relic).filter(
        Relic.deleted_at == None,
        Relic.access_level == "public"
    ).order_by(Relic.created_at.desc())

    total = query.count()
    relics = query.offset(offset).limit(limit).all()

    return {
        "relics": relics,
        "total": total
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
