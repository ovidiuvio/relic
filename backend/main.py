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
from backend.models import Relic, ClientKey, ClientBookmark
from backend.schemas import (
    RelicCreate, RelicResponse, RelicListResponse,
    RelicFork
)
from backend.storage import storage_service
from backend.utils import generate_relic_id, parse_expiry_string, is_expired, hash_password, generate_client_id
from backend.backup import start_backup_scheduler, shutdown_backup_scheduler, perform_backup


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
    """Initialize database, storage, and backup scheduler on startup."""
    init_db()
    storage_service.ensure_bucket()

    # Start backup scheduler
    if settings.BACKUP_ENABLED:
        await start_backup_scheduler()

        # Create backup on startup
        if settings.BACKUP_ON_STARTUP:
            import logging
            logger = logging.getLogger('relic.main')
            logger.info("Creating startup backup...")
            await perform_backup(backup_type='startup')


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if settings.BACKUP_ENABLED:
        # Create backup on shutdown
        if settings.BACKUP_ON_SHUTDOWN:
            import logging
            logger = logging.getLogger('relic.main')
            logger.info("Creating shutdown backup...")
            await perform_backup(backup_type='shutdown')

        # Stop scheduler
        await shutdown_backup_scheduler()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/v1/client/register", response_model=dict)
async def register_client(request: Request, db: Session = Depends(get_db)):
    """
    Register a new client key.

    If the client key already exists, returns the existing client.
    If not, creates a new client record.
    """
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        raise HTTPException(status_code=400, detail="X-Client-Key header required")

    # Check if client already exists
    existing_client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    if existing_client:
        return {
            "client_id": existing_client.id,
            "created_at": existing_client.created_at,
            "relic_count": existing_client.relic_count,
            "message": "Client already registered"
        }

    # Create new client
    client = ClientKey(
        id=x_client_key,
        created_at=datetime.utcnow()
    )
    db.add(client)
    db.commit()

    return {
        "client_id": client.id,
        "created_at": client.created_at,
        "relic_count": 0,
        "message": "Client registered successfully"
    }


@app.get("/api/v1/client/relics", response_model=dict)
async def get_client_relics(request: Request, db: Session = Depends(get_db)):
    """
    Get all relics owned by this client.

    Requires valid X-Client-Key header.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    relics = db.query(Relic).filter(
        Relic.client_id == client.id
    ).order_by(Relic.created_at.desc()).all()

    return {
        "client_id": client.id,
        "relic_count": len(relics),
        "relics": [
            {
                "id": relic.id,
                "name": relic.name,
                "content_type": relic.content_type,
                "size_bytes": relic.size_bytes,
                "created_at": relic.created_at,
                "access_level": relic.access_level
            }
            for relic in relics
        ]
    }


# ==================== Client Key Functions ====================

def get_client_key(request: Request, db: Session) -> Optional[ClientKey]:
    """Extract and validate client key from request headers."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None

    client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    return client


