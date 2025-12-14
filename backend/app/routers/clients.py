from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.models import ClientKey, Relic
from backend.app.schemas import ClientNameUpdate
from backend.app.api.deps import get_client_key

router = APIRouter()

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
        return {
            "client_id": existing_client.id,
            "name": existing_client.name,
            "created_at": existing_client.created_at,
            "relic_count": existing_client.relic_count,
            "message": "Client already registered"
        }

    # Create new client
    client = ClientKey(
        id=x_client_key,
        created_at=datetime.utcnow()
    )
    db.add(client)
    db.commit()

    return {
        "client_id": client.id,
        "created_at": client.created_at,
        "relic_count": 0,
        "message": "Client registered successfully"
    }


@router.get("/relics", response_model=dict)
async def get_client_relics(request: Request, db: Session = Depends(get_db)):
    """
    Get all relics owned by this client.

    Requires valid X-Client-Key header.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(status_code=401, detail="Valid client key required")

    relics = db.query(Relic).filter(
        Relic.client_id == client.id
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
