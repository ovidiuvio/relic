"""Space endpoints."""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import func, or_, and_, case, select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, contains_eager
from datetime import datetime
from typing import Optional, List

from backend.config import settings
from backend.database import get_db
from backend.models import Relic, ClientKey, Space, SpaceAccess, space_relics, Comment, Tag
from backend.schemas import (
    RelicListResponse, SpaceCreate, SpaceUpdate, SpaceResponse,
    SpaceAccessBase, SpaceAccessResponse, SpaceTransferOwnership
)
from backend.utils import generate_relic_id, get_fork_counts, clamp_limit, like_term, apply_relic_search, relic_sort_order
from backend.dependencies import get_client_key, get_space_role, check_space_access, get_space_relic_count

router = APIRouter(prefix="/api/v1/spaces")


@router.post("", response_model=SpaceResponse)
async def create_space(
    space_in: SpaceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new space."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")

    space = Space(
        id=generate_relic_id(),
        name=space_in.name,
        visibility=space_in.visibility,
        owner_client_id=client.id
    )

    db.add(space)
    await db.commit()
    await db.refresh(space)

    return {
        "id": space.id,
        "name": space.name,
        "visibility": space.visibility,
        "owner_client_id": space.owner_client_id,
        "created_at": space.created_at,
        "relic_count": 0,
        "role": "owner"
    }

