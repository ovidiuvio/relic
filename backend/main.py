"""Main FastAPI application."""
from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey, Boolean, JSON, Text, Table, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, selectinload
from datetime import datetime
import uuid
from typing import Optional, List
import io

from backend.config import settings
from backend.database import init_db, get_db, SessionLocal
from backend.models import Base, Relic, ClientKey, Tag, relic_tags, ClientBookmark, RelicReport, Comment
from backend.schemas import (
    RelicCreate, RelicResponse, RelicListResponse,
    RelicFork, ReportCreate, ReportResponse,
    CommentCreate, CommentResponse, ClientNameUpdate, CommentUpdate,
    RelicUpdate
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
    import os
    if not os.getenv("SKIP_DB_INIT"):
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


@app.get("/api/v1/version")
async def get_version():
    """Get application version."""
    return {"version": settings.APP_VERSION}


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
            "name": existing_client.name,
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
async def get_client_relics(
    request: Request,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all relics owned by this client.

    Requires valid X-Client-Key header.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    query = db.query(Relic).options(selectinload(Relic.tags)).filter(
        Relic.client_id == client.id
    )

    if tag:
        tag_obj = db.query(Tag).filter(Tag.name == tag.strip().lower()).first()
        if tag_obj:
            query = query.filter(Relic.tags.contains(tag_obj))
        else:
            return {
                "client_id": client.id,
                "relic_count": 0,
                "relics": []
            }

    relics = query.order_by(Relic.created_at.desc()).all()

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
                "access_level": relic.access_level,
                "access_count": relic.access_count,
                "bookmark_count": relic.bookmark_count,
                "tags": [{"id": t.id, "name": t.name} for t in relic.tags]
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


# ==================== Admin Authorization ====================

def is_admin_client(client: Optional[ClientKey]) -> bool:
    """
    Check if a client has admin privileges.

    A client is admin if their ID is in the ADMIN_CLIENT_IDS config.
    """
    if not client:
        return False
    return client.id in settings.get_admin_client_ids()


def get_admin_client(request: Request, db: Session) -> ClientKey:
    """
    Get client and verify admin privileges.

    Raises HTTPException if not authenticated or not admin.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(
            status_code=401,
            detail="Client key required"
        )
    if not is_admin_client(client):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return client


def check_ownership_or_admin(
    relic: Relic,
    client: Optional[ClientKey],
    require_auth: bool = True
) -> bool:
    """
    Check if client owns the relic or is an admin.

    Args:
        relic: The relic to check ownership for
        client: The client making the request
        require_auth: If True, require authentication

    Returns:
        True if client owns relic or is admin

    Raises:
        HTTPException: If require_auth is True and client is None
    """
    if require_auth and not client:
        raise HTTPException(
            status_code=401,
            detail="Client key required"
        )

    if not client:
        return False

    # Admin can do anything
    if is_admin_client(client):
        return True

    # Owner check
    return relic.client_id == client.id


# ==================== Helper Functions ====================

def process_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    """Process a list of tag names and return Tag objects (creating new ones if needed)."""
    if not tag_names:
        return []

    # Normalize tags
    normalized_names = sorted(list(set(name.strip().lower() for name in tag_names if name.strip())))

    if not normalized_names:
        return []

    # Find existing tags
    existing_tags = db.query(Tag).filter(Tag.name.in_(normalized_names)).all()
    existing_names = {tag.name for tag in existing_tags}

    result_tags = list(existing_tags)

    # Create new tags
    for name in normalized_names:
        if name not in existing_names:
            new_tag = Tag(name=name)
            db.add(new_tag)
            result_tags.append(new_tag)

    return result_tags


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
    # Normalize tags input - handle if it comes as comma-separated string in a single list element
    if tags and len(tags) == 1 and ',' in tags[0]:
        tags = [t.strip() for t in tags[0].split(',')]

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

        # Process tags
        tag_objects = process_tags(db, tags) if tags else []

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

        # Associate tags
        if tag_objects:
            relic.tags = tag_objects

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
async def get_relic(
    relic_id: str,
    request: Request,
    password: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get relic metadata."""
    relic = db.query(Relic).options(selectinload(Relic.tags)).filter(Relic.id == relic_id).first()

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

    # Check if client can edit
    client = get_client_key(request, db)
    relic.can_edit = check_ownership_or_admin(relic, client, require_auth=False)

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
    tags: Optional[List[str]] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Fork a relic (create new independent lineage).

    Creates a new relic with fork_of pointing to the original.
    Public endpoint - anyone can fork. Fork belongs to forking client if key provided.
    """
    # Normalize tags input
    if tags and len(tags) == 1 and ',' in tags[0]:
        tags = [t.strip() for t in tags[0].split(',')]

    # Validate access_level
    if access_level and access_level not in ['public', 'private']:
        raise HTTPException(status_code=400, detail="Invalid access_level. Must be 'public' or 'private'")

    # Get client (optional - fork is public)
    client = get_or_create_client_key(request, db)

    original = db.query(Relic).filter(Relic.id == relic_id).first()

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

        # Process tags: use provided tags or copy from original
        if tags is not None:
            tag_objects = process_tags(db, tags)
        else:
            tag_objects = list(original.tags)

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

        # Associate tags
        if tag_objects:
            fork.tags = tag_objects

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


@app.put("/api/v1/relics/{relic_id}", response_model=RelicResponse)
async def update_relic(
    relic_id: str,
    update: RelicUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update relic metadata.

    Only owner or admin can update.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, client):
        raise HTTPException(status_code=403, detail="Not authorized to edit this relic")

    if update.name is not None:
        relic.name = update.name

    if update.content_type is not None:
        relic.content_type = update.content_type

    if update.language_hint is not None:
        relic.language_hint = update.language_hint

    if update.access_level is not None:
        relic.access_level = update.access_level

    if update.expires_in is not None:
        relic.expires_at = parse_expiry_string(update.expires_in)

    if update.tags is not None:
        relic.tags = process_tags(db, update.tags)

    db.commit()
    db.refresh(relic)

    relic.can_edit = True
    return relic


@app.delete("/api/v1/relics/{relic_id}")
async def delete_relic(relic_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Delete a relic (hard delete).

    Only client owner OR admin can delete.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Client key required")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Check ownership OR admin privileges
    if not check_ownership_or_admin(relic, client, require_auth=False):
        raise HTTPException(status_code=403, detail="Not authorized to delete this relic")

    # Delete file from S3 storage
    try:
        await storage_service.delete(relic.s3_key)
    except Exception as e:
        # Log error but don't fail the delete operation
        print(f"Failed to delete file from S3: {e}")

    # Hard delete in database
    db.delete(relic)

    # Update owner's relic count (not admin's count if admin is deleting)
    if relic.client_id:
        owner = db.query(ClientKey).filter(ClientKey.id == relic.client_id).first()
        if owner and owner.relic_count > 0:
            owner.relic_count -= 1

    db.commit()

    return {"message": "Relic deleted successfully"}


# ==================== Listing & Search ====================

@app.put("/api/v1/client/name", response_model=dict)
async def update_client_name(
    name_update: ClientNameUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update the client's display name."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    client.name = name_update.name
    db.commit()
    
    return {"status": "updated", "name": client.name}


@app.get("/api/v1/relics", response_model=RelicListResponse)
async def list_relics(
    limit: int = 1000,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List the 1000 most recent public relics."""
    query = db.query(Relic).options(selectinload(Relic.tags)).filter(Relic.access_level == "public")

    if tag:
        tag_obj = db.query(Tag).filter(Tag.name == tag.strip().lower()).first()
        if tag_obj:
            query = query.filter(Relic.tags.contains(tag_obj))
        else:
            # If tag doesn't exist, return empty list
            return {"relics": []}

    relics = query.order_by(Relic.created_at.desc()).limit(limit).all()

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

    # Increment bookmark count
    relic.bookmark_count += 1

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

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if relic and relic.bookmark_count > 0:
        relic.bookmark_count -= 1

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

    # Join bookmarks with relics, exclude deleted relics, and eagerly load tags
    bookmarks = db.query(ClientBookmark, Relic).join(
        Relic, ClientBookmark.relic_id == Relic.id
    ).options(selectinload(Relic.tags)).filter(
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
                "access_count": relic.access_count,
                "bookmark_count": relic.bookmark_count,
                "bookmark_id": bookmark.id,
                "bookmarked_at": bookmark.created_at,
                "tags": [{"id": t.id, "name": t.name} for t in relic.tags]
            }
            for bookmark, relic in bookmarks
        ]
    }


