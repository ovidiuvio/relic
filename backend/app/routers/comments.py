from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from backend.app.core.database import get_db
from backend.app.models import Comment, Relic, ClientKey
from backend.app.schemas import CommentCreate, CommentResponse, CommentUpdate
from backend.app.api.deps import get_client_key, is_admin_client

router = APIRouter()

@router.post("/{relic_id}/comments", response_model=CommentResponse)
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


@router.get("/{relic_id}/comments", response_model=List[CommentResponse])
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


@router.put("/{relic_id}/comments/{comment_id}", response_model=CommentResponse)
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


@router.delete("/{relic_id}/comments/{comment_id}")
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