def get_or_create_client_key(request: Request, db: Session) -> Optional[ClientKey]:
    """Get existing client or create new one if key provided."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None

    # Try to get existing client
    client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    if client:
        return client

    # Create new client if it doesn't exist
    client = ClientKey(
        id=x_client_key,
        created_at=datetime.utcnow()
    )
    db.add(client)
    db.commit()
    return client


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
    request: Request,
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    language_hint: Optional[str] = Form(None),
    access_level: str = Form("public"),
    expires_in: Optional[str] = Form(None),
    tags: Optional[List[str]] = Form(None),
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

    # Get or create client
    client = get_or_create_client_key(request, db)

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

        # Upload to storage
        s3_key = f"relics/{relic_id}"
        await storage_service.upload(s3_key, content, content_type)

        # Parse expiry
        expires_at = parse_expiry_string(expires_in)

        # Create relic record
        relic = Relic(
            id=relic_id,
            client_id=client.id if client else None,
            name=name,
            content_type=content_type,
            language_hint=language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            access_level=access_level,
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )

        # Update client relic count
        if client:
            client.relic_count += 1

        db.add(relic)
        db.commit()
        db.refresh(relic)

        return {
            "id": relic.id,
            "url": f"/{relic.id}",
            "created_at": relic.created_at,
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

    if not relic:
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

    if not relic:
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



@app.post("/api/v1/relics/{relic_id}/fork", response_model=dict)
async def fork_relic(
    relic_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    access_level: Optional[str] = Form(None),
    expires_in: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Fork a relic (create new independent lineage).

    Creates a new relic with fork_of pointing to the original.
    Public endpoint - anyone can fork. Fork belongs to forking client if key provided.
    """
    # Validate access_level
    if access_level and access_level not in ['public', 'private']:
        raise HTTPException(status_code=400, detail="Invalid access_level. Must be 'public' or 'private'")

    # Get client (optional - fork is public)
    client = get_or_create_client_key(request, db)

    original = db.query(Relic).filter(Relic.id == relic_id).first()

    if not original:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not original:
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

        # Upload to storage
        s3_key = f"relics/{new_id}"
        await storage_service.upload(s3_key, content, content_type)

        # Calculate expiry date if provided
        expires_at = None
        if expires_in and expires_in != 'never':
            expires_at = parse_expiry_string(expires_in)

        # Create fork
        fork = Relic(
            id=new_id,
            client_id=client.id if client else None,  # Fork belongs to client if provided
            name=name or original.name,
            content_type=content_type,
            language_hint=original.language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            fork_of=relic_id,
            access_level=access_level or original.access_level,
            expires_at=expires_at
        )

        # Update client relic count if client exists
        if client:
            client.relic_count += 1

        db.add(fork)
        db.commit()
        db.refresh(fork)

        return {
            "id": fork.id,
            "url": f"/{fork.id}",
            "fork_of": fork.fork_of,
            "created_at": fork.created_at
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/relics/{relic_id}")
async def delete_relic(relic_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Delete a relic (hard delete).

    Only client owner can delete.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Client key required")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Check client ownership
    if relic.client_id != client.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this relic")

    # Delete file from S3 storage
    try:
        await storage_service.delete(relic.s3_key)
    except Exception as e:
        # Log error but don't fail the delete operation
        print(f"Failed to delete file from S3: {e}")

    # Hard delete in database
    db.delete(relic)

    # Update client relic count
    if client.relic_count > 0:
        client.relic_count -= 1

    db.commit()

    return {"message": "Relic deleted successfully"}


# ==================== Listing & Search ====================

@app.get("/api/v1/relics", response_model=RelicListResponse)
async def list_relics(
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """List the 1000 most recent public relics."""
    relics = db.query(Relic).filter(
        Relic.access_level == "public"
    ).order_by(Relic.created_at.desc()).limit(limit).all()

    return {
        "relics": relics
    }


# ==================== Bookmark Operations ====================

@app.post("/api/v1/bookmarks", response_model=dict)
async def add_bookmark(
    request: Request,
    relic_id: str,
    db: Session = Depends(get_db)
):
    """
    Add a bookmark for the authenticated client.

    Requires valid X-Client-Key header.
    Returns bookmark details or error if already bookmarked.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    # Verify relic exists and is not deleted
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Check if already bookmarked
    existing = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Relic already bookmarked")

    # Create bookmark
    bookmark = ClientBookmark(
        client_id=client.id,
        relic_id=relic_id,
        created_at=datetime.utcnow()
    )

    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    return {
        "id": bookmark.id,
        "relic_id": bookmark.relic_id,
        "created_at": bookmark.created_at,
        "message": "Bookmark added successfully"
    }


@app.delete("/api/v1/bookmarks/{relic_id}")
async def remove_bookmark(
    relic_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Remove a bookmark for the authenticated client.

    Requires valid X-Client-Key header.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    # Find bookmark
    bookmark = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark)
    db.commit()

    return {"message": "Bookmark removed successfully"}


@app.get("/api/v1/bookmarks/check/{relic_id}")
async def check_bookmark(
    relic_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Check if a relic is bookmarked by the authenticated client.

    Requires valid X-Client-Key header.
    Returns bookmarked status.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    bookmark = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()

    return {
        "relic_id": relic_id,
        "is_bookmarked": bookmark is not None,
        "bookmark_id": bookmark.id if bookmark else None
    }


@app.get("/api/v1/bookmarks", response_model=dict)
async def get_client_bookmarks(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get all bookmarks for the authenticated client.

    Requires valid X-Client-Key header.
    Returns list of bookmarked relics with bookmark metadata.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    # Join bookmarks with relics, exclude deleted relics
    bookmarks = db.query(ClientBookmark, Relic).join(
        Relic, ClientBookmark.relic_id == Relic.id
    ).filter(
        ClientBookmark.client_id == client.id
    ).order_by(ClientBookmark.created_at.desc()).all()

    return {
        "client_id": client.id,
        "bookmark_count": len(bookmarks),
        "bookmarks": [
            {
                "id": relic.id,
                "name": relic.name,
                "content_type": relic.content_type,
                "size_bytes": relic.size_bytes,
                "created_at": relic.created_at,
                "access_level": relic.access_level,
                "bookmark_id": bookmark.id,
                "bookmarked_at": bookmark.created_at
            }
            for bookmark, relic in bookmarks
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