@router.get("", response_model=dict)
async def list_spaces(
    request: Request,
    visibility: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List spaces with server-side filtering, sorting, and pagination.
    If authenticated: returns public spaces + private spaces user has access to.
    If anonymous: returns only public spaces.
    category: all, my, shared, public
    sort_by: created_at, name, relic_count
    """
    limit = clamp_limit(limit, default=50)
    offset = max(0, offset)
    client_id = request.headers.get("X-Client-Key")
    is_admin = client_id and client_id in settings.get_admin_client_ids()

    stmt = select(Space).options(selectinload(Space.access_list))

    access_sq = (
        select(SpaceAccess.space_id).where(SpaceAccess.client_id == client_id).scalar_subquery()
    ) if client_id else None

    # Apply visibility filter at SQL level
    if not is_admin:
        if access_sq is not None:
            stmt = stmt.where(
                or_(
                    Space.visibility == "public",
                    Space.owner_client_id == client_id,
                    Space.id.in_(access_sq)
                )
            )
        else:
            stmt = stmt.where(Space.visibility == "public")

    # Optional direct visibility filter
    if visibility:
        stmt = stmt.where(Space.visibility == visibility)

    # Category filter
    if category == "my" and client_id:
        stmt = stmt.where(Space.owner_client_id == client_id)
    elif category == "shared" and client_id:
        shared_sq = select(SpaceAccess.space_id).where(
            SpaceAccess.client_id == client_id
        ).scalar_subquery()
        stmt = stmt.where(
            Space.id.in_(shared_sq),
            Space.owner_client_id != client_id
        )
    elif category == "public":
        stmt = stmt.where(Space.visibility == "public")

    # Search
    if search:
        term = like_term(search)
        stmt = stmt.where(or_(Space.name.ilike(term), Space.id.ilike(term)))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar()

    if sort_by == "priority" and access_sq is not None:
        priority_expr = case(
            (Space.owner_client_id == client_id, 1),
            (and_(Space.id.in_(access_sq), Space.visibility == "private"), 2),
            else_=3
        )
        spaces_result = await db.execute(
            stmt.order_by(priority_expr, Space.created_at.desc()).offset(offset).limit(limit)
        )
    else:
        if sort_by == "relic_count":
            relic_count_subq = (
                select(space_relics.c.space_id, func.count(space_relics.c.relic_id).label("cnt"))
                .group_by(space_relics.c.space_id)
                .subquery()
            )
            stmt = stmt.outerjoin(relic_count_subq, Space.id == relic_count_subq.c.space_id)
            sort_col = func.coalesce(relic_count_subq.c.cnt, 0)
        elif sort_by == "name":
            sort_col = Space.name
        else:
            sort_col = Space.created_at
        order = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        spaces_result = await db.execute(stmt.order_by(order).offset(offset).limit(limit))

    spaces = spaces_result.scalars().all()

    # Bulk relic count for this page only
    space_ids = [s.id for s in spaces]
    relic_counts = {}
    if space_ids:
        rc_result = await db.execute(
            select(space_relics.c.space_id, func.count(space_relics.c.relic_id))
            .where(space_relics.c.space_id.in_(space_ids))
            .group_by(space_relics.c.space_id)
        )
        relic_counts = dict(rc_result.all())

    result = []
    for space in spaces:
        role = get_space_role(space, client_id)
        result.append({
            "id": space.id,
            "name": space.name,
            "visibility": space.visibility,
            "owner_client_id": space.owner_client_id,
            "created_at": space.created_at,
            "relic_count": relic_counts.get(space.id, 0),
            "role": role
        })

    return {"spaces": result, "total": total, "limit": limit, "offset": offset}

@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(
    space_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get space details."""
    client_id = request.headers.get("X-Client-Key")

    result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not check_space_access(space, client_id, "viewer"):
        raise HTTPException(status_code=403, detail="Not authorized to view this space")

    return {
        "id": space.id,
        "name": space.name,
        "visibility": space.visibility,
        "owner_client_id": space.owner_client_id,
        "created_at": space.created_at,
        "relic_count": await get_space_relic_count(space.id, db),
        "role": get_space_role(space, client_id)
    }

@router.put("/{space_id}", response_model=SpaceResponse)
async def update_space(
    space_id: str,
    space_in: SpaceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update space metadata."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")
    client_id = client.id

    result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner or admin can update space metadata
    is_admin = client_id in settings.get_admin_client_ids()
    if space.owner_client_id != client_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this space")

    if space_in.name is not None:
        space.name = space_in.name
    if space_in.visibility is not None:
        space.visibility = space_in.visibility

    await db.commit()
    await db.refresh(space)

    return {
        "id": space.id,
        "name": space.name,
        "visibility": space.visibility,
        "owner_client_id": space.owner_client_id,
        "created_at": space.created_at,
        "relic_count": await get_space_relic_count(space.id, db),
        "role": get_space_role(space, client_id)
    }

@router.post("/{space_id}/transfer-ownership", response_model=SpaceResponse)
async def transfer_space_ownership(
    space_id: str,
    transfer_in: SpaceTransferOwnership,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Transfer space ownership to another user. Only the current owner or a system admin can do this."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")
    client_id = client.id

    result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    is_admin = client_id in settings.get_admin_client_ids()
    if space.owner_client_id != client_id and not is_admin:
        raise HTTPException(status_code=403, detail="Only the space owner or a system admin can transfer ownership")

    # Resolve new owner by public_id
    new_owner_result = await db.execute(
        select(ClientKey).where(ClientKey.public_id == transfer_in.public_id)
    )
    new_owner = new_owner_result.scalar_one_or_none()
    if not new_owner:
        raise HTTPException(status_code=404, detail="No user found with that Public ID")

    if new_owner.id == space.owner_client_id:
        raise HTTPException(status_code=400, detail="This user is already the owner")

    # Add old owner to SpaceAccess as admin so they keep access
    old_access_result = await db.execute(
        select(SpaceAccess).where(
            SpaceAccess.space_id == space_id,
            SpaceAccess.client_id == space.owner_client_id
        )
    )
    if not old_access_result.scalar_one_or_none():
        db.add(SpaceAccess(space_id=space_id, client_id=space.owner_client_id, role="admin"))

    # Remove new owner from SpaceAccess if they were a member (they become the owner now)
    new_owner_access_result = await db.execute(
        select(SpaceAccess).where(
            SpaceAccess.space_id == space_id,
            SpaceAccess.client_id == new_owner.id
        )
    )
    new_owner_access = new_owner_access_result.scalar_one_or_none()
    if new_owner_access:
        await db.delete(new_owner_access)

    # Transfer ownership
    space.owner_client_id = new_owner.id
    await db.commit()
    await db.refresh(space)

    return {
        "id": space.id,
        "name": space.name,
        "visibility": space.visibility,
        "owner_client_id": space.owner_client_id,
        "created_at": space.created_at,
        "relic_count": await get_space_relic_count(space.id, db),
        "role": get_space_role(space, client_id)
    }


@router.delete("/{space_id}")
async def delete_space(
    space_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete a space."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")
    client_id = client.id

    result = await db.execute(select(Space).where(Space.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner or admin can delete space
    is_admin = client_id in settings.get_admin_client_ids()
    if space.owner_client_id != client_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this space")

    await db.delete(space)
    await db.commit()
    return {"message": "Space deleted successfully"}

@router.get("/{space_id}/relics", response_model=dict)
async def get_space_relics(
    space_id: str,
    request: Request,
    limit: int = 25,
    offset: int = 0,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    """Get relics in a space with pagination."""
    limit = clamp_limit(limit)
    offset = max(0, offset)
    client_id = request.headers.get("X-Client-Key")
    is_admin = client_id in settings.get_admin_client_ids() if client_id else False

    space_result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = space_result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not check_space_access(space, client_id, "viewer"):
        raise HTTPException(status_code=403, detail="Not authorized to view this space")

    stmt = select(Relic).options(selectinload(Relic.tags)).join(
        space_relics, Relic.id == space_relics.c.relic_id
    ).where(
        space_relics.c.space_id == space_id
    ).where(
        or_(Relic.expires_at.is_(None), Relic.expires_at > datetime.utcnow())
    )

    if space.visibility == "public":
        # Public spaces only show public relics
        stmt = stmt.where(Relic.access_level == "public")

    if tag:
        tag_result = await db.execute(select(Tag).where(Tag.name == tag.strip().lower()))
        tag_obj = tag_result.scalar_one_or_none()
        if tag_obj:
            stmt = stmt.where(Relic.tags.contains(tag_obj))
        else:
            stmt = stmt.where(False)

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

    result = []
    for relic in relics:
        can_edit = client_id is not None and (relic.client_id == client_id or is_admin)
        result.append({
            "id": relic.id,
            "name": relic.name,
            "description": relic.description,
            "content_type": relic.content_type,
            "language_hint": relic.language_hint,
            "size_bytes": relic.size_bytes,
            "fork_of": relic.fork_of,
            "access_level": relic.access_level,
            "created_at": relic.created_at,
            "expires_at": relic.expires_at,
            "access_count": relic.access_count,
            "bookmark_count": relic.bookmark_count,
            "comments_count": comments_counts.get(relic.id, 0),
            "forks_count": forks_counts.get(relic.id, 0),
            "can_edit": can_edit,
            "tags": [{"name": t.name, "id": t.id} for t in relic.tags]
        })

    return {"relics": result, "total": total, "limit": limit, "offset": offset}

@router.post("/{space_id}/relics")
async def add_relic_to_space(
    space_id: str,
    relic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Add a relic to a space."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")
    client_id = client.id

    space_result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = space_result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    relic_result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = relic_result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Must have edit access to space
    if not check_space_access(space, client_id, "editor"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this space")

    # Must have access to relic (either public, owner, or admin)
    is_admin = client_id in settings.get_admin_client_ids()
    if relic.access_level in ("private", "restricted"):
        if space.visibility == "public":
            raise HTTPException(status_code=400, detail="Cannot add private or restricted relics to a public space")
        if relic.client_id != client_id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this relic")

    await db.execute(pg_insert(space_relics).values(space_id=space_id, relic_id=relic_id).on_conflict_do_nothing())
    await db.commit()

    return {"message": "Relic added to space successfully"}

@router.delete("/{space_id}/relics/{relic_id}")
async def remove_relic_from_space(
    space_id: str,
    relic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Remove a relic from a space."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")
    client_id = client.id

    space_result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = space_result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    relic_result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = relic_result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Must have edit access to space
    if not check_space_access(space, client_id, "editor"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this space")

    # Direct DELETE on association table — avoids lazy loading space.relics
    await db.execute(
        delete(space_relics).where(
            space_relics.c.space_id == space_id,
            space_relics.c.relic_id == relic_id
        )
    )
    await db.commit()

    return {"message": "Relic removed from space successfully"}

@router.get("/{space_id}/access", response_model=dict)
async def get_space_access(
    space_id: str,
    request: Request,
    limit: int = 25,
    offset: int = 0,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get the access list for a space with pagination and optional search."""
    limit = clamp_limit(limit)
    offset = max(0, offset)
    client_id = request.headers.get("X-Client-Key")

    space_result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = space_result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not check_space_access(space, client_id, "editor"):
        raise HTTPException(status_code=403, detail="Not authorized to view space access list")

    owner_result = await db.execute(select(ClientKey).where(ClientKey.id == space.owner_client_id))
    owner = owner_result.scalar_one_or_none()
    owner_row = {
        "id": space.id,
        "space_id": space.id,
        "public_id": owner.public_id if owner else None,
        "client_name": owner.name if owner else None,
        "role": "owner",
        "created_at": space.created_at,
    }

    access_stmt = (
        select(SpaceAccess)
        .join(SpaceAccess.client)
        .options(contains_eager(SpaceAccess.client))
        .where(SpaceAccess.space_id == space_id)
    )
    if search:
        term = like_term(search)
        access_stmt = access_stmt.where(
            or_(ClientKey.name.ilike(term), ClientKey.public_id.ilike(term))
        )

    access_total_result = await db.execute(select(func.count()).select_from(access_stmt.subquery()))
    access_total = access_total_result.scalar()

    access_entries_result = await db.execute(
        access_stmt.order_by(SpaceAccess.created_at).offset(offset).limit(limit)
    )
    access_entries = access_entries_result.scalars().all()

    access_list = [
        {
            "id": access.id,
            "space_id": access.space_id,
            "public_id": access.client.public_id if access.client else None,
            "client_name": access.client.name if access.client else None,
            "role": access.role,
            "created_at": access.created_at,
        }
        for access in access_entries
    ]

    return {
        "owner": owner_row,
        "access": access_list,
        "total": access_total,
        "limit": limit,
        "offset": offset,
    }

@router.post("/{space_id}/access", response_model=SpaceAccessResponse)
async def add_space_access(
    space_id: str,
    access_in: SpaceAccessBase,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Add or update a user's access to a space."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")
    client_id = client.id

    space_result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = space_result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner or admin can modify access list
    if not check_space_access(space, client_id, "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to modify space access list")

    # Look up target client by public_id
    target_result = await db.execute(
        select(ClientKey).where(ClientKey.public_id == access_in.public_id)
    )
    target_client = target_result.scalar_one_or_none()
    if not target_client:
        raise HTTPException(status_code=404, detail="No user found with that Public ID")

    # Prevent modifying owner's own access
    if target_client.id == space.owner_client_id:
        raise HTTPException(status_code=400, detail="Cannot modify owner access")

    # Check if access already exists
    access_result = await db.execute(
        select(SpaceAccess).where(
            SpaceAccess.space_id == space_id,
            SpaceAccess.client_id == target_client.id
        )
    )
    access = access_result.scalar_one_or_none()

    if access:
        # Update existing
        access.role = access_in.role
    else:
        # Create new
        access = SpaceAccess(
            space_id=space_id,
            client_id=target_client.id,
            role=access_in.role
        )
        db.add(access)

    await db.commit()
    await db.refresh(access)

    return {
        "id": access.id,
        "space_id": access.space_id,
        "public_id": target_client.public_id,
        "client_name": target_client.name,
        "role": access.role,
        "created_at": access.created_at,
    }

@router.delete("/{space_id}/access/{access_id}")
async def remove_space_access(
    space_id: str,
    access_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Remove a user's access from a space."""
    client = await get_client_key(request, db)
    if not client:
        if request.headers.get("X-Client-Key"):
            raise HTTPException(status_code=401, detail="Invalid client key")
        raise HTTPException(status_code=401, detail="Client key required")
    client_id = client.id

    space_result = await db.execute(
        select(Space).options(selectinload(Space.access_list)).where(Space.id == space_id)
    )
    space = space_result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    access_result = await db.execute(
        select(SpaceAccess).where(
            SpaceAccess.id == access_id,
            SpaceAccess.space_id == space_id
        )
    )
    access = access_result.scalar_one_or_none()

    if not access:
        raise HTTPException(status_code=404, detail="Access record not found")

    # Only owner, admin, or the user themselves can remove access
    if access.client_id != client_id and not check_space_access(space, client_id, "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to remove space access")

    await db.delete(access)
    await db.commit()

    return {"message": "Access removed successfully"}
