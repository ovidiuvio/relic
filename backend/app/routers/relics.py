from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.utils import generate_relic_id, parse_expiry_string, is_expired, hash_password
from backend.app.models import Relic, ClientKey
from backend.app.schemas import RelicResponse, RelicListResponse
from backend.app.services.storage import storage_service
from backend.app.api.deps import get_client_key, get_or_create_client_key, check_ownership_or_admin

router = APIRouter()

# ==================== Helper Functions ====================

def generate_unique_relic_id(db: Session, max_retries: int = 5) -> str:
    """
    Generate a unique relic ID with collision handling.
    """
    for attempt in range(max_retries):
        relic_id = generate_relic_id()

        # Check if ID already exists
        existing = db.query(Relic).filter(Relic.id == relic_id).first()
        if not existing:
            return relic_id

    raise HTTPException(
        status_code=500,
        detail="Failed to generate unique relic ID after multiple attempts"
    )

# ==================== Relic Operations ====================

@router.post("", response_model=dict)
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


@router.get("", response_model=RelicListResponse)
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


@router.get("/{relic_id}", response_model=RelicResponse)
async def get_relic(relic_id: str, password: Optional[str] = None, db: Session = Depends(get_db)):
    """Get relic metadata."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")

    # Check optional password protection (independent of access_level)
    if relic.password_hash:
        if not password:
            raise HTTPException(status_code=403, detail="This relic requires a password")
        if hash_password(password) != relic.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")

    # Increment access count
    relic.access_count += 1
    db.commit()

    return relic

@router.get("/{relic_id}/raw")
async def get_relic_raw(relic_id: str, db: Session = Depends(get_db)):
    """Get raw relic content."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()

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


@router.post("/{relic_id}/fork", response_model=dict)
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
    """
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


@router.delete("/{relic_id}")
async def delete_relic(relic_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Delete a relic (hard delete).
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
