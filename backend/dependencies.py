"""Shared dependencies and helper functions for route modules."""
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime
from typing import Optional, List

from backend.config import settings
from backend.models import Relic, ClientKey, Tag, Space, space_relics
from backend.utils import generate_relic_id


async def get_client_key(request: Request, db: AsyncSession) -> Optional[ClientKey]:
    """Extract and validate client key from request headers."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None

    result = await db.execute(select(ClientKey).where(ClientKey.id == x_client_key))
    return result.scalar_one_or_none()


async def get_or_create_client_key(request: Request, db: AsyncSession) -> Optional[ClientKey]:
    """Get existing client or create new one if key provided."""
    x_client_key = request.headers.get("X-Client-Key")
    if not x_client_key:
        return None

    # Upsert to avoid race condition when two concurrent requests arrive with the same new key
    await db.execute(
        pg_insert(ClientKey)
        .values(id=x_client_key, created_at=datetime.utcnow())
        .on_conflict_do_nothing()
    )
    await db.commit()

    result = await db.execute(select(ClientKey).where(ClientKey.id == x_client_key))
    return result.scalar_one()


def is_admin_client(client: Optional[ClientKey]) -> bool:
    """
    Check if a client has admin privileges.

    A client is admin if their ID is in the ADMIN_CLIENT_IDS config (immutable
    super-admin) OR their ClientKey.is_admin flag is set (runtime-grantable).
    The ClientKey is already loaded, so no extra query is needed.
    """
    if not client:
        return False
    return bool(client.is_admin) or client.id in settings.get_admin_client_ids()


async def is_admin_client_id(db: AsyncSession, client_id: Optional[str]) -> bool:
    """
    Check admin privileges given only a client ID string.

    Env super-admins are resolved without a query; otherwise the ClientKey.is_admin
    flag is looked up. Used by call sites that hold a client_id but not a ClientKey.
    """
    if not client_id:
        return False
    if client_id in settings.get_admin_client_ids():
        return True
    result = await db.execute(select(ClientKey.is_admin).where(ClientKey.id == client_id))
    return bool(result.scalar_one_or_none())


async def get_admin_client(request: Request, db: AsyncSession) -> ClientKey:
    """
    Get client and verify admin privileges.

    Raises HTTPException if not authenticated or not admin.
    """
    client = await get_client_key(request, db)
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


async def process_tags(db: AsyncSession, tag_names: List[str]) -> List[Tag]:
    """Process a list of tag names and return Tag objects (creating new ones if needed)."""
    if not tag_names:
        return []

    # Normalize tags
    normalized_names = sorted(list(set(name.strip().lower() for name in tag_names if name.strip())))

    if not normalized_names:
        return []

    # Insert missing tags, ignoring conflicts from concurrent requests
    await db.execute(
        pg_insert(Tag).values([{"name": name} for name in normalized_names]).on_conflict_do_nothing()
    )

    # Fetch all tag objects (existing + newly inserted)
    result = await db.execute(select(Tag).where(Tag.name.in_(normalized_names)))
    return result.scalars().all()


async def generate_unique_relic_id(db: AsyncSession, max_retries: int = 5) -> str:
    """
    Generate a unique relic ID with collision handling.
    """
    for attempt in range(max_retries):
        relic_id = generate_relic_id()

        result = await db.execute(select(Relic).where(Relic.id == relic_id))
        if not result.scalar_one_or_none():
            return relic_id

    # This should virtually never happen with 128-bit IDs
    raise HTTPException(
        status_code=500,
        detail="Failed to generate unique relic ID after multiple attempts"
    )


async def get_space_relic_count(space_id: str, db: AsyncSession) -> int:
    """Get the count of relics in a space efficiently using COUNT query."""
    result = await db.execute(
        select(func.count(Relic.id)).join(
            space_relics, Relic.id == space_relics.c.relic_id
        ).where(space_relics.c.space_id == space_id)
    )
    return result.scalar() or 0


async def get_space_role(space: Space, client_id: Optional[str], db: AsyncSession, *, is_admin: Optional[bool] = None) -> Optional[str]:
    """Helper to determine a client's role in a space.

    Args:
        is_admin: Pre-computed admin status. When provided, skips the
            ``is_admin_client_id`` DB query, eliminating redundant lookups
            in handlers that have already resolved admin status.
    """
    if not client_id:
        return None

    if space.owner_client_id == client_id:
        return "owner"

    # Admins (env super-admin or runtime-granted) get 'admin' role if no other role
    _is_admin = is_admin if is_admin is not None else await is_admin_client_id(db, client_id)
    if _is_admin:
        return "admin"

    for access in space.access_list:
        if access.client_id == client_id:
            return access.role

    return None

async def check_space_access(space: Space, client_id: Optional[str], db: AsyncSession, required_role: str = "viewer", *, is_admin: Optional[bool] = None) -> bool:
    """Helper to check if client has required access to space.

    Args:
        is_admin: Pre-computed admin status. When provided, skips the
            ``is_admin_client_id`` DB query, eliminating redundant lookups.
    """
    # Admins have full access to all spaces
    _is_admin = is_admin if is_admin is not None else await is_admin_client_id(db, client_id)
    if _is_admin:
        return True

    # Admin already handled above; pass is_admin=False to avoid a second lookup
    role = await get_space_role(space, client_id, db, is_admin=False)
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
