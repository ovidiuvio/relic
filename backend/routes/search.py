"""Universal search: every relic the requester is entitled to see, in one list.

Entitled means any of:
  public      listed for everyone
  yours       you own it, whatever its visibility
  bookmarked  you bookmarked it (you had its link), unless it has since been restricted to others
  shared      it's restricted and you're on its access list
  spaces      it's in a space you own or belong to
Nothing else: someone else's private relic never appears, not even when its ID is searched for,
because its link is its only key. Admins get the same view; the admin relic list is separate.
Anonymous requests see public relics only. Expired relics are left out.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy import select, func, or_, and_, false
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from backend.database import get_db
from backend.models import Relic, Tag, Comment, UserBookmark, RelicAccess, Space, SpaceAccess, space_relics
from backend.schemas import RelicResponse
from backend.dependencies import get_current_user
from backend.utils import (
    clamp_limit, apply_relic_search, apply_owner_filter, relic_sort_order, parse_types,
    apply_type_filter, relic_facets, apply_range_filters, apply_visibility_filter, get_fork_counts, hidden_parents,
)

router = APIRouter(prefix="/api/v1")

SOURCES = ("public", "yours", "bookmarked", "shared", "spaces")


def _your_space_ids(user_id: str):
    owned = select(Space.id).where(Space.owner_id == user_id)
    member = select(SpaceAccess.space_id).where(SpaceAccess.user_id == user_id)
    return owned.union(member)


def _source_conditions(user_id: Optional[str]) -> dict:
    """One condition per source; together (OR) they are everything the user may see."""
    conditions = {"public": Relic.access_level == "public"}
    if not user_id:
        return conditions
    conditions["yours"] = Relic.user_id == user_id
    conditions["bookmarked"] = and_(
        Relic.access_level != "restricted",
        Relic.id.in_(select(UserBookmark.relic_id).where(UserBookmark.user_id == user_id)),
    )
    conditions["shared"] = and_(
        Relic.access_level == "restricted",
        Relic.id.in_(select(RelicAccess.relic_id).where(RelicAccess.user_id == user_id)),
    )
    conditions["spaces"] = Relic.id.in_(
        select(space_relics.c.relic_id).where(space_relics.c.space_id.in_(_your_space_ids(user_id)))
    )
    return conditions


async def _sources_for(db: AsyncSession, relics, user_id: Optional[str]) -> dict:
    """Why each of these relics is visible: {relic_id: {"sources": [...], "spaces": [{id, name}]}}."""
    ids = [r.id for r in relics]
    out = {r.id: {"sources": [], "spaces": []} for r in relics}
    for r in relics:
        if r.access_level == "public":
            out[r.id]["sources"].append("public")
        if user_id and r.user_id == user_id:
            out[r.id]["sources"].append("yours")
    if not user_id or not ids:
        return out
    bookmarked = set((await db.execute(
        select(UserBookmark.relic_id).where(UserBookmark.user_id == user_id, UserBookmark.relic_id.in_(ids))
    )).scalars().all())
    shared = set((await db.execute(
        select(RelicAccess.relic_id).where(RelicAccess.user_id == user_id, RelicAccess.relic_id.in_(ids))
    )).scalars().all())
    in_spaces = (await db.execute(
        select(space_relics.c.relic_id, Space.id, Space.name)
        .join(Space, Space.id == space_relics.c.space_id)
        .where(space_relics.c.relic_id.in_(ids), Space.id.in_(_your_space_ids(user_id)))
        .order_by(Space.name)
    )).all()
    for r in relics:
        if r.id in bookmarked and r.access_level != "restricted":
            out[r.id]["sources"].append("bookmarked")
        if r.id in shared and r.access_level == "restricted":
            out[r.id]["sources"].append("shared")
    for relic_id, space_id, name in in_spaces:
        entry = out[relic_id]
        if "spaces" not in entry["sources"]:
            entry["sources"].append("spaces")
        entry["spaces"].append({"id": space_id, "name": name})
    return out


@router.get("/search", response_model=dict)
async def search_everywhere(
    request: Request,
    limit: int = 25,
    offset: int = 0,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    owner: Optional[str] = None,  # an owner's public ID
    source: Optional[str] = None,  # one of SOURCES: only relics visible for that reason
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    min_size: Optional[int] = Query(None, ge=0),
    max_size: Optional[int] = Query(None, ge=0),
    access_level: Optional[str] = None,  # public, private or restricted
    types: Optional[str] = None,  # comma-separated content types (a type facet)
    facets: bool = False,  # include type, tag and source counts
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    """Search every relic you can see (see the module docstring for what that means)."""
    limit = clamp_limit(limit)
    offset = max(0, offset)
    user = await get_current_user(request, db)
    user_id = user.id if user else None
    conditions = _source_conditions(user_id)

    stmt = (
        select(Relic)
        .options(selectinload(Relic.tags), joinedload(Relic.owner))
        .where(or_(*conditions.values()))
        .where(or_(Relic.expires_at.is_(None), Relic.expires_at > datetime.utcnow()))
    )
    if tag:
        tag_obj = (await db.execute(select(Tag).where(Tag.name == tag.strip().lower()))).scalar_one_or_none()
        if not tag_obj:
            return {"relics": [], "total": 0, "limit": limit, "offset": offset, "facets": None}
        stmt = stmt.where(Relic.tags.contains(tag_obj))
    if search:
        stmt = apply_relic_search(stmt, search)
    stmt = apply_owner_filter(stmt, owner)
    stmt = apply_range_filters(stmt, created_after, created_before, min_size, max_size)
    stmt = apply_visibility_filter(stmt, access_level)

    # Counts describe the list before its type and source filters, so each facet shows what it
    # would give.
    facet_counts = None
    if facets:
        facet_counts = await relic_facets(db, stmt, parse_types(types))
        # All the source counts in one pass over the results (COUNT … FILTER).
        typed = apply_type_filter(stmt, parse_types(types)).with_only_columns(Relic.id).order_by(None).subquery()
        names = list(conditions)
        row = (await db.execute(
            select(*[func.count().filter(conditions[n]) for n in names]).where(Relic.id.in_(select(typed.c.id)))
        )).one()
        facet_counts["sources"] = {n: row[i] or 0 for i, n in enumerate(names)}

    if source in conditions:
        stmt = stmt.where(conditions[source])
    elif source:
        stmt = stmt.where(false())  # a source this requester has none of (anonymous asking for "yours")
    stmt = apply_type_filter(stmt, parse_types(types))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
    relics = (await db.execute(
        stmt.order_by(*relic_sort_order(sort_by, sort_order, search=search)).offset(offset).limit(limit)
    )).unique().scalars().all()

    relic_ids = [r.id for r in relics]
    comments_counts = {}
    if relic_ids:
        rows = await db.execute(
            select(Comment.relic_id, func.count(Comment.id)).where(Comment.relic_id.in_(relic_ids)).group_by(Comment.relic_id)
        )
        comments_counts = dict(rows.all())
    forks_counts = await get_fork_counts(db, relic_ids)
    parents_hidden = await hidden_parents(db, relics, user_id)
    why = await _sources_for(db, relics, user_id)

    out = []
    for relic in relics:
        item = RelicResponse.from_orm(relic).model_dump()
        item["comments_count"] = comments_counts.get(relic.id, 0)
        item["forks_count"] = forks_counts.get(relic.id, 0)
        item["can_edit"] = bool(user_id) and relic.user_id == user_id
        if relic.id in parents_hidden:
            item["fork_of"] = None
            item["fork_of_hidden"] = True
        item.update(why[relic.id])
        out.append(item)
    return {"relics": out, "total": total, "limit": limit, "offset": offset, "facets": facet_counts}


@router.get("/tags", response_model=dict)
async def search_tags(
    request: Request,
    search: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Tags matching a search, counted over the relics you can see (the same rule as search), so a
    tag only on someone's private relic stays unknown. Names starting with the search come first,
    then by how often they're used."""
    from backend.models import relic_tags
    from backend.utils import like_escape
    from sqlalchemy import case

    limit = max(1, min(limit, 50))
    user = await get_current_user(request, db)
    conditions = _source_conditions(user.id if user else None)
    visible = (
        select(Relic.id)
        .where(or_(*conditions.values()))
        .where(or_(Relic.expires_at.is_(None), Relic.expires_at > datetime.utcnow()))
    )
    term = (search or "").strip().lower()
    stmt = (
        select(Tag.name, func.count())
        .join(relic_tags, relic_tags.c.tag_id == Tag.id)
        .where(relic_tags.c.relic_id.in_(visible))
        .group_by(Tag.name)
    )
    if term:
        esc = like_escape(term)
        stmt = stmt.where(Tag.name.ilike(f"%{esc}%")).order_by(
            case((Tag.name.ilike(f"{esc}%"), 0), else_=1), func.count().desc(), Tag.name
        )
    else:
        stmt = stmt.order_by(func.count().desc(), Tag.name)
    rows = (await db.execute(stmt.limit(limit))).all()
    return {"tags": [{"name": name, "count": count} for name, count in rows]}
