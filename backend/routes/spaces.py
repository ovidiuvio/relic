"""Space endpoints."""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, selectinload
from datetime import datetime
from typing import Optional, List

from backend.config import settings
from backend.database import get_db
from backend.models import Relic, ClientKey, Space, SpaceAccess, space_relics
from backend.schemas import (
    RelicListResponse, SpaceCreate, SpaceUpdate, SpaceResponse,
    SpaceAccessBase, SpaceAccessResponse
)
from backend.utils import generate_relic_id
from backend.dependencies import get_space_role, check_space_access, get_space_relic_count

router = APIRouter(prefix="/api/v1/spaces")


@router.post("", response_model=SpaceResponse)
async def create_space(
    space_in: SpaceCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new space."""
    client_id = request.headers.get("X-Client-Key")
    if not client_id:
        raise HTTPException(status_code=401, detail="Client key required")

    space = Space(
        id=generate_relic_id(),
        name=space_in.name,
        visibility=space_in.visibility,
        owner_client_id=client_id
    )

    db.add(space)
    db.commit()
    db.refresh(space)

    return {
        "id": space.id,
        "name": space.name,
        "visibility": space.visibility,
        "owner_client_id": space.owner_client_id,
        "created_at": space.created_at,
        "relic_count": 0,
        "role": "owner"
    }

@router.get("", response_model=List[SpaceResponse])
async def list_spaces(
    request: Request,
    visibility: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List spaces.
    If authenticated: returns public spaces + private spaces user has access to.
    If anonymous: returns only public spaces.
    Optionally filter by visibility.
    """
    client_id = request.headers.get("X-Client-Key")
    is_admin = client_id and client_id in settings.get_admin_client_ids()

    query = db.query(Space).options(selectinload(Space.access_list))

    if visibility:
        query = query.filter(Space.visibility == visibility)

    spaces = query.all()

    # Fetch all relic counts in a single query instead of one per space
    relic_counts = dict(
        db.query(space_relics.c.space_id, func.count(space_relics.c.relic_id))
        .group_by(space_relics.c.space_id)
        .all()
    )

    result = []
    for space in spaces:
        role = get_space_role(space, client_id)

        # Determine if space should be included
        is_visible = False
        if is_admin or space.visibility == "public" or role is not None:
            is_visible = True

        if is_visible:
            result.append({
                "id": space.id,
                "name": space.name,
                "visibility": space.visibility,
                "owner_client_id": space.owner_client_id,
                "created_at": space.created_at,
                "relic_count": relic_counts.get(space.id, 0),
                "role": role
            })

    # Sort by creation date, newest first
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result

@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(
    space_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get space details."""
    client_id = request.headers.get("X-Client-Key")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not check_space_access(space, client_id, "viewer"):
        raise HTTPException(status_code=403, detail="Not authorized to view this space")

    return {
        "id": space.id,
        "name": space.name,
        "visibility": space.visibility,
        "owner_client_id": space.owner_client_id,
        "created_at": space.created_at,
        "relic_count": get_space_relic_count(space.id, db),
        "role": get_space_role(space, client_id)
    }

@router.put("/{space_id}", response_model=SpaceResponse)
async def update_space(
    space_id: str,
    space_in: SpaceUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update space metadata."""
    client_id = request.headers.get("X-Client-Key")
    if not client_id:
        raise HTTPException(status_code=401, detail="Client key required")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner or admin can update space metadata
    is_admin = client_id in settings.get_admin_client_ids()
    if space.owner_client_id != client_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this space")

    if space_in.name is not None:
        space.name = space_in.name
    if space_in.visibility is not None:
        space.visibility = space_in.visibility

    db.commit()
    db.refresh(space)

    return {
        "id": space.id,
        "name": space.name,
        "visibility": space.visibility,
        "owner_client_id": space.owner_client_id,
        "created_at": space.created_at,
        "relic_count": get_space_relic_count(space.id, db),
        "role": get_space_role(space, client_id)
    }

@router.delete("/{space_id}")
async def delete_space(
    space_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a space."""
    client_id = request.headers.get("X-Client-Key")
    if not client_id:
        raise HTTPException(status_code=401, detail="Client key required")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner or admin can delete space
    is_admin = client_id in settings.get_admin_client_ids()
    if space.owner_client_id != client_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this space")

    db.delete(space)
    db.commit()
    return {"message": "Space deleted successfully"}

@router.get("/{space_id}/relics", response_model=RelicListResponse)
async def get_space_relics(
    space_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get relics in a space."""
    client_id = request.headers.get("X-Client-Key")
    is_admin = client_id in settings.get_admin_client_ids() if client_id else False

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not check_space_access(space, client_id, "viewer"):
        raise HTTPException(status_code=403, detail="Not authorized to view this space")

    # Query relics in space with filters applied at database level
    # Filter: not expired, and either public or private but visible to space member
    # ⚡ Bolt: Use selectinload(Relic.tags) to prevent N+1 queries when accessing relic.tags later
    query = db.query(Relic).options(selectinload(Relic.tags)).join(
        space_relics, Relic.id == space_relics.c.relic_id
    ).filter(
        space_relics.c.space_id == space_id
    ).filter(
        # Exclude expired relics
        or_(Relic.expires_at.is_(None), Relic.expires_at > datetime.utcnow())
    ).filter(
        # Show public relics to everyone, or private relics to space members/admin
        or_(
            Relic.access_level == "public",
            and_(Relic.access_level == "private", Relic.client_id == client_id),
            and_(Relic.access_level == "private", is_admin),
            # Private relics are visible to anyone with space access (space membership grants visibility)
            and_(Relic.access_level == "private", client_id is not None)
        )
    ).order_by(Relic.created_at.desc())

    relics = query.all()

    # Format response
    result = []
    for relic in relics:
        can_edit = client_id is not None and (relic.client_id == client_id or is_admin)
        relic_dict = {
            "id": relic.id,
            "name": relic.name,
            "description": relic.description,
            "content_type": relic.content_type,
            "language_hint": relic.language_hint,
            "size_bytes": relic.size_bytes,
            "fork_of": relic.fork_of,
            "access_level": relic.access_level,
            "created_at": relic.created_at,
            "expires_at": relic.expires_at,
            "access_count": relic.access_count,
            "bookmark_count": relic.bookmark_count,
            "can_edit": can_edit,
            "tags": [{"name": t.name, "id": t.id} for t in relic.tags]
        }
        result.append(relic_dict)

    return {"relics": result}

@router.post("/{space_id}/relics")
async def add_relic_to_space(
    space_id: str,
    relic_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Add a relic to a space."""
    client_id = request.headers.get("X-Client-Key")
    if not client_id:
        raise HTTPException(status_code=401, detail="Client key required")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Must have edit access to space
    if not check_space_access(space, client_id, "editor"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this space")

    # Must have access to relic (either public or owner)
    is_admin = client_id in settings.get_admin_client_ids()
    if relic.access_level == "private" and relic.client_id != client_id and not is_admin:
         raise HTTPException(status_code=403, detail="Not authorized to access this relic")

    if relic not in space.relics:
        space.relics.append(relic)
        db.commit()

    return {"message": "Relic added to space successfully"}

@router.delete("/{space_id}/relics/{relic_id}")
async def remove_relic_from_space(
    space_id: str,
    relic_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Remove a relic from a space."""
    client_id = request.headers.get("X-Client-Key")
    if not client_id:
        raise HTTPException(status_code=401, detail="Client key required")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Must have edit access to space
    if not check_space_access(space, client_id, "editor"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this space")

    if relic in space.relics:
        space.relics.remove(relic)
        db.commit()

    return {"message": "Relic removed from space successfully"}

@router.get("/{space_id}/access", response_model=List[SpaceAccessResponse])
async def get_space_access(
    space_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get the access list for a space."""
    client_id = request.headers.get("X-Client-Key")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner, editors, or admin can view access list
    if not check_space_access(space, client_id, "editor"):
        raise HTTPException(status_code=403, detail="Not authorized to view space access list")

    result = []
    for access in space.access_list:
        result.append({
            "id": access.id,
            "space_id": access.space_id,
            "client_id": access.client_id,
            "role": access.role,
            "created_at": access.created_at,
            "client_name": access.client.name
        })

    return result

@router.post("/{space_id}/access", response_model=SpaceAccessResponse)
async def add_space_access(
    space_id: str,
    access_in: SpaceAccessBase,
    request: Request,
    db: Session = Depends(get_db)
):
    """Add or update a user's access to a space."""
    client_id = request.headers.get("X-Client-Key")
    if not client_id:
        raise HTTPException(status_code=401, detail="Client key required")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner or admin can modify access list
    if not check_space_access(space, client_id, "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to modify space access list")

    # Prevent modifying owner's own access
    if access_in.client_id == space.owner_client_id:
         raise HTTPException(status_code=400, detail="Cannot modify owner access")

    # Check if client to be added exists
    target_client = db.query(ClientKey).filter(ClientKey.id == access_in.client_id).first()
    if not target_client:
        raise HTTPException(status_code=404, detail="Client to add not found")

    # Check if access already exists
    access = db.query(SpaceAccess).filter(
        SpaceAccess.space_id == space_id,
        SpaceAccess.client_id == access_in.client_id
    ).first()

    if access:
        # Update existing
        access.role = access_in.role
    else:
        # Create new
        access = SpaceAccess(
            space_id=space_id,
            client_id=access_in.client_id,
            role=access_in.role
        )
        db.add(access)

    db.commit()
    db.refresh(access)

    return {
        "id": access.id,
        "space_id": access.space_id,
        "client_id": access.client_id,
        "role": access.role,
        "created_at": access.created_at,
        "client_name": target_client.name
    }

@router.delete("/{space_id}/access/{target_client_id}")
async def remove_space_access(
    space_id: str,
    target_client_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Remove a user's access from a space."""
    client_id = request.headers.get("X-Client-Key")
    if not client_id:
        raise HTTPException(status_code=401, detail="Client key required")

    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Only owner, admin, or the user themselves can remove access
    if target_client_id != client_id and not check_space_access(space, client_id, "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to remove space access")

    access = db.query(SpaceAccess).filter(
        SpaceAccess.space_id == space_id,
        SpaceAccess.client_id == target_client_id
    ).first()

    if not access:
        raise HTTPException(status_code=404, detail="Access record not found")

    db.delete(access)
    db.commit()

    return {"message": "Access removed successfully"}
