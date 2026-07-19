"""Relic CRUD and content endpoints."""
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime
from typing import Optional, List
import logging
import urllib.parse

from backend.config import settings
from backend.database import get_db
from backend.models import Relic, User, Tag, Space, Comment, RelicAccess, space_relics
from backend.schemas import RelicResponse, RelicListResponse, RelicUpdate, RelicAccessAdd, RelicAccessEntry
from backend.storage import storage_service, FileTooLargeError
from backend.utils import parse_expiry_string, is_expired, hash_password, get_fork_count, get_fork_counts, clamp_limit, like_term, apply_relic_search, relic_sort_order
from backend.dependencies import (
    get_current_user, check_ownership_or_admin,
    process_tags, generate_unique_relic_id, check_space_access
)

logger = logging.getLogger(__name__)


router = APIRouter()


async def _create_relic_record(
    db: AsyncSession,
    user: Optional[User],
    relic_id: str,
    s3_key: str,
    size_bytes: int,
    *,
    name: Optional[str],
    content_type: str,
    language_hint: Optional[str],
    access_level: str,
    expires_in: Optional[str],
    tags: Optional[List[str]],
    space_id: Optional[str],
) -> dict:
    """Create the relic DB record after content is already in storage. Commits."""
    expires_at = parse_expiry_string(expires_in)
    tag_objects = await process_tags(db, tags) if tags else []

    relic = Relic(
        id=relic_id,
        user_id=user.id if user else None,
        name=name,
        content_type=content_type,
        language_hint=language_hint,
        size_bytes=size_bytes,
        s3_key=s3_key,
        access_level=access_level,
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )

    if tag_objects:
        relic.tags = tag_objects

    # Update user relic count (flushed with commit)
    if user:
        user.relic_count += 1

    db.add(relic)

    # Add to space if space_id is provided
    if space_id:
        space_result = await db.execute(select(Space).where(Space.id == space_id))
        space = space_result.scalar_one_or_none()
        if space and user and await check_space_access(space, user.id, db, "editor"):
            await db.flush()
            await db.execute(pg_insert(space_relics).values(space_id=space.id, relic_id=relic.id).on_conflict_do_nothing())

    await db.commit()

    return {
        "id": relic.id,
        "name": relic.name,
        "content_type": relic.content_type,
        "language_hint": relic.language_hint,
        "url": f"/{relic.id}",
        "created_at": relic.created_at,
        "size_bytes": relic.size_bytes
    }


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
    db: AsyncSession = Depends(get_db)
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

    # Validate user key if provided (anonymous creation is allowed)
    user = await get_current_user(request, db)
    if not user and request.headers.get("X-User-Key"):
        raise HTTPException(status_code=401, detail="Invalid user key")

    if not file:
        raise HTTPException(status_code=400, detail="No content provided")

    # Reject oversized uploads before touching the body when the client declares a length
    declared_length = request.headers.get("content-length")
    if declared_length and declared_length.isdigit() and int(declared_length) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    s3_key = None
    try:
        if not content_type:
            content_type = file.content_type or "application/octet-stream"
        if not name:
            name = file.filename

        # Generate unique relic ID with collision handling
        relic_id = await generate_unique_relic_id(db)

        # Stream to storage without buffering the whole file in memory;
        # size limit is enforced as bytes flow through
        s3_key = f"relics/{relic_id}"
        size_bytes = await storage_service.upload_stream(
            s3_key, file.read, content_type, max_size=settings.MAX_UPLOAD_SIZE
        )

        return await _create_relic_record(
            db, user, relic_id, s3_key, size_bytes,
            name=name, content_type=content_type, language_hint=language_hint,
            access_level=access_level, expires_in=expires_in, tags=tags, space_id=space_id,
        )

    except HTTPException:
        raise
    except FileTooLargeError:
        raise HTTPException(status_code=413, detail="File too large")
    except Exception as e:
        await db.rollback()
        logger.error(f"Operation failed: {e}")
        if s3_key:
            try:
                await storage_service.delete(s3_key)
            except Exception:
                logger.warning(f"Failed to clean up orphaned S3 object {s3_key}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.post("/api/v1/relics/raw", response_model=dict)
@router.put("/api/v1/relics/raw", response_model=dict)
async def create_relic_raw(
    request: Request,
    name: Optional[str] = None,
    content_type: Optional[str] = None,
    language_hint: Optional[str] = None,
    access_level: str = "public",
    expires_in: Optional[str] = None,
    tags: Optional[str] = None,
    space_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a relic from a raw request body (no multipart form).

    This is the fast path for large uploads: the body streams straight to
    storage with no multipart parsing and no temp-file spooling. Metadata
    comes from query parameters (tags comma-separated); the content type
    from the Content-Type header unless overridden via ?content_type=.

    Example: curl -T bigfile.bin "https://host/api/v1/relics/raw?name=bigfile.bin"
    """
    tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else None

    if access_level not in ("public", "private", "restricted"):
        raise HTTPException(
            status_code=400,
            detail="Invalid access_level. Must be 'public', 'private', or 'restricted'."
        )

    # Validate user key if provided (anonymous creation is allowed)
    user = await get_current_user(request, db)
    if not user and request.headers.get("X-User-Key"):
        raise HTTPException(status_code=401, detail="Invalid user key")

    # Reject oversized uploads before touching the body when the client declares a length
    declared_length = request.headers.get("content-length")
    if declared_length and declared_length.isdigit() and int(declared_length) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    if not content_type:
        content_type = request.headers.get("content-type") or "application/octet-stream"

    # Adapt the request body stream to the read(n) interface of upload_stream
    body_iter = request.stream().__aiter__()
    leftover = b""

    async def read(n: int) -> bytes:
        nonlocal leftover
        while not leftover:
            try:
                leftover = await body_iter.__anext__()
            except StopAsyncIteration:
                return b""
        out, leftover = leftover[:n], leftover[n:]
        return out

    s3_key = None
    try:
        relic_id = await generate_unique_relic_id(db)
        s3_key = f"relics/{relic_id}"
        size_bytes = await storage_service.upload_stream(
            s3_key, read, content_type, max_size=settings.MAX_UPLOAD_SIZE
        )
        if size_bytes == 0:
            await storage_service.delete(s3_key)
            raise HTTPException(status_code=400, detail="No content provided")

        return await _create_relic_record(
            db, user, relic_id, s3_key, size_bytes,
            name=name, content_type=content_type, language_hint=language_hint,
            access_level=access_level, expires_in=expires_in, tags=tag_list, space_id=space_id,
        )

    except HTTPException:
        raise
    except FileTooLargeError:
        raise HTTPException(status_code=413, detail="File too large")
    except Exception as e:
        await db.rollback()
        logger.error(f"Operation failed: {e}")
        if s3_key:
            try:
                await storage_service.delete(s3_key)
            except Exception:
                logger.warning(f"Failed to clean up orphaned S3 object {s3_key}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/api/v1/relics/{relic_id}", response_model=RelicResponse)
async def get_relic(
    relic_id: str,
    request: Request,
    password: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get relic metadata."""
    result = await db.execute(
        select(Relic).options(
            selectinload(Relic.tags),
            selectinload(Relic.access_list),
            joinedload(Relic.owner)
        ).where(Relic.id == relic_id)
    )
    relic = result.scalar_one_or_none()

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if is_expired(relic.expires_at):
        raise HTTPException(status_code=410, detail="Relic has expired")

    # Check optional password protection (independent of access_level)
    # access_level only affects listing in recents:
    # - public: listed and discoverable
    # - private: not listed (URL serves as access token)
    # - restricted: not listed, only accessible by owner/admin or explicitly allowed users
    if relic.password_hash:
        if not password:
            raise HTTPException(status_code=403, detail="This relic requires a password")
        if hash_password(password) != relic.password_hash:
            raise HTTPException(status_code=403, detail="Invalid password")

    # Check if user can edit
    user = await get_current_user(request, db)

    # Enforce restricted access
    if relic.access_level == "restricted":
        if not check_ownership_or_admin(relic, user, require_auth=False):
            allowed_ids = {a.user_id for a in relic.access_list}
            if not user or user.id not in allowed_ids:
                raise HTTPException(status_code=403, detail="Access restricted")
    relic.can_edit = check_ownership_or_admin(relic, user, require_auth=False)

    # Increment access count atomically
    await db.execute(
        update(Relic).where(Relic.id == relic_id).values(access_count=Relic.access_count + 1)
    )
    relic.access_count = (relic.access_count or 0) + 1  # keep local object in sync
    await db.commit()

    # Calculate counts
    comments_result = await db.execute(
        select(func.count(Comment.id)).where(Comment.relic_id == relic_id)
    )
    comments_count = comments_result.scalar()
    relic_response = RelicResponse.from_orm(relic)
    relic_response.comments_count = comments_count or 0
    relic_response.forks_count = await get_fork_count(db, relic_id)
    return relic_response

@router.get("/{relic_id}")
@router.get("/{relic_id}/raw")
async def get_relic_raw(relic_id: str, request: Request, password: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Get raw relic content."""
    result = await db.execute(
        select(Relic).options(selectinload(Relic.access_list)).where(Relic.id == relic_id)
    )
    relic = result.scalar_one_or_none()

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
        user = await get_current_user(request, db)
        if not check_ownership_or_admin(relic, user, require_auth=False):
            allowed_ids = {a.user_id for a in relic.access_list}
            if not user or user.id not in allowed_ids:
                raise HTTPException(status_code=403, detail="Access restricted")

    try:
        body, content_length = await storage_service.stream(relic.s3_key)
        return StreamingResponse(
            body,
            media_type=relic.content_type,
            headers={
                "Content-Length": str(content_length),
                "Content-Disposition": "inline; filename*=UTF-8''{filename}".format(
                    filename=urllib.parse.quote(relic.name or relic.id, safe="")
                ),
            }
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
    db: AsyncSession = Depends(get_db)
):
    """
    Fork a relic (create new independent lineage).

    Creates a new relic with fork_of pointing to the original.
    Fork belongs to forking user if key provided.
    """
    # Normalize tags input
    if tags and len(tags) == 1 and ',' in tags[0]:
        tags = [t.strip() for t in tags[0].split(',')]

    # Validate access_level
    if access_level and access_level not in ['public', 'private', 'restricted']:
        raise HTTPException(status_code=400, detail="Invalid access_level. Must be 'public', 'private', or 'restricted'")

    # Validate user key if provided (anonymous forking is allowed)
    user = await get_current_user(request, db)
    if not user and request.headers.get("X-User-Key"):
        raise HTTPException(status_code=401, detail="Invalid user key")

    result = await db.execute(
        select(Relic).options(
            selectinload(Relic.access_list),
            selectinload(Relic.tags)
        ).where(Relic.id == relic_id)
    )
    original = result.scalar_one_or_none()

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
        if not check_ownership_or_admin(original, user, require_auth=False):
            allowed_ids = {a.user_id for a in original.access_list}
            if not user or user.id not in allowed_ids:
                raise HTTPException(status_code=403, detail="Access restricted")

    s3_key = None
    try:
        # Generate unique new ID with collision handling
        new_id = await generate_unique_relic_id(db)
        s3_key = f"relics/{new_id}"

        if file:
            # New content provided: stream it to storage
            content_type = file.content_type or original.content_type
            size_bytes = await storage_service.upload_stream(
                s3_key, file.read, content_type, max_size=settings.MAX_UPLOAD_SIZE
            )
        else:
            # Same content: server-side S3 copy, no data flows through the app
            content_type = original.content_type
            size_bytes = original.size_bytes or 0
            await storage_service.copy(original.s3_key, s3_key, size_bytes, content_type)

        # Calculate expiry date if provided
        expires_at = None
        if expires_in and expires_in != 'never':
            expires_at = parse_expiry_string(expires_in)

        # Process tags: use provided tags or copy from original
        if tags is not None:
            tag_objects = await process_tags(db, tags)
        else:
            tag_objects = list(original.tags)

        # Create fork
        fork = Relic(
            id=new_id,
            user_id=user.id if user else None,  # Fork belongs to user if provided
            name=name or original.name,
            content_type=content_type,
            language_hint=original.language_hint,
            size_bytes=size_bytes,
            s3_key=s3_key,
            fork_of=relic_id,
            access_level=access_level or original.access_level,
            expires_at=expires_at
        )

        # Associate tags
        if tag_objects:
            fork.tags = tag_objects

        # Update user relic count (flushed with commit)
        if user:
            user.relic_count += 1

        db.add(fork)
        await db.commit()

        return {
            "id": fork.id,
            "name": fork.name,
            "content_type": fork.content_type,
            "language_hint": fork.language_hint,
            "url": f"/{fork.id}",
            "fork_of": fork.fork_of,
            "created_at": fork.created_at
        }

    except HTTPException:
        raise
    except FileTooLargeError:
        raise HTTPException(status_code=413, detail="File too large")
    except Exception as e:
        await db.rollback()
        logger.error(f"Operation failed: {e}")
        if s3_key:
            try:
                await storage_service.delete(s3_key)
            except Exception:
                logger.warning(f"Failed to clean up orphaned S3 object {s3_key}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/api/v1/relics/{relic_id}/lineage")
async def get_relic_lineage(relic_id: str, max_nodes: int = 200, db: AsyncSession = Depends(get_db)):
    """Get the fork lineage tree for a relic."""
    max_nodes = min(max(max_nodes, 1), 5000)
    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    current = result.scalar_one_or_none()
    if not current:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Walk up to root — O(depth) queries, typically very shallow
    visited_up = set()
    root_id = current.id
    current_relic = current
    while current_relic.fork_of and current_relic.fork_of not in visited_up:
        visited_up.add(current_relic.fork_of)
        parent_result = await db.execute(select(Relic).where(Relic.id == current_relic.fork_of))
        parent = parent_result.scalar_one_or_none()
        if not parent:
            break
        root_id = parent.id
        current_relic = parent

    root_result = await db.execute(select(Relic).where(Relic.id == root_id))
    root_relic_obj = root_result.scalar_one_or_none()
    if not root_relic_obj:
        return {"current_relic_id": relic_id, "root": None, "total_nodes": 0, "truncated": False}

    tree_nodes = {
        root_id: {"id": root_relic_obj.id, "name": root_relic_obj.name, "created_at": root_relic_obj.created_at, "children": []}
    }

    # Level-by-level BFS with batched IN queries — O(depth) queries regardless of tree size
    current_level_ids = [root_id]
    truncated = False

    while current_level_ids:
        children_result = await db.execute(
            select(Relic).where(Relic.fork_of.in_(current_level_ids))
        )
        children = [c for c in children_result.scalars().all() if c.id not in tree_nodes]
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
    db: AsyncSession = Depends(get_db)
):
    """
    Update relic metadata.

    Only owner or admin can update.
    """
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(
        select(Relic).options(selectinload(Relic.tags), joinedload(Relic.owner)).where(Relic.id == relic_id)
    )
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, user):
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
        relic.tags = await process_tags(db, update.tags)

    await db.commit()
    await db.refresh(relic)

    relic.can_edit = True
    return relic


@router.delete("/api/v1/relics/{relic_id}")
async def delete_relic(relic_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Delete a relic (hard delete).

    Only owner OR admin can delete.
    """
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="User key required")

    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Check ownership OR admin privileges
    if not check_ownership_or_admin(relic, user, require_auth=False):
        raise HTTPException(status_code=403, detail="Not authorized to delete this relic")

    # Store user_id before deletion
    relic_user_id = relic.user_id
    was_owner = user and user.id == relic.user_id

    # Delete file from S3 storage
    try:
        await storage_service.delete(relic.s3_key)
    except Exception as e:
        # Log error but don't fail the delete operation
        logger.error(f"Failed to delete file from S3 for relic {relic_id}: {e}", exc_info=True)

    # Hard delete in database
    await db.delete(relic)

    # Update owner's relic count atomically (not admin's count if admin is deleting)
    if relic_user_id:
        await db.execute(
            update(User)
            .where(User.id == relic_user_id, User.relic_count > 0)
            .values(relic_count=User.relic_count - 1)
        )

    await db.commit()

    logger.info(f"Relic {relic_id} deleted successfully by {'owner' if was_owner else 'admin'}")

    return {"message": "Relic deleted successfully"}


@router.get("/api/v1/relics", response_model=RelicListResponse)
async def list_relics(
    limit: int = 25,
    offset: int = 0,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    """List the most recent public relics with pagination."""
    limit = clamp_limit(limit)
    offset = max(0, offset)
    stmt = select(Relic).options(selectinload(Relic.tags), joinedload(Relic.owner)).where(Relic.access_level == "public")

    if tag:
        tag_result = await db.execute(select(Tag).where(Tag.name == tag.strip().lower()))
        tag_obj = tag_result.scalar_one_or_none()
        if tag_obj:
            stmt = stmt.where(Relic.tags.contains(tag_obj))
        else:
            return {"relics": [], "total": 0, "limit": limit, "offset": offset}

    if search:
        stmt = apply_relic_search(stmt, search)

    order = relic_sort_order(sort_by, sort_order)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar()

    relics_result = await db.execute(stmt.order_by(order).offset(offset).limit(limit))
    relics = relics_result.scalars().all()

    relic_ids = [r.id for r in relics]
    comments_counts = {}

    if relic_ids:
        comments_result = await db.execute(
            select(Comment.relic_id, func.count(Comment.id))
            .where(Comment.relic_id.in_(relic_ids))
            .group_by(Comment.relic_id)
        )
        comments_counts = {row[0]: row[1] for row in comments_result.all()}

    forks_counts = await get_fork_counts(db, relic_ids)

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
    db: AsyncSession = Depends(get_db)
):
    """List users with explicit access to a restricted relic. Owner/admin only."""
    limit = clamp_limit(limit)
    offset = max(0, offset)
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, user):
        raise HTTPException(status_code=403, detail="Not authorized")

    access_stmt = select(RelicAccess).join(RelicAccess.user).options(
        contains_eager(RelicAccess.user)
    ).where(RelicAccess.relic_id == relic_id)

    if search:
        term = like_term(search)
        access_stmt = access_stmt.where(
            or_(User.name.ilike(term), User.public_id.ilike(term))
        )

    total_result = await db.execute(select(func.count()).select_from(access_stmt.subquery()))
    total = total_result.scalar()

    entries_result = await db.execute(
        access_stmt.order_by(RelicAccess.created_at).offset(offset).limit(limit)
    )
    entries = entries_result.scalars().all()

    return {
        "access": [
            RelicAccessEntry(
                public_id=e.user.public_id if e.user else None,
                user_name=e.user.name if e.user else None,
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
    db: AsyncSession = Depends(get_db)
):
    """Add a user to a relic's access list by public_id. Owner/admin only."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, user):
        raise HTTPException(status_code=403, detail="Not authorized")

    target_result = await db.execute(select(User).where(User.public_id == body.public_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for duplicate
    existing_result = await db.execute(
        select(RelicAccess).where(
            RelicAccess.relic_id == relic_id,
            RelicAccess.user_id == target.id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already has access")

    access_entry = RelicAccess(relic_id=relic_id, user_id=target.id)
    db.add(access_entry)
    await db.commit()

    return RelicAccessEntry(
        public_id=target.public_id,
        user_name=target.name,
        created_at=access_entry.created_at
    )


@router.delete("/api/v1/relics/{relic_id}/access/{public_id}")
async def remove_relic_access(
    relic_id: str,
    public_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Remove a user from a relic's access list by public_id. Owner/admin only."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not check_ownership_or_admin(relic, user):
        raise HTTPException(status_code=403, detail="Not authorized")

    target_result = await db.execute(select(User).where(User.public_id == public_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    entry_result = await db.execute(
        select(RelicAccess).where(
            RelicAccess.relic_id == relic_id,
            RelicAccess.user_id == target.id
        )
    )
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Access entry not found")

    await db.delete(entry)
    await db.commit()

    return {"message": "Access removed"}
