"""Utility functions."""
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession


def generate_relic_id() -> str:
    """
    Generate GitHub Gist-style 32-character hexadecimal ID.

    Provides 128 bits of entropy using cryptographically secure
    random number generation. Practically collision-proof and
    resistant to enumeration attacks.

    Format: 32 lowercase hexadecimal characters (0-9, a-f)
    Example: f47ac10b58cc4372a5670e02b2c3d479

    Returns:
        Cryptographically secure 32-character hex string

    Security properties:
        - 128 bits of entropy (16 bytes)
        - Uses os.urandom() via secrets.token_hex()
        - 50% collision probability: ~1.8×10^19 relics
        - Brute force at 1M attempts/sec: ~1.1×10^25 years
        - Same approach as GitHub Gists
    """
    return secrets.token_hex(16)  # 16 bytes = 32 hex characters


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def parse_expiry_string(expires_in: Optional[str]) -> Optional[datetime]:
    """
    Parse expiry string and return expiration datetime.

    Args:
        expires_in: "10m", "1h", "24h", "7d", "30d", "1y", or None

    Returns:
        Datetime object or None
    """
    if not expires_in or expires_in == "never":
        return None

    now = datetime.utcnow()
    multipliers = {
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
        "M": 2592000,  # 30 days
        "y": 31536000  # 365 days
    }

    try:
        value = int(expires_in[:-1])
        unit = expires_in[-1]

        if unit not in multipliers:
            return None

        seconds = value * multipliers[unit]
        return now + timedelta(seconds=seconds)
    except (ValueError, KeyError):
        return None


def is_expired(expires_at: Optional[datetime]) -> bool:
    """Check if a relic has expired."""
    if not expires_at:
        return False
    return datetime.utcnow() > expires_at


MAX_PAGE_LIMIT = 1000


