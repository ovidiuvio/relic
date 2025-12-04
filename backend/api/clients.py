from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from backend.models import ClientKey, Relic
from backend.services.clients import get_client_key

router = APIRouter()

@router.post("/client/register", response_model=dict)
async def register_client(request: Request, db: Session = Depends(get_db)):
    """Register a new client key."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        raise HTTPException(status_code=400, detail="X-Client-Key header required")
    existing_client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    if existing_client:
        return {
            "client_id": existing_client.id,
            "created_at": existing_client.created_at,
            "relic_count": existing_client.relic_count,
            "message": "Client already registered"
        }
    client = ClientKey(id=x_client_key, created_at=datetime.utcnow())
    db.add(client)
    db.commit()
    return {
        "client_id": client.id,
        "created_at": client.created_at,
        "relic_count": 0,
        "message": "Client registered successfully"
    }

@router.get("/client/relics", response_model=dict)
async def get_client_relics(request: Request, db: Session = Depends(get_db)):
    """Get all relics owned by this client."""
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")
    relics = db.query(Relic).filter(
        Relic.client_id == client.id,
        Relic.deleted_at.is_(None)
    ).order_by(Relic.created_at.desc()).all()
    return {
        "client_id": client.id,
        "relic_count": len(relics),
        "relics": [
            {
                "id": relic.id,
                "name": relic.name,
                "content_type": relic.content_type,
                "size_bytes": relic.size_bytes,
                "created_at": relic.created_at,
                "access_level": relic.access_level
            }
            for relic in relics
        ]
    }
