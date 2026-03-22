"""Client registration and management endpoints."""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload
from datetime import datetime
from typing import Optional
import secrets

from backend.database import get_db
from backend.models import Relic, ClientKey, Tag, Comment
from backend.schemas import ClientNameUpdate
from backend.dependencies import get_client_key
from backend.utils import get_fork_counts, clamp_limit, like_term

router = APIRouter(prefix="/api/v1/client")


def generate_public_id(db: Session) -> str:
    """Generate a unique 16-char hex public_id, retrying on collision."""
    for _ in range(10):
        pid = secrets.token_hex(8)
        if not db.query(ClientKey).filter(ClientKey.public_id == pid).first():
            return pid
    raise RuntimeError("Failed to generate unique public_id after 10 attempts")


@router.post("/register", response_model=dict)
async def register_client(request: Request, db: Session = Depends(get_db)):
    """
    Register a new client key.

    If the client key already exists, returns the existing client.
    If not, creates a new client record.
    """
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        raise HTTPException(status_code=400, detail="X-Client-Key header required")

    # Check if client already exists
    existing_client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    if existing_client:
        # Lazily generate public_id for existing clients that don't have one
        if not existing_client.public_id:
            existing_client.public_id = generate_public_id(db)
            db.commit()
        return {
            "client_id": existing_client.id,
            "public_id": existing_client.public_id,
            "name": existing_client.name,
            "created_at": existing_client.created_at,
            "relic_count": existing_client.relic_count,
            "message": "Client already registered"
        }

    # Create new client
    client = ClientKey(
        id=x_client_key,
        public_id=generate_public_id(db),
        created_at=datetime.utcnow()
    )
    db.add(client)
    db.commit()

    return {
        "client_id": client.id,
        "public_id": client.public_id,
        "created_at": client.created_at,
        "relic_count": 0,
        "message": "Client registered successfully"
    }


@router.get("/relics", response_model=dict)
async def get_client_relics(
    request: Request,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get relics owned by this client with pagination.

    Requires valid X-Client-Key header.
    """
    limit = clamp_limit(limit)
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    query = db.query(Relic).options(selectinload(Relic.tags)).filter(
        Relic.client_id == client.id
    )

    if tag:
        tag_obj = db.query(Tag).filter(Tag.name == tag.strip().lower()).first()
        if tag_obj:
            query = query.filter(Relic.tags.contains(tag_obj))
        else:
            return {
                "client_id": client.id,
                "relic_count": 0,
                "relics": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }

    if search:
        term = like_term(search)
        tag_subquery = db.query(Relic.id).join(Relic.tags).filter(Tag.name.ilike(term)).subquery()
        query = query.filter(
            or_(Relic.name.ilike(term), Relic.id.ilike(term), Relic.description.ilike(term), Relic.id.in_(tag_subquery))
        ).distinct()

    sort_map = {
        "created_at": Relic.created_at,
        "name": Relic.name,
        "size": Relic.size_bytes,
        "access_count": Relic.access_count,
        "bookmark_count": Relic.bookmark_count,
    }
    sort_col = sort_map.get(sort_by, Relic.created_at)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    total = query.count()
    relics = query.order_by(order).offset(offset).limit(limit).all()

    # Fetch all counts in bulk (2 queries instead of N*2)
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

    return {
        "client_id": client.id,
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
                "tags": [{"id": t.id, "name": t.name} for t in relic.tags]
            }
            for relic in relics
        ]
    }


@router.put("/name", response_model=dict)
async def update_client_name(
    name_update: ClientNameUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update the client's display name."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Authentication required")

    client.name = name_update.name
    db.commit()

    return {"status": "updated", "name": client.name}
