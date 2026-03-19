"""Bookmark endpoints."""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from datetime import datetime

from backend.database import get_db
from backend.models import Relic, ClientBookmark, Comment
from backend.dependencies import get_client_key

router = APIRouter(prefix="/api/v1/bookmarks")


@router.post("", response_model=dict)
async def add_bookmark(
    request: Request,
    relic_id: str,
    db: Session = Depends(get_db)
):
    """
    Add a bookmark for the authenticated client.

    Requires valid X-Client-Key header.
    Returns bookmark details or error if already bookmarked.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    # Verify relic exists and is not deleted
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Check if already bookmarked
    existing = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Relic already bookmarked")

    # Create bookmark
    bookmark = ClientBookmark(
        client_id=client.id,
        relic_id=relic_id,
        created_at=datetime.utcnow()
    )

    # Increment bookmark count
    relic.bookmark_count += 1

    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

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
    db: Session = Depends(get_db)
):
    """
    Remove a bookmark for the authenticated client.

    Requires valid X-Client-Key header.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    # Find bookmark
    bookmark = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if relic and relic.bookmark_count > 0:
        relic.bookmark_count -= 1

    db.delete(bookmark)
    db.commit()

    return {"message": "Bookmark removed successfully"}


@router.get("/check/{relic_id}")
async def check_bookmark(
    relic_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Check if a relic is bookmarked by the authenticated client.

    Requires valid X-Client-Key header.
    Returns bookmarked status.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    bookmark = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()

    return {
        "relic_id": relic_id,
        "is_bookmarked": bookmark is not None,
        "bookmark_id": bookmark.id if bookmark else None
    }


@router.get("", response_model=dict)
async def get_client_bookmarks(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get all bookmarks for the authenticated client.

    Requires valid X-Client-Key header.
    Returns list of bookmarked relics with bookmark metadata.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    # Join bookmarks with relics, exclude deleted relics, and eagerly load tags
    bookmarks = db.query(ClientBookmark, Relic).join(
        Relic, ClientBookmark.relic_id == Relic.id
    ).options(selectinload(Relic.tags)).filter(
        ClientBookmark.client_id == client.id
    ).order_by(ClientBookmark.created_at.desc()).all()

    # Fetch all counts in bulk (2 queries instead of N*2)
    relic_ids = [relic.id for _, relic in bookmarks]
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

    return {
        "client_id": client.id,
        "bookmark_count": len(bookmarks),
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
                "tags": [{"id": t.id, "name": t.name} for t in relic.tags]
            }
            for bookmark, relic in bookmarks
        ]
    }
