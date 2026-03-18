"""Shared dependencies and helper functions for route modules."""
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from sqlalchemy import func

from backend.config import settings
from backend.models import Relic, ClientKey, Tag, Space, space_relics
from backend.utils import generate_relic_id


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


def is_admin_client(client: Optional[ClientKey]) -> bool:
    """
    Check if a client has admin privileges.

    A client is admin if their ID is in the ADMIN_CLIENT_IDS config.
    """
    if not client:
        return False
    return client.id in settings.get_admin_client_ids()


def get_admin_client(request: Request, db: Session) -> ClientKey:
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


def process_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    """Process a list of tag names and return Tag objects (creating new ones if needed)."""
    if not tag_names:
        return []

    # Normalize tags
    normalized_names = sorted(list(set(name.strip().lower() for name in tag_names if name.strip())))

    if not normalized_names:
        return []

    # Find existing tags
    existing_tags = db.query(Tag).filter(Tag.name.in_(normalized_names)).all()
    existing_names = {tag.name for tag in existing_tags}

    result_tags = list(existing_tags)

    # Create new tags
    for name in normalized_names:
        if name not in existing_names:
            new_tag = Tag(name=name)
            db.add(new_tag)
            result_tags.append(new_tag)

    return result_tags


def generate_unique_relic_id(db: Session, max_retries: int = 5) -> str:
    """
    Generate a unique relic ID with collision handling.

    Attempts to generate a unique ID by checking the database for existing IDs.
    With 128-bit entropy (32 hex chars), collisions are astronomically rare,
    but this provides defensive handling just in case.

    Args:
        db: Database session for checking existing IDs
        max_retries: Maximum number of generation attempts (default: 5)

    Returns:
        A unique relic ID guaranteed not to exist in the database

    Raises:
        HTTPException: If unable to generate unique ID after max_retries
    """
    for attempt in range(max_retries):
        relic_id = generate_relic_id()

        # Check if ID already exists
        existing = db.query(Relic).filter(Relic.id == relic_id).first()
        if not existing:
            return relic_id

    # This should virtually never happen with 128-bit IDs
    raise HTTPException(
        status_code=500,
        detail="Failed to generate unique relic ID after multiple attempts"
    )


def get_space_relic_count(space_id: str, db: Session) -> int:
    """Get the count of relics in a space efficiently using COUNT query."""
    count = db.query(func.count(Relic.id)).join(
        space_relics, Relic.id == space_relics.c.relic_id
    ).filter(space_relics.c.space_id == space_id).scalar()
    return count or 0


def get_space_role(space: Space, client_id: Optional[str]) -> Optional[str]:
    """Helper to determine a client's role in a space."""
    if not client_id:
        return None

    # Admins get 'admin' role if no other role
    is_admin = client_id in settings.get_admin_client_ids()

    if space.owner_client_id == client_id:
        return "owner"

    if is_admin:
        return "admin"

    for access in space.access_list:
        if access.client_id == client_id:
            return access.role

    return None

def check_space_access(space: Space, client_id: Optional[str], required_role: str = "viewer") -> bool:
    """Helper to check if client has required access to space."""
    # Admins have full access to all spaces
    if client_id and client_id in settings.get_admin_client_ids():
        return True

    role = get_space_role(space, client_id)
    if role == "owner":
        return True

    if not role:
        # Public spaces can be viewed by anyone
        return required_role == "viewer" and space.visibility == "public"

    if required_role == "viewer":
        return role in ("viewer", "editor", "admin")
    elif required_role == "editor":
        return role in ("editor", "admin")
    elif required_role == "admin":
        return role == "admin"

    return False
