"""User registration and management endpoints."""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime
from typing import Optional
import secrets

from backend.database import get_db
from backend.models import Relic, User, Tag, Comment
from backend.schemas import UserNameUpdate
from backend.dependencies import get_current_user
from backend.utils import get_fork_counts, clamp_limit, apply_relic_search, relic_sort_order

router = APIRouter(prefix="/api/v1/user")


async def generate_public_id(db: AsyncSession) -> str:
    """Generate a unique 16-char hex public_id, retrying on collision."""
    for _ in range(10):
        pid = secrets.token_hex(8)
        result = await db.execute(select(User).where(User.public_id == pid))
        if not result.scalar_one_or_none():
            return pid
    raise RuntimeError("Failed to generate unique public_id after 10 attempts")


@router.post("/register", response_model=dict)
async def register_user(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Register a new user key.

    If the user key already exists, returns the existing user.
    If not, creates a new user record.
    """
    x_user_key = request.headers.get("X-User-Key")
    if not x_user_key:
        raise HTTPException(status_code=400, detail="X-User-Key header required")

    # Check if user already exists
    result = await db.execute(select(User).where(User.id == x_user_key))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        # Lazily generate public_id for existing users that don't have one
        if not existing_user.public_id:
            existing_user.public_id = await generate_public_id(db)
            await db.commit()
        return {
            "user_id": existing_user.id,
            "public_id": existing_user.public_id,
            "name": existing_user.name,
            "created_at": existing_user.created_at,
            "relic_count": existing_user.relic_count,
            "message": "User already registered"
        }

    # Create new user
    user = User(
        id=x_user_key,
        public_id=await generate_public_id(db),
        created_at=datetime.utcnow()
    )
    db.add(user)
    await db.commit()

    return {
        "user_id": user.id,
        "public_id": user.public_id,
        "created_at": user.created_at,
        "relic_count": 0,
        "message": "User registered successfully"
    }


@router.get("/relics", response_model=dict)
async def get_user_relics(
    request: Request,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    access_level: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 25,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Get relics owned by this user with pagination.

    Requires valid X-User-Key header.
    """
    limit = clamp_limit(limit)
    offset = max(0, offset)
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")

    stmt = select(Relic).options(selectinload(Relic.tags), joinedload(Relic.owner)).where(
        Relic.user_id == user.id
    )

    if access_level:
        if access_level not in ("public", "private", "restricted"):
            raise HTTPException(
                status_code=400,
                detail="Invalid access_level. Must be 'public', 'private', or 'restricted'."
            )
        stmt = stmt.where(Relic.access_level == access_level)

    if tag:
        result = await db.execute(select(Tag).where(Tag.name == tag.strip().lower()))
        tag_obj = result.scalar_one_or_none()
        if tag_obj:
            stmt = stmt.where(Relic.tags.contains(tag_obj))
        else:
            return {
                "user_id": user.id,
                "relic_count": 0,
                "relics": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }

    if search:
        stmt = apply_relic_search(stmt, search)

    order = relic_sort_order(sort_by, sort_order)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar()

    relics_result = await db.execute(stmt.order_by(order).offset(offset).limit(limit))
    relics = relics_result.scalars().all()

    # Fetch all counts in bulk (2 queries instead of N*2)
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

    return {
        "user_id": user.id,
        "relic_count": total,
        "total": total,
        "limit": limit,
        "offset": offset,
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
                "comments_count": comments_counts.get(relic.id, 0),
                "forks_count": forks_counts.get(relic.id, 0),
                "owner_name": relic.owner_name,
                "owner_public_id": relic.owner_public_id,
                "tags": [{"id": t.id, "name": t.name} for t in relic.tags]
            }
            for relic in relics
        ]
    }


@router.put("/name", response_model=dict)
async def update_user_name(
    name_update: UserNameUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update the user's display name."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user.name = name_update.name
    await db.commit()

    return {"status": "updated", "name": user.name}
