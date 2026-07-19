"""Bookmark endpoints."""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime
from typing import Optional

from backend.database import get_db
from backend.models import Relic, UserBookmark, Comment, User, Tag
from backend.dependencies import get_current_user
from backend.utils import get_fork_counts, clamp_limit, apply_relic_search, relic_sort_order

router = APIRouter(prefix="/api/v1/bookmarks")


@router.post("", response_model=dict)
async def add_bookmark(
    request: Request,
    relic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a bookmark for the authenticated user.

    Requires valid X-User-Key header.
    Returns bookmark details or error if already bookmarked.
    """
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")

    # Verify relic exists and is not deleted
    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Check if already bookmarked
    existing_result = await db.execute(
        select(UserBookmark).where(
            UserBookmark.user_id == user.id,
            UserBookmark.relic_id == relic_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Relic already bookmarked")

    # Create bookmark
    bookmark = UserBookmark(
        user_id=user.id,
        relic_id=relic_id,
        created_at=datetime.utcnow()
    )

    # Increment bookmark count atomically
    await db.execute(
        update(Relic).where(Relic.id == relic_id).values(bookmark_count=Relic.bookmark_count + 1)
    )

    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)

    return {
        "id": bookmark.id,
        "relic_id": bookmark.relic_id,
        "created_at": bookmark.created_at,
        "message": "Bookmark added successfully"
    }


@router.delete("/{relic_id}")
async def remove_bookmark(
    relic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a bookmark for the authenticated user.

    Requires valid X-User-Key header.
    """
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")

    # Find bookmark
    result = await db.execute(
        select(UserBookmark).where(
            UserBookmark.user_id == user.id,
            UserBookmark.relic_id == relic_id
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    # Decrement bookmark count atomically
    await db.execute(
        update(Relic)
        .where(Relic.id == relic_id, Relic.bookmark_count > 0)
        .values(bookmark_count=Relic.bookmark_count - 1)
    )

    await db.delete(bookmark)
    await db.commit()

    return {"message": "Bookmark removed successfully"}


@router.get("/check/{relic_id}")
async def check_bookmark(
    relic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a relic is bookmarked by the authenticated user.

    Requires valid X-User-Key header.
    Returns bookmarked status.
    """
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")

    result = await db.execute(
        select(UserBookmark).where(
            UserBookmark.user_id == user.id,
            UserBookmark.relic_id == relic_id
        )
    )
    bookmark = result.scalar_one_or_none()

    return {
        "relic_id": relic_id,
        "is_bookmarked": bookmark is not None,
        "bookmark_id": bookmark.id if bookmark else None
    }


@router.get("", response_model=dict)
async def get_user_bookmarks(
    request: Request,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 25,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Get bookmarks for the authenticated user with pagination.

    Requires valid X-User-Key header.
    Returns list of bookmarked relics with bookmark metadata.
    sort_by: created_at (bookmarked date), name, size, access_count, bookmark_count
    """
    limit = clamp_limit(limit)
    offset = max(0, offset)
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Valid user key required")

    stmt = select(UserBookmark, Relic).join(
        Relic, UserBookmark.relic_id == Relic.id
    ).options(
        selectinload(Relic.tags),
        joinedload(Relic.owner)
    ).where(
        UserBookmark.user_id == user.id
    )

    if tag:
        tag_result = await db.execute(select(Tag).where(Tag.name == tag.strip().lower()))
        tag_obj = tag_result.scalar_one_or_none()
        if tag_obj:
            stmt = stmt.where(Relic.tags.contains(tag_obj))
        else:
            return {
                "user_id": user.id,
                "bookmark_count": 0,
                "bookmarks": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }

    if search:
        stmt = apply_relic_search(stmt, search)

    order = relic_sort_order(sort_by, sort_order, {"created_at": UserBookmark.created_at})

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar()

    rows = (await db.execute(stmt.order_by(order).offset(offset).limit(limit))).all()

    relic_ids = [relic.id for _, relic in rows]
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
        "bookmark_count": total,
        "total": total,
        "limit": limit,
        "offset": offset,
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
                "comments_count": comments_counts.get(relic.id, 0),
                "forks_count": forks_counts.get(relic.id, 0),
                "bookmark_id": bookmark.id,
                "bookmarked_at": bookmark.created_at,
                "owner_name": relic.owner_name,
                "owner_public_id": relic.owner_public_id,
                "tags": [{"id": t.id, "name": t.name} for t in relic.tags]
            }
            for bookmark, relic in rows
        ]
    }


@router.get("/{relic_id}/bookmarkers", response_model=dict)
async def get_relic_bookmarkers(
    relic_id: str,
    limit: int = 25,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of users who bookmarked a specific relic with pagination.
    Returns public_id and names, sorted by most recent first.
    """
    limit = clamp_limit(limit)
    offset = max(0, offset)

    stmt = select(User, UserBookmark).join(
        UserBookmark, UserBookmark.user_id == User.id
    ).where(UserBookmark.relic_id == relic_id)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar()

    rows = (await db.execute(
        stmt.order_by(UserBookmark.created_at.desc()).offset(offset).limit(limit)
    )).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "bookmarkers": [
            {
                "public_id": u.public_id,
                "name": u.name or "Anonymous",
                "bookmarked_at": b.created_at
            }
            for u, b in rows
        ]
    }
