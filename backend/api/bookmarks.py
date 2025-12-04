from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from backend.models import ClientBookmark, Relic
from backend.services.clients import get_client_key

router = APIRouter()

@router.post("/bookmarks", response_model=dict)
async def add_bookmark(request: Request, relic_id: str, db: Session = Depends(get_db)):
    """Add a bookmark."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic or relic.deleted_at:
        raise HTTPException(status_code=404, detail="Relic not found")
    existing = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Relic already bookmarked")
    bookmark = ClientBookmark(client_id=client.id, relic_id=relic_id, created_at=datetime.utcnow())
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return {
        "id": bookmark.id,
        "relic_id": bookmark.relic_id,
        "created_at": bookmark.created_at,
        "message": "Bookmark added successfully"
    }

@router.delete("/bookmarks/{relic_id}")
async def remove_bookmark(relic_id: str, request: Request, db: Session = Depends(get_db)):
    """Remove a bookmark."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")
    bookmark = db.query(ClientBookmark).filter(
        ClientBookmark.client_id == client.id,
        ClientBookmark.relic_id == relic_id
    ).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
    return {"message": "Bookmark removed successfully"}

@router.get("/bookmarks/check/{relic_id}")
async def check_bookmark(relic_id: str, request: Request, db: Session = Depends(get_db)):
    """Check if a relic is bookmarked."""
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

@router.get("/bookmarks", response_model=dict)
async def get_client_bookmarks(request: Request, db: Session = Depends(get_db)):
    """Get all bookmarks for a client."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")
    bookmarks = db.query(ClientBookmark, Relic).join(
        Relic, ClientBookmark.relic_id == Relic.id
    ).filter(
        ClientBookmark.client_id == client.id,
        Relic.deleted_at.is_(None)
    ).order_by(ClientBookmark.created_at.desc()).all()
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
                "bookmark_id": bookmark.id,
                "bookmarked_at": bookmark.created_at
            }
            for bookmark, relic in bookmarks
        ]
    }
