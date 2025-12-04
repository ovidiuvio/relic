from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from backend.models import ClientKey

def get_client_key(request: Request, db: Session) -> Optional[ClientKey]:
    """Extract and validate client key from request headers."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None
    client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    return client

def get_or_create_client_key(request: Request, db: Session) -> Optional[ClientKey]:
    """Get existing client or create new one if key provided."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None
    client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    if client:
        return client
    client = ClientKey(id=x_client_key, created_at=datetime.utcnow())
    db.add(client)
    db.commit()
    return client
