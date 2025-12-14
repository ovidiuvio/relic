from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models import ClientKey, Relic
from datetime import datetime

# ==================== Client Key Functions ====================

def get_client_key(request: Request, db: Session = Depends(get_db)) -> Optional[ClientKey]:
    """Extract and validate client key from request headers."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None

    client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    return client


def get_or_create_client_key(request: Request, db: Session = Depends(get_db)) -> Optional[ClientKey]:
    """Get existing client or create new one if key provided."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None

    # Try to get existing client
    client = db.query(ClientKey).filter(ClientKey.id == x_client_key).first()
    if client:
        return client

    # Create new client if it doesn't exist
    client = ClientKey(
        id=x_client_key,
        created_at=datetime.utcnow()
    )
    db.add(client)
    db.commit()
    return client


# ==================== Admin Authorization ====================

def is_admin_client(client: Optional[ClientKey]) -> bool:
    """
    Check if a client has admin privileges.

    A client is admin if their ID is in the ADMIN_CLIENT_IDS config.
    """
    if not client:
        return False
    return client.id in settings.get_admin_client_ids()


def get_admin_client(request: Request, db: Session = Depends(get_db)) -> ClientKey:
    """
    Get client and verify admin privileges.

    Raises HTTPException if not authenticated or not admin.
    """
    client = get_client_key(request, db)
    if not client:
        raise HTTPException(
            status_code=401,
            detail="Client key required"
        )
    if not is_admin_client(client):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return client


def check_ownership_or_admin(
    relic: Relic,
    client: Optional[ClientKey],
    require_auth: bool = True
) -> bool:
    """
    Check if client owns the relic or is an admin.

    Args:
        relic: The relic to check ownership for
        client: The client making the request
        require_auth: If True, require authentication

    Returns:
        True if client owns relic or is admin

    Raises:
        HTTPException: If require_auth is True and client is None
    """
    if require_auth and not client:
        raise HTTPException(
            status_code=401,
            detail="Client key required"
        )

    if not client:
        return False

    # Admin can do anything
    if is_admin_client(client):
        return True

    # Owner check
    return relic.client_id == client.id
