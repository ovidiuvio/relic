"""Relic CRUD and content endpoints."""
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from datetime import datetime
from typing import Optional, List
import logging

from backend.config import settings
from backend.database import get_db
from backend.models import Relic, ClientKey, Tag, Space, Comment
from backend.schemas import RelicResponse, RelicListResponse, RelicUpdate
from backend.storage import storage_service
from backend.utils import parse_expiry_string, is_expired, hash_password
from backend.dependencies import (
    get_client_key, get_or_create_client_key, check_ownership_or_admin,
    process_tags, generate_unique_relic_id, check_space_access
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/v1/relics", response_model=dict)
async def create_relic(
    request: Request,
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    language_hint: Optional[str] = Form(None),
    access_level: str = Form("public"),
    expires_in: Optional[str] = Form(None),
    tags: Optional[List[str]] = Form(None),
    space_id: Optional[str] = Form(None),
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

        # Add to space if space_id is provided
        if space_id:
            space = db.query(Space).filter(Space.id == space_id).first()
            if space and client and check_space_access(space, client.id, "editor"):
                space.relics.append(relic)

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
        logger.error(f"Operation failed: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/api/v1/relics/{relic_id}", response_model=RelicResponse)
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

    # Calculate counts using SQL COUNT (efficient, single queries)
    comments_count = db.query(func.count(Comment.id)).filter(Comment.relic_id == relic_id).scalar()
    forks_count = db.query(func.count(Relic.id)).filter(Relic.fork_of == relic_id).scalar()
    relic_response = RelicResponse.from_orm(relic)
    relic_response.comments_count = comments_count or 0
    relic_response.forks_count = forks_count or 0
    return relic_response

@router.get("/{relic_id}")
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
        logger.error(f"Operation failed: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.post("/api/v1/relics/{relic_id}/fork", response_model=dict)
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
        logger.error(f"Operation failed: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/api/v1/relics/{relic_id}/lineage")
async def get_relic_lineage(relic_id: str, db: Session = Depends(get_db)):
    """Get the fork lineage tree for a relic."""
    current = db.query(Relic).filter(Relic.id == relic_id).first()
    if not current:
        raise HTTPException(status_code=404, detail="Relic not found")
        
    visited = set()
    root_id = current.id
    current_relic = current
    
    while current_relic.fork_of and current_relic.fork_of not in visited:
        visited.add(current_relic.fork_of)
        parent = db.query(Relic).filter(Relic.id == current_relic.fork_of).first()
        if not parent:
            break
        root_id = parent.id
        current_relic = parent

    tree_nodes = {}
    queue = [root_id]
    visited_down = set([root_id])
    
    root_relic_obj = db.query(Relic).filter(Relic.id == root_id).first()
    if not root_relic_obj:
        return {"current_relic_id": relic_id, "root": None}
        
    tree_nodes[root_id] = {
        "id": root_relic_obj.id,
        "name": root_relic_obj.name,
        "created_at": root_relic_obj.created_at,
        "children": []
    }
    
    while queue:
        current_id = queue.pop(0)
        children = db.query(Relic).filter(Relic.fork_of == current_id).all()
        for child in children:
            if child.id not in visited_down:
                visited_down.add(child.id)
                queue.append(child.id)
                child_data = {
                    "id": child.id,
                    "name": child.name,
                    "created_at": child.created_at,
                    "children": []
                }
                tree_nodes[child.id] = child_data
                tree_nodes[current_id]["children"].append(child_data)
                
    return {
        "current_relic_id": relic_id,
        "root": tree_nodes[root_id]
    }


@router.put("/api/v1/relics/{relic_id}", response_model=RelicResponse)
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


@router.delete("/api/v1/relics/{relic_id}")
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


@router.get("/api/v1/relics", response_model=RelicListResponse)
async def list_relics(
    limit: int = 200,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List the most recent public relics."""
    query = db.query(Relic).options(selectinload(Relic.tags)).filter(Relic.access_level == "public")

    if tag:
        tag_obj = db.query(Tag).filter(Tag.name == tag.strip().lower()).first()
        if tag_obj:
            query = query.filter(Relic.tags.contains(tag_obj))
        else:
            return {"relics": []}

    relics = query.order_by(Relic.created_at.desc()).limit(limit).all()

    # Fetch all counts in bulk (2 queries instead of N*2)
    relic_ids = [r.id for r in relics]
    comments_counts = {}
    forks_counts = {}

    if relic_ids:
        comments_counts = {
            row[0]: row[1]
            for row in db.query(Comment.relic_id, func.count(Comment.id)).filter(
                Comment.relic_id.in_(relic_ids)
            ).group_by(Comment.relic_id).all()
        }
        forks_counts = {
            row[0]: row[1]
            for row in db.query(Relic.fork_of, func.count(Relic.id)).filter(
                Relic.fork_of.in_(relic_ids)
            ).group_by(Relic.fork_of).all()
        }

    relic_responses = []
    for relic in relics:
        relic_response = RelicResponse.from_orm(relic)
        relic_response.comments_count = comments_counts.get(relic.id, 0)
        relic_response.forks_count = forks_counts.get(relic.id, 0)
        relic_responses.append(relic_response)

    return {"relics": relic_responses}
