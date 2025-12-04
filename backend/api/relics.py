from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from backend.database import get_db
from backend.models import Relic
from backend.schemas import RelicResponse, RelicListResponse
from backend.storage import storage_service
from backend.utils import parse_expiry_string, is_expired, hash_password
from backend.core.config import settings
from backend.services.clients import get_or_create_client_key, get_client_key
from backend.services.relics import generate_unique_relic_id

router = APIRouter()

@router.post("/relics", response_model=dict)
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
    """
    if access_level not in ("public", "private"):
        raise HTTPException(
            status_code=400,
            detail="Invalid access_level. Must be 'public' or 'private'."
        )
    client = get_or_create_client_key(request, db)
    try:
        if file:
            content = await file.read()
            if not content_type:
                content_type = file.content_type or "application/octet-stream"
            if not name:
                name = file.filename
        else:
            raise HTTPException(status_code=400, detail="No content provided")
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        relic_id = generate_unique_relic_id(db)
        s3_key = f"relics/{relic_id}"
        await storage_service.upload(s3_key, content, content_type)
        expires_at = parse_expiry_string(expires_in)
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

@router.get("/relics/{relic_id}", response_model=RelicResponse)
async def get_relic(relic_id: str, password: Optional[str] = None, db: Session = Depends(get_db)):
    """Get relic metadata."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic or relic.deleted_at:
        raise HTTPException(status_code=404, detail="Relic not found")
    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")
    if relic.password_hash:
        if not password or hash_password(password) != relic.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")
    relic.access_count += 1
    db.commit()
    return relic

@router.get("/{relic_id}/raw")
async def get_relic_raw(relic_id: str, db: Session = Depends(get_db)):
    """Get raw relic content."""
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic or relic.deleted_at:
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

@router.post("/relics/{relic_id}/fork", response_model=dict)
async def fork_relic(
    relic_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    access_level: Optional[str] = Form(None),
    expires_in: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Fork a relic."""
    if access_level and access_level not in ['public', 'private']:
        raise HTTPException(status_code=400, detail="Invalid access_level")
    client = get_or_create_client_key(request, db)
    original = db.query(Relic).filter(Relic.id == relic_id).first()
    if not original or original.deleted_at:
        raise HTTPException(status_code=404, detail="Relic not found")
    try:
        content, content_type = (await file.read(), file.content_type) if file else \
            (await storage_service.download(original.s3_key), original.content_type)
        new_id = generate_unique_relic_id(db)
        s3_key = f"relics/{new_id}"
        await storage_service.upload(s3_key, content, content_type)
        expires_at = parse_expiry_string(expires_in) if expires_in and expires_in != 'never' else None
        fork = Relic(
            id=new_id,
            client_id=client.id if client else None,
            name=name or original.name,
            content_type=content_type,
            language_hint=original.language_hint,
            size_bytes=len(content),
            s3_key=s3_key,
            fork_of=relic_id,
            access_level=access_level or original.access_level,
            expires_at=expires_at
        )
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

@router.delete("/relics/{relic_id}")
async def delete_relic(relic_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a relic."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Client key required")
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")
    if relic.client_id != client.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        await storage_service.delete(relic.s3_key)
    except Exception as e:
        print(f"Failed to delete file from S3: {e}")
    relic.deleted_at = datetime.utcnow()
    if client.relic_count > 0:
        client.relic_count -= 1
    db.commit()
    return {"message": "Relic deleted successfully"}

@router.get("/relics", response_model=RelicListResponse)
async def list_relics(limit: int = 1000, db: Session = Depends(get_db)):
    """List recent public relics."""
    relics = db.query(Relic).filter(
        Relic.deleted_at == None,
        Relic.access_level == "public"
    ).order_by(Relic.created_at.desc()).limit(limit).all()
    return {"relics": relics}
