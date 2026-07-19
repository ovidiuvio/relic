"""Comment endpoints."""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from backend.database import get_db
from backend.models import Relic, User, Comment
from backend.schemas import CommentCreate, CommentResponse, CommentUpdate
from backend.dependencies import get_current_user, is_admin_user
from backend.utils import clamp_limit

router = APIRouter(prefix="/api/v1/relics")


@router.post("/{relic_id}/comments", response_model=CommentResponse)
async def create_comment(
    relic_id: str,
    comment: CommentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a comment on a relic."""
    # Verify relic exists
    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Get user key (optional but recommended)
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to comment")

    if not user.name:
        raise HTTPException(status_code=400, detail="You must set a display name in your profile to comment")

    user_id = user.id

    db_comment = Comment(
        relic_id=relic_id,
        user_id=user_id,
        line_number=comment.line_number,
        content=comment.content,
        parent_id=comment.parent_id
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)

    # Add author name and public_id to response
    response = CommentResponse.from_orm(db_comment)
    response.author_name = user.name
    response.public_id = user.public_id
    return response


@router.get("/{relic_id}/comments", response_model=dict)
async def get_relic_comments(
    relic_id: str,
    line_number: Optional[int] = None,
    limit: int = 1000,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get comments for a relic with pagination."""
    limit = clamp_limit(limit, default=1000)
    offset = max(0, offset)

    result = await db.execute(select(Relic).where(Relic.id == relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    stmt = select(Comment, User.name, User.public_id).outerjoin(
        User, Comment.user_id == User.id
    ).where(Comment.relic_id == relic_id)

    if line_number is not None:
        stmt = stmt.where(Comment.line_number == line_number)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar()

    rows = (await db.execute(
        stmt.order_by(Comment.line_number, Comment.created_at).offset(offset).limit(limit)
    )).all()

    comments = []
    for comment, author_name, public_id in rows:
        comment_resp = CommentResponse.from_orm(comment)
        comment_resp.author_name = author_name
        comment_resp.public_id = public_id
        comments.append(comment_resp)

    return {"comments": comments, "total": total, "limit": limit, "offset": offset}


@router.put("/{relic_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    relic_id: str,
    comment_id: str,
    comment_update: CommentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update a comment (only by the author)."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.relic_id == relic_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check ownership
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this comment")

    comment.content = comment_update.content
    await db.commit()
    await db.refresh(comment)

    response = CommentResponse.from_orm(comment)
    response.author_name = user.name
    response.public_id = user.public_id
    return response


@router.delete("/{relic_id}/comments/{comment_id}")
async def delete_comment(
    relic_id: str,
    comment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment (only by the author or admin)."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.relic_id == relic_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check ownership or admin status
    is_owner = comment.user_id == user.id
    is_admin = is_admin_user(user)

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    await db.delete(comment)
    await db.commit()
    return {"status": "deleted"}