# ==================== Comments ====================

@app.post("/api/v1/relics/{relic_id}/comments", response_model=CommentResponse)
async def create_comment(
    relic_id: str,
    comment: CommentCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a comment on a relic."""
    # Verify relic exists
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Get client key (optional but recommended)
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required to comment")
    
    if not client.name:
        raise HTTPException(status_code=400, detail="You must set a display name in your profile to comment")

    client_id = client.id

    db_comment = Comment(
        relic_id=relic_id,
        client_id=client_id,
        line_number=comment.line_number,
        content=comment.content,
        parent_id=comment.parent_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    
    # Add author name to response
    response = CommentResponse.from_orm(db_comment)
    response.author_name = client.name
    return response


@app.get("/api/v1/relics/{relic_id}/comments", response_model=List[CommentResponse])
async def get_relic_comments(
    relic_id: str,
    db: Session = Depends(get_db)
):
    """Get all comments for a relic."""
    # Verify relic exists
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Join with ClientKey to get author names
    results = db.query(Comment, ClientKey.name).outerjoin(
        ClientKey, Comment.client_id == ClientKey.id
    ).filter(
        Comment.relic_id == relic_id
    ).order_by(Comment.line_number, Comment.created_at).all()
    
    comments = []
    for comment, author_name in results:
        comment_resp = CommentResponse.from_orm(comment)
        comment_resp.author_name = author_name
        comments.append(comment_resp)
    
    return comments


@app.put("/api/v1/relics/{relic_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    relic_id: str,
    comment_id: str,
    comment_update: CommentUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a comment (only by the author)."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.relic_id == relic_id
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check ownership
    if comment.client_id != client.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this comment")

    comment.content = comment_update.content
    db.commit()
    db.refresh(comment)
    
    response = CommentResponse.from_orm(comment)
    response.author_name = client.name
    return response


@app.delete("/api/v1/relics/{relic_id}/comments/{comment_id}")
async def delete_comment(
    relic_id: str,
    comment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a comment (only by the author or admin)."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.relic_id == relic_id
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check ownership or admin status
    is_owner = comment.client_id == client.id
    is_admin = is_admin_client(client)

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()
    return {"status": "deleted"}


# ==================== Admin Operations ====================

@app.get("/api/v1/admin/check")
async def admin_check(request: Request, db: Session = Depends(get_db)):
    """
    Check if current client has admin privileges.

    Returns admin status without throwing error.
    """
    client = get_client_key(request, db)
    return {
        "client_id": client.id if client else None,
        "is_admin": is_admin_client(client)
    }


@app.get("/api/v1/admin/relics", response_model=dict)
async def admin_list_all_relics(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    access_level: Optional[str] = None,
    client_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all relics including private ones.

    Requires admin privileges.
    Optional filters: access_level, client_id
    """
    get_admin_client(request, db)  # Verify admin

    query = db.query(Relic).options(selectinload(Relic.tags))

    if access_level:
        query = query.filter(Relic.access_level == access_level)
    
    if client_id:
        query = query.filter(Relic.client_id == client_id)

    total = query.count()
    relics = query.order_by(Relic.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "client_id": client_id,
        "relics": [
            {
                "id": r.id,
                "name": r.name,
                "client_id": r.client_id,
                "content_type": r.content_type,
                "size_bytes": r.size_bytes,
                "access_level": r.access_level,
                "access_count": r.access_count,
                "bookmark_count": r.bookmark_count,
                "created_at": r.created_at,
                "expires_at": r.expires_at,
                "tags": [{"id": t.id, "name": t.name} for t in r.tags]
            }
            for r in relics
        ]
    }


@app.get("/api/v1/admin/clients", response_model=dict)
async def admin_list_clients(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all registered clients.

    Requires admin privileges.
    """
    get_admin_client(request, db)

    total = db.query(ClientKey).count()
    clients = db.query(ClientKey).order_by(
        ClientKey.created_at.desc()
    ).offset(offset).limit(limit).all()

    admin_ids = settings.get_admin_client_ids()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "clients": [
            {
                "id": c.id,
                "created_at": c.created_at,
                "relic_count": c.relic_count,
                "is_admin": c.id in admin_ids
            }
            for c in clients
        ]
    }


@app.get("/api/v1/admin/stats", response_model=dict)
async def admin_get_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Get system statistics.

    Requires admin privileges.
    """
    get_admin_client(request, db)

    from sqlalchemy import func

    total_relics = db.query(func.count(Relic.id)).scalar() or 0
    total_clients = db.query(func.count(ClientKey.id)).scalar() or 0
    total_size = db.query(func.sum(Relic.size_bytes)).scalar() or 0
    public_relics = db.query(func.count(Relic.id)).filter(
        Relic.access_level == "public"
    ).scalar() or 0
    private_relics = db.query(func.count(Relic.id)).filter(
        Relic.access_level == "private"
    ).scalar() or 0

    return {
        "total_relics": total_relics,
        "total_clients": total_clients,
        "total_size_bytes": total_size,
        "public_relics": public_relics,
        "private_relics": private_relics,
        "admin_count": len(settings.get_admin_client_ids())
    }


@app.delete("/api/v1/admin/clients/{client_id}")
async def admin_delete_client(
    client_id: str,
    request: Request,
    delete_relics: bool = False,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Delete a client and optionally their relics.

    Requires admin privileges.

    Args:
        delete_relics: If True, also delete all relics owned by this client
    """
    get_admin_client(request, db)

    client = db.query(ClientKey).filter(ClientKey.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Prevent deleting admin clients
    if client_id in settings.get_admin_client_ids():
        raise HTTPException(
            status_code=403,
            detail="Cannot delete admin client"
        )

    if delete_relics:
        # Delete all relics owned by this client
        client_relics = db.query(Relic).filter(Relic.client_id == client_id).all()
        for relic in client_relics:
            try:
                await storage_service.delete(relic.s3_key)
            except Exception as e:
                print(f"Failed to delete file from S3: {e}")
            db.delete(relic)
    else:
        # Just disassociate relics from client
        db.query(Relic).filter(Relic.client_id == client_id).update(
            {Relic.client_id: None}
        )

    # Delete bookmarks
    db.query(ClientBookmark).filter(ClientBookmark.client_id == client_id).delete()

    # Delete client
    db.delete(client)
    db.commit()

    return {"message": f"Client {client_id} deleted successfully"}


@app.get("/api/v1/admin/config", response_model=dict)
async def admin_get_config(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Get application configuration (environment variables).

    Requires admin privileges.
    """
    get_admin_client(request, db)

    return {
        "app": {
            "APP_NAME": settings.APP_NAME,
            "APP_VERSION": settings.APP_VERSION,
            "DEBUG": settings.DEBUG
        },
        "database": {
            "DATABASE_URL": settings.DATABASE_URL
        },
        "storage": {
            "S3_ENDPOINT_URL": settings.S3_ENDPOINT_URL,
            "S3_ACCESS_KEY": settings.S3_ACCESS_KEY,
            "S3_SECRET_KEY": settings.S3_SECRET_KEY,
            "S3_BUCKET_NAME": settings.S3_BUCKET_NAME,
            "S3_REGION": settings.S3_REGION
        },
        "upload": {
            "MAX_UPLOAD_SIZE": settings.MAX_UPLOAD_SIZE,
            "MAX_UPLOAD_SIZE_MB": settings.MAX_UPLOAD_SIZE / 1024 / 1024
        },
        "backup": {
            "BACKUP_ENABLED": settings.BACKUP_ENABLED,
            "BACKUP_TIMES": settings.BACKUP_TIMES,
            "BACKUP_TIMEZONE": settings.BACKUP_TIMEZONE,
            "BACKUP_RETENTION_DAYS": settings.BACKUP_RETENTION_DAYS,
            "BACKUP_RETENTION_WEEKS": settings.BACKUP_RETENTION_WEEKS,
            "BACKUP_CLEANUP_ENABLED": settings.BACKUP_CLEANUP_ENABLED,
            "BACKUP_ON_STARTUP": settings.BACKUP_ON_STARTUP,
            "BACKUP_ON_SHUTDOWN": settings.BACKUP_ON_SHUTDOWN
        },
        "admin": {
            "ADMIN_CLIENT_IDS": settings.get_admin_client_ids()
        },
        "cors": {
            "ALLOWED_ORIGINS": settings.get_allowed_origins()
        }
    }


@app.get("/api/v1/admin/backups", response_model=dict)
async def admin_list_backups(
    request: Request,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all database backups.

    Requires admin privileges.
    """
    from backend.backup import list_all_backups

    get_admin_client(request, db)

    try:
        backups = await list_all_backups()

        # Sort by timestamp descending (newest first)
        backups_sorted = sorted(backups, key=lambda x: x['timestamp'], reverse=True)

        total = len(backups_sorted)
        total_size = sum(b['size'] for b in backups_sorted)

        # Apply pagination
        paginated = backups_sorted[offset:offset + limit]

        # Format for response
        formatted = []
        for backup in paginated:
            formatted.append({
                "key": backup['key'],
                "filename": backup['key'].split('/')[-1],
                "timestamp": backup['timestamp'].isoformat(),
                "size_bytes": backup['size'],
                "last_modified": backup['last_modified'].isoformat() if backup.get('last_modified') else None
            })

        return {
            "total": total,
            "total_size_bytes": total_size,
            "limit": limit,
            "offset": offset,
            "backups": formatted
        }
    except Exception as e:
        return {
            "total": 0,
            "total_size_bytes": 0,
            "backups": [],
            "error": str(e)
        }


@app.post("/api/v1/admin/backups", response_model=dict)
async def admin_create_backup(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Trigger a manual database backup.

    Requires admin privileges.
    """
    from backend.backup import perform_backup

    get_admin_client(request, db)

    try:
        success = await perform_backup(backup_type='manual')
        if success:
            return {"success": True, "message": "Backup completed successfully"}
        else:
            return {"success": False, "message": "Backup failed - check server logs"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/v1/admin/backups/{filename}/download")
async def admin_download_backup(
    filename: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Download a specific backup file.

    Requires admin privileges.
    """
    get_admin_client(request, db)

    # Validate filename format
    if not filename.startswith('backup-') or not filename.endswith('.sql.gz'):
        raise HTTPException(status_code=400, detail="Invalid backup filename")

    key = f"db/{filename}"

    try:
        # Get the backup file from S3
        data = await storage_service.download(key)
        
        from fastapi.responses import Response
        return Response(
            content=data,
            media_type="application/gzip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Backup not found: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




# ==================== Report Operations ====================

@app.post("/api/v1/reports", response_model=dict)
async def create_report(
    report: ReportCreate,
    db: Session = Depends(get_db)
):
    """
    Report a relic for inappropriate content.
    """
    # Verify relic exists
    relic = db.query(Relic).filter(Relic.id == report.relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Create report
    new_report = RelicReport(
        relic_id=report.relic_id,
        reason=report.reason,
        created_at=datetime.utcnow()
    )

    db.add(new_report)
    db.commit()
    
    return {"message": "Report submitted successfully"}


@app.get("/api/v1/admin/reports", response_model=dict)
async def admin_list_reports(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all reports.
    
    Requires admin privileges.
    """
    get_admin_client(request, db)

    total = db.query(RelicReport).count()
    reports = db.query(RelicReport).order_by(
        RelicReport.created_at.desc()
    ).offset(offset).limit(limit).all()

    # Enrich with relic names
    report_responses = []
    for r in reports:
        relic = db.query(Relic).filter(Relic.id == r.relic_id).first()
        report_responses.append({
            "id": r.id,
            "relic_id": r.relic_id,
            "reason": r.reason,
            "created_at": r.created_at,
            "relic_name": relic.name if relic else "Unknown (Deleted)"
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "reports": report_responses
    }


@app.delete("/api/v1/admin/reports/{report_id}")
async def admin_delete_report(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Dismiss (delete) a report.
    
    Requires admin privileges.
    """
    get_admin_client(request, db)

    report = db.query(RelicReport).filter(RelicReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()

    return {"message": "Report dismissed successfully"}
