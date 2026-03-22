"""Relic CRUD and content endpoints."""
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload, joinedload, contains_eager
from sqlalchemy import func, or_
from datetime import datetime
from typing import Optional, List
import logging
import urllib.parse

from backend.config import settings
from backend.database import get_db
from backend.models import Relic, ClientKey, Tag, Space, Comment, RelicAccess
from backend.schemas import RelicResponse, RelicListResponse, RelicUpdate, RelicAccessAdd, RelicAccessEntry
from backend.storage import storage_service
from backend.utils import parse_expiry_string, is_expired, hash_password, get_fork_count, get_fork_counts, clamp_limit, like_term, apply_relic_search, relic_sort_order
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
    if access_level not in ("public", "private", "restricted"):
        raise HTTPException(
            status_code=400,
            detail="Invalid access_level. Must be 'public', 'private', or 'restricted'."
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
    relic = db.query(Relic).options(
        selectinload(Relic.tags),
        selectinload(Relic.access_list)
    ).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")

    # Check optional password protection (independent of access_level)
    # access_level only affects listing in recents:
    # - public: listed and discoverable
    # - private: not listed (URL serves as access token)
    # - restricted: not listed, only accessible by owner/admin or explicitly allowed clients
    if relic.password_hash:
        if not password:
            raise HTTPException(status_code=403, detail="This relic requires a password")
        if hash_password(password) != relic.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")

    # Check if client can edit
    client = get_client_key(request, db)

    # Enforce restricted access
    if relic.access_level == "restricted":
        if not check_ownership_or_admin(relic, client, require_auth=False):
            allowed_ids = {a.client_id for a in relic.access_list}
            if not client or client.id not in allowed_ids:
                raise HTTPException(status_code=403, detail="Access restricted")
    relic.can_edit = check_ownership_or_admin(relic, client, require_auth=False)

    # Increment access count
    relic.access_count += 1
    db.commit()

    # Calculate counts
    comments_count = db.query(func.count(Comment.id)).filter(Comment.relic_id == relic_id).scalar()
    relic_response = RelicResponse.from_orm(relic)
    relic_response.comments_count = comments_count or 0
    relic_response.forks_count = get_fork_count(db, relic_id)
    return relic_response

@router.get("/{relic_id}")
@router.get("/{relic_id}/raw")
async def get_relic_raw(relic_id: str, request: Request, password: Optional[str] = None, db: Session = Depends(get_db)):
    """Get raw relic content."""
    relic = db.query(Relic).options(selectinload(Relic.access_list)).filter(Relic.id == relic_id).first()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")

    # Check password protection
    if relic.password_hash:
        if not password:
            raise HTTPException(status_code=403, detail="This relic requires a password")
        if hash_password(password) != relic.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")

    # Enforce restricted access
    if relic.access_level == "restricted":
        client = get_client_key(request, db)
        if not check_ownership_or_admin(relic, client, require_auth=False):
            allowed_ids = {a.client_id for a in relic.access_list}
            if not client or client.id not in allowed_ids:
                raise HTTPException(status_code=403, detail="Access restricted")

    try:
        content = await storage_service.download(relic.s3_key)
        return StreamingResponse(
            iter([content]),
            media_type=relic.content_type,
            headers={"Content-Disposition": "inline; filename*=UTF-8''{filename}".format(
                filename=urllib.parse.quote(relic.name or relic.id, safe="")
            )}
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
    Fork belongs to forking client if key provided.
    """
    # Normalize tags input
    if tags and len(tags) == 1 and ',' in tags[0]:
        tags = [t.strip() for t in tags[0].split(',')]

    # Validate access_level
    if access_level and access_level not in ['public', 'private', 'restricted']:
        raise HTTPException(status_code=400, detail="Invalid access_level. Must be 'public', 'private', or 'restricted'")

    # Get client (optional)
    client = get_or_create_client_key(request, db)

    original = db.query(Relic).options(selectinload(Relic.access_list)).filter(Relic.id == relic_id).first()

    if not original:
        raise HTTPException(status_code=404, detail="Relic not found")

    if is_expired(original.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")

    # Check password protection
    if original.password_hash:
        password = request.headers.get("X-Relic-Password")
        if not password:
            raise HTTPException(status_code=403, detail="This relic requires a password")
        if hash_password(password) != original.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")

    # Enforce restricted access
    if original.access_level == "restricted":
        if not check_ownership_or_admin(original, client, require_auth=False):
            allowed_ids = {a.client_id for a in original.access_list}
            if not client or client.id not in allowed_ids:
                raise HTTPException(status_code=403, detail="Access restricted")

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
async def get_relic_lineage(relic_id: str, max_nodes: int = 200, db: Session = Depends(get_db)):
    """Get the fork lineage tree for a relic."""
    max_nodes = min(max(max_nodes, 1), 5000)
    current = db.query(Relic).filter(Relic.id == relic_id).first()
    if not current:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Walk up to root — O(depth) queries, typically very shallow
    visited_up = set()
    root_id = current.id
    current_relic = current
    while current_relic.fork_of and current_relic.fork_of not in visited_up:
        visited_up.add(current_relic.fork_of)
        parent = db.query(Relic).filter(Relic.id == current_relic.fork_of).first()
        if not parent:
            break
        root_id = parent.id
        current_relic = parent

    root_relic_obj = db.query(Relic).filter(Relic.id == root_id).first()
    if not root_relic_obj:
        return {"current_relic_id": relic_id, "root": None, "total_nodes": 0, "truncated": False}

    tree_nodes = {
        root_id: {"id": root_relic_obj.id, "name": root_relic_obj.name, "created_at": root_relic_obj.created_at, "children": []}
    }

    # Level-by-level BFS with batched IN queries — O(depth) queries regardless of tree size
    current_level_ids = [root_id]
    truncated = False

    while current_level_ids:
        children = [
            c for c in db.query(Relic).filter(Relic.fork_of.in_(current_level_ids)).all()
            if c.id not in tree_nodes
        ]
        if max_nodes > 0 and len(tree_nodes) + len(children) > max_nodes:
            truncated = True
            break
        next_level_ids = []
        for child in children:
            child_data = {"id": child.id, "name": child.name, "created_at": child.created_at, "children": []}
            tree_nodes[child.id] = child_data
            tree_nodes[child.fork_of]["children"].append(child_data)
            next_level_ids.append(child.id)
        current_level_ids = next_level_ids

    return {
        "current_relic_id": relic_id,
        "root": tree_nodes[root_id],
        "total_nodes": len(tree_nodes),
        "truncated": truncated,
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
        logger.error(f"Failed to delete file from S3 for relic {relic_id}: {e}", exc_info=True)

    # Hard delete in database
    db.delete(relic)

    # Update owner's relic count (not admin's count if admin is deleting)
    if relic.client_id:
        owner = db.query(ClientKey).filter(ClientKey.id == relic.client_id).first()
        if owner and owner.relic_count > 0:
            owner.relic_count -= 1

    db.commit()

    logger.info(f"Relic {relic_id} deleted successfully by {'owner' if client and client.id == relic.client_id else 'admin'}")

    return {"message": "Relic deleted successfully"}


@router.get("/api/v1/relics", response_model=RelicListResponse)
async def list_relics(
    limit: int = 25,
    offset: int = 0,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    """List the most recent public relics with pagination."""
    limit = clamp_limit(limit)
    offset = max(0, offset)
    query = db.query(Relic).options(selectinload(Relic.tags)).filter(Relic.access_level == "public")

    if tag:
        tag_obj = db.query(Tag).filter(Tag.name == tag.strip().lower()).first()
        if tag_obj:
            query = query.filter(Relic.tags.contains(tag_obj))
        else:
            return {"relics": [], "total": 0, "limit": limit, "offset": offset}

    if search:
        query = apply_relic_search(query, search, db)

    order = relic_sort_order(sort_by, sort_order)

    total = query.count()
    relics = query.order_by(order).offset(offset).limit(limit).all()

    relic_ids = [r.id for r in relics]
    comments_counts = {}

    if relic_ids:
        comments_counts = {
            row[0]: row[1]
            for row in db.query(Comment.relic_id, func.count(Comment.id)).filter(
                Comment.relic_id.in_(relic_ids)
            ).group_by(Comment.relic_id).all()
        }
    forks_counts = get_fork_counts(db, relic_ids)

    relic_responses = []
    for relic in relics:
        relic_response = RelicResponse.from_orm(relic)
        relic_response.comments_count = comments_counts.get(relic.id, 0)
        relic_response.forks_count = forks_counts.get(relic.id, 0)
        relic_responses.append(relic_response)

    return {"relics": relic_responses, "total": total, "limit": limit, "offset": offset}


@router.get("/api/v1/relics/{relic_id}/access", response_model=dict)
async def get_relic_access(
    relic_id: str,
    request: Request,
    search: Optional[str] = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List clients with explicit access to a restricted relic. Owner/admin only."""
    limit = clamp_limit(limit)
    offset = max(0, offset)
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, client):
        raise HTTPException(status_code=403, detail="Not authorized")

    access_query = db.query(RelicAccess).join(RelicAccess.client).options(
        contains_eager(RelicAccess.client)
    ).filter(RelicAccess.relic_id == relic_id)

    if search:
        term = like_term(search)
        access_query = access_query.filter(
            or_(ClientKey.name.ilike(term), ClientKey.public_id.ilike(term))
        )

    total = access_query.count()
    entries = access_query.order_by(RelicAccess.created_at).offset(offset).limit(limit).all()

    return {
        "access": [
            RelicAccessEntry(
                public_id=e.client.public_id if e.client else None,
                client_name=e.client.name if e.client else None,
                created_at=e.created_at
            )
            for e in entries
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/v1/relics/{relic_id}/access", response_model=RelicAccessEntry)
async def add_relic_access(
    relic_id: str,
    body: RelicAccessAdd,
    request: Request,
    db: Session = Depends(get_db)
):
    """Add a client to a relic's access list by public_id. Owner/admin only."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, client):
        raise HTTPException(status_code=403, detail="Not authorized")

    target = db.query(ClientKey).filter(ClientKey.public_id == body.public_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check for duplicate
    existing = db.query(RelicAccess).filter(
        RelicAccess.relic_id == relic_id,
        RelicAccess.client_id == target.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Client already has access")

    access_entry = RelicAccess(relic_id=relic_id, client_id=target.id)
    db.add(access_entry)
    db.commit()

    return RelicAccessEntry(
        public_id=target.public_id,
        client_name=target.name,
        created_at=access_entry.created_at
    )


@router.delete("/api/v1/relics/{relic_id}/access/{public_id}")
async def remove_relic_access(
    relic_id: str,
    public_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Remove a client from a relic's access list by public_id. Owner/admin only."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, client):
        raise HTTPException(status_code=403, detail="Not authorized")

    target = db.query(ClientKey).filter(ClientKey.public_id == public_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Client not found")

    entry = db.query(RelicAccess).filter(
        RelicAccess.relic_id == relic_id,
        RelicAccess.client_id == target.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Access entry not found")

    db.delete(entry)
    db.commit()

    return {"message": "Access removed"}