def like_escape(value: str) -> str:
    """Escape LIKE wildcard characters so they match literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def like_term(value: str) -> str:
    """Wrap a search value in % for ILIKE, with wildcards escaped."""
    return f"%{like_escape(value)}%"


def apply_owner_filter(stmt, owner: Optional[str]):
    """Filter a Relic Select statement to one owner, named by public ID."""
    from backend.models import Relic, User
    from sqlalchemy import select
    if not owner:
        return stmt
    owner_id = select(User.id).where(User.public_id == owner.strip()).scalar_subquery()
    return stmt.where(Relic.user_id == owner_id)


MAX_SEARCH_TERMS = 10


def search_terms(search: str) -> List[str]:
    """A search's terms: its words, with "quoted phrases" kept whole (an unclosed quote runs
    to the end). Blank terms and repeats are dropped; at most MAX_SEARCH_TERMS are kept."""
    import re
    terms = []
    for quoted, word in re.findall(r'"([^"]*)"?|(\S+)', search or ""):
        term = (quoted if quoted else word).strip()
        if term and term.lower() not in (t.lower() for t in terms):
            terms.append(term)
    return terms[:MAX_SEARCH_TERMS]


def _utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """A datetime as the naive UTC the database stores."""
    from datetime import timezone
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def apply_range_filters(stmt, created_after: Optional[datetime] = None, created_before: Optional[datetime] = None,
                        min_size: Optional[int] = None, max_size: Optional[int] = None):
    """Filter a Relic Select statement by when relics were created (created_after inclusive,
    created_before exclusive; aware datetimes are converted to UTC, naive ones taken as UTC)
    and by size in bytes (both bounds inclusive)."""
    from backend.models import Relic
    if created_after is not None:
        stmt = stmt.where(Relic.created_at >= _utc_naive(created_after))
    if created_before is not None:
        stmt = stmt.where(Relic.created_at < _utc_naive(created_before))
    if min_size is not None:
        stmt = stmt.where(Relic.size_bytes >= min_size)
    if max_size is not None:
        stmt = stmt.where(Relic.size_bytes <= max_size)
    return stmt


def apply_relic_search(stmt, search: str):
    """Filter a Relic Select statement by a search: every term (see search_terms) must match
    the name, ID, description or a tag name, case-insensitively and in any order. A one-word
    search matches exactly as it always has."""
    from backend.models import Relic, Tag
    from sqlalchemy import select, or_
    terms = search_terms(search)
    if not terms:
        return stmt
    for t in terms:
        term = like_term(t)
        tag_sq = select(Relic.id).join(Relic.tags).where(Tag.name.ilike(term)).scalar_subquery()
        stmt = stmt.where(
            or_(Relic.name.ilike(term), Relic.id.ilike(term), Relic.description.ilike(term), Relic.id.in_(tag_sq))
        )
    return stmt.distinct()


def relevance_order(search: str) -> tuple:
    """ORDER BY for the best matches of a search first: a name equal to the search, then names
    starting with it, then names containing it, then names containing every term, then the
    rest (matches in the ID, description or tags); newest first within each."""
    from backend.models import Relic
    from sqlalchemy import case, and_
    terms = search_terms(search)
    phrase = " ".join(terms)
    if not phrase:
        return (Relic.created_at.desc(), Relic.id.desc())
    esc = like_escape(phrase)
    rank = case(
        (Relic.name.ilike(esc), 0),
        (Relic.name.ilike(f"{esc}%"), 1),
        (Relic.name.ilike(f"%{esc}%"), 2),
        (and_(*[Relic.name.ilike(like_term(t)) for t in terms]), 3),
        else_=4,
    )
    return (rank, Relic.created_at.desc(), Relic.id.desc())


MAX_TYPE_FILTER = 400  # content types in one ?types= filter (a facet sends its whole family)


def parse_types(types: Optional[str]) -> List[str]:
    """Split a ?types= value ("text/x-python,application/json") into lowercase content types.

    Parameters after ';' are dropped, blanks and oversized entries are ignored, and the list is
    capped, so a crafted value can't blow up the query.
    """
    if not types:
        return []
    out = []
    for part in types.split(","):
        t = part.split(";", 1)[0].strip().lower()
        if t and len(t) <= 100 and t not in out:
            out.append(t)
        if len(out) >= MAX_TYPE_FILTER:
            break
    return out


def apply_type_filter(stmt, types: List[str]):
    """Keep relics whose content type is one of `types`, ignoring parameters such as charset."""
    from backend.models import Relic
    from sqlalchemy import func, or_
    if not types:
        return stmt
    ct = func.lower(Relic.content_type)
    return stmt.where(or_(ct.in_(types), *[ct.like(f"{like_escape(t)};%", escape="\\") for t in types]))


async def relic_facets(db: AsyncSession, stmt, types: Optional[List[str]] = None, tag_limit: int = 20) -> Dict:
    """Counts for a filtered relic list: relics per content type, and its most used tags.

    `stmt` is the list's Select with its scope and filters but not its type filter (any entity
    columns; Relic is joined); `types` is that type filter (see parse_types). Type counts ignore
    it, so each type facet shows what it would give; tag counts apply it, so they describe the
    list as shown. Content types are reported lowercase without parameters; the client groups
    them into its type families, so the server needs no copy of the type catalogue.
    """
    from backend.models import Relic, Tag, relic_tags
    from sqlalchemy import select, func

    ids = stmt.with_only_columns(Relic.id).order_by(None).subquery()
    type_rows = await db.execute(
        select(func.lower(Relic.content_type), func.count())
        .where(Relic.id.in_(select(ids.c.id)))
        .group_by(func.lower(Relic.content_type))
    )
    type_counts: Dict[str, int] = {}
    for content_type, count in type_rows.all():
        base = (content_type or "application/octet-stream").split(";", 1)[0].strip()
        type_counts[base] = type_counts.get(base, 0) + count

    tagged = apply_type_filter(stmt, types or []).with_only_columns(Relic.id).order_by(None).subquery()
    tag_rows = await db.execute(
        select(Tag.name, func.count())
        .join(relic_tags, relic_tags.c.tag_id == Tag.id)
        .where(relic_tags.c.relic_id.in_(select(tagged.c.id)))
        .group_by(Tag.name)
        .order_by(func.count().desc(), Tag.name)
        .limit(tag_limit)
    )
    return {"types": type_counts, "tags": [{"name": name, "count": count} for name, count in tag_rows.all()]}


def relic_sort_order(sort_by: str, sort_order: str, overrides: dict = None, search: Optional[str] = None) -> tuple:
    """Return SQLAlchemy ORDER BY clauses for the common relic sort options.

    Pass the result unpacked: ``stmt.order_by(*relic_sort_order(...))``.

    sort_by: created_at, name, owner, size, access_count, bookmark_count, comments_count,
    forks_count, and relevance (best matches of `search` first; newest first without one).
    Unknown keys fall back to created_at.
    overrides: dict mapping sort key names to alternative columns,
    e.g. {"created_at": ClientBookmark.created_at} for bookmarks.

    Names and owners sort case-insensitively. Rows without a value (unnamed relics,
    anonymous relics when sorting by owner) come last
    in either direction, and ties are broken by newest first, then id, so offset
    pagination never repeats or skips a row between pages.
    """
    from backend.models import Relic, Comment, User
    from sqlalchemy import select, func, nulls_last
    from sqlalchemy.orm import aliased

    if sort_by == "relevance":
        return relevance_order(search or "")

    fork = aliased(Relic)
    sort_map = {
        "created_at": Relic.created_at,
        "name": func.lower(Relic.name),
        # Owner's display name; anonymous relics and unnamed owners have none.
        "owner": select(func.lower(User.name))
            .where(User.id == Relic.user_id).correlate(Relic).scalar_subquery(),
        "size": Relic.size_bytes,
        "access_count": Relic.access_count,
        "bookmark_count": Relic.bookmark_count,
        # Counted per row; comment.relic_id and relic.fork_of are indexed.
        "comments_count": select(func.count(Comment.id))
            .where(Comment.relic_id == Relic.id).correlate(Relic).scalar_subquery(),
        "forks_count": select(func.count(fork.id))
            .where(fork.fork_of == Relic.id).correlate(Relic).scalar_subquery(),
    }
    if overrides:
        sort_map.update(overrides)
    sort_col = sort_map.get(sort_by, sort_map["created_at"])
    primary = nulls_last(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    return (primary, Relic.created_at.desc(), Relic.id.desc())


def clamp_limit(limit: int, default: int = 25) -> int:
    """Clamp a pagination limit to [1, MAX_PAGE_LIMIT]."""
    if limit < 1:
        return default
    return min(limit, MAX_PAGE_LIMIT)


async def get_fork_counts(db: AsyncSession, relic_ids: List[str]) -> Dict[str, int]:
    """Count direct forks for each relic. Returns {relic_id: count}."""
    if not relic_ids:
        return {}
    from backend.models import Relic
    from sqlalchemy import select, func
    result = await db.execute(
        select(Relic.fork_of, func.count(Relic.id))
        .where(Relic.fork_of.in_(relic_ids))
        .group_by(Relic.fork_of)
    )
    return {row[0]: row[1] for row in result.all()}


async def get_fork_count(db: AsyncSession, relic_id: str) -> int:
    """Count direct forks of a single relic."""
    from backend.models import Relic
    from sqlalchemy import select, func
    result = await db.execute(
        select(func.count(Relic.id)).where(Relic.fork_of == relic_id)
    )
    return result.scalar() or 0


async def hidden_relic_ids(db: AsyncSession, relic_ids, user_id: Optional[str], is_admin: bool = False) -> set:
    """Which of these relic IDs this user may not be shown.

    A private relic's ID is its access token, and a restricted relic is only for its owner and
    the people on its access list, so their IDs must not turn up anywhere else (a fork's
    fork_of, a lineage tree) unless the user owns the relic, is on its list, or is an admin.
    IDs of relics that no longer exist are not hidden.
    """
    from backend.models import Relic, RelicAccess
    from sqlalchemy import select

    relic_ids = {i for i in relic_ids if i}
    if not relic_ids or is_admin:
        return set()
    rows = (await db.execute(
        select(Relic.id, Relic.user_id).where(Relic.id.in_(relic_ids), Relic.access_level != "public")
    )).all()
    hidden = {r.id for r in rows if not (user_id and r.user_id == user_id)}
    if hidden and user_id:
        allowed = await db.execute(
            select(RelicAccess.relic_id).where(RelicAccess.relic_id.in_(hidden), RelicAccess.user_id == user_id)
        )
        hidden -= set(allowed.scalars().all())
    return hidden


async def hidden_parents(db: AsyncSession, relics, user_id: Optional[str], is_admin: bool = False) -> set:
    """IDs of these relics whose fork_of the user may not be shown (see hidden_relic_ids).

    A fork's owner always sees its parent: they had its ID to fork it.
    """
    others = [r for r in relics if r.fork_of and not (user_id and r.user_id == user_id)]
    hidden = await hidden_relic_ids(db, {r.fork_of for r in others}, user_id, is_admin)
    return {r.id for r in others if r.fork_of in hidden}


