"""Enforcement helpers for runtime quotas and content policy.

Route handlers call into this module rather than reading settings directly, so
quota resolution and the "admins are exempt" rule live in exactly one place.
"""
import fnmatch
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import is_admin_user
from backend.models import Comment, Relic, User
from backend.settings_registry import QUOTA_OVERRIDE_COLUMNS

# Quota name -> the global setting it defaults to. Quota names are what the
# usage API and the admin UI speak; setting keys are an implementation detail.
QUOTA_DEFAULT_KEYS = {
    "max_relics": "max_relics_per_user",
    "max_relics_per_day": "max_relics_per_user_per_day",
    "max_storage_bytes": "max_storage_bytes_per_user",
    "max_comments_per_day": "max_comments_per_user_per_day",
}

# Reverse of QUOTA_OVERRIDE_COLUMNS: setting key -> User column.
_OVERRIDE_COLUMN_BY_SETTING = {v: k for k, v in QUOTA_OVERRIDE_COLUMNS.items()}

UNLIMITED = 0


def resolve_user_quotas(user: Optional[User], config: Dict[str, Any]) -> Dict[str, int]:
    """Return the effective quotas for a user.

    A per-user override of NULL means "inherit the global default"; 0 means
    unlimited. Anonymous users get the globals, since there is nothing to
    override against.
    """
    quotas = {}
    for quota_name, setting_key in QUOTA_DEFAULT_KEYS.items():
        value = config[setting_key]
        column = _OVERRIDE_COLUMN_BY_SETTING.get(setting_key)
        if user is not None and column is not None:
            override = getattr(user, column, None)
            if override is not None:
                value = override
        quotas[quota_name] = value
    return quotas


async def get_user_usage(db: AsyncSession, user_id: str) -> Dict[str, int]:
    """Return live usage for a user.

    Computed from the relic table rather than User.relic_count, which is a
    cached counter that drifts (admin.py recomputes it for the same reason).
    """
    day_ago = datetime.utcnow() - timedelta(days=1)
    result = await db.execute(
        select(
            func.count(Relic.id),
            func.coalesce(func.sum(Relic.size_bytes), 0),
            func.count(Relic.id).filter(Relic.created_at > day_ago),
        ).where(Relic.user_id == user_id)
    )
    relic_count, storage_bytes, relics_today = result.one()
    return {
        "relic_count": relic_count or 0,
        "storage_bytes": int(storage_bytes or 0),
        "relics_today": relics_today or 0,
    }


async def get_usage_for_users(db: AsyncSession, user_ids: list) -> Dict[str, Dict[str, int]]:
    """Return usage for many users in one grouped query.

    Used by the admin user listing, which would otherwise issue a query per row.
    """
    if not user_ids:
        return {}
    day_ago = datetime.utcnow() - timedelta(days=1)
    result = await db.execute(
        select(
            Relic.user_id,
            func.count(Relic.id),
            func.coalesce(func.sum(Relic.size_bytes), 0),
            func.count(Relic.id).filter(Relic.created_at > day_ago),
        )
        .where(Relic.user_id.in_(user_ids))
        .group_by(Relic.user_id)
    )
    usage = {
        row[0]: {
            "relic_count": row[1] or 0,
            "storage_bytes": int(row[2] or 0),
            "relics_today": row[3] or 0,
        }
        for row in result.all()
    }
    # Users with no relics produce no row; report zeroes rather than omitting them.
    for user_id in user_ids:
        usage.setdefault(user_id, {"relic_count": 0, "storage_bytes": 0, "relics_today": 0})
    return usage


def _matches_any(content_type: str, patterns: list) -> bool:
    """Return True if the content type matches any glob pattern."""
    value = (content_type or "").split(";")[0].strip().lower()
    return any(fnmatch.fnmatch(value, pattern.strip().lower()) for pattern in patterns)


def assert_content_type_allowed(content_type: str, config: Dict[str, Any]) -> None:
    """Reject content types outside the allow list or inside the block list."""
    allowed = config["allowed_content_types"]
    blocked = config["blocked_content_types"]

    if allowed and not _matches_any(content_type, allowed):
        raise HTTPException(
            status_code=415,
            detail=f"Content type '{content_type}' is not allowed on this instance",
        )
    if blocked and _matches_any(content_type, blocked):
        raise HTTPException(
            status_code=415,
            detail=f"Content type '{content_type}' is blocked on this instance",
        )


# Types that cannot execute script, so they stay viewable even when raw
# downloads are forced. Note image/* excludes SVG, which is handled below.
INLINE_SAFE_TYPES = ("text/plain", "text/markdown", "text/csv", "application/json", "application/pdf")
INLINE_SAFE_PREFIXES = ("image/", "video/", "audio/")

# Script-capable types, inline only when raw downloads are not forced.
SCRIPTABLE_TYPES = ("text/html", "application/xhtml+xml", "image/svg+xml")


def raw_disposition(content_type: str, config: Dict[str, Any]) -> str:
    """Return the Content-Disposition mode for raw content.

    With force_download_raw on, only types that provably cannot execute script
    stay inline, so the instance cannot be used to host a working page.
    """
    if not config["force_download_raw"]:
        return "inline"

    value = (content_type or "").split(";")[0].strip().lower()
    if value in SCRIPTABLE_TYPES:
        return "attachment"
    if value in INLINE_SAFE_TYPES or value.startswith(INLINE_SAFE_PREFIXES):
        return "inline"
    return "attachment"


def assert_length(value: Optional[str], limit: int, field: str) -> None:
    """Reject a text field longer than `limit`. A limit of 0 means unlimited."""
    if limit and value and len(value) > limit:
        raise HTTPException(
            status_code=400,
            detail=f"{field} exceeds the maximum length of {limit} characters",
        )


def assert_tags_allowed(tags: Optional[list], config: Dict[str, Any]) -> None:
    """Reject too many tags, or any tag that is too long."""
    if not tags:
        return
    max_count = config["max_tag_count"]
    if max_count and len(tags) > max_count:
        raise HTTPException(status_code=400, detail=f"At most {max_count} tags are allowed")
    max_length = config["max_tag_length"]
    if max_length:
        for tag in tags:
            if len(tag) > max_length:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tag '{tag[:32]}...' exceeds the maximum length of {max_length} characters",
                )


async def assert_can_create_relic(
    db: AsyncSession,
    user: Optional[User],
    config: Dict[str, Any],
    content_type: Optional[str] = None,
) -> int:
    """Check everything knowable before content is streamed, and return the
    effective byte ceiling for this upload.

    The returned ceiling is the smaller of the global upload limit and the
    user's remaining storage quota, so a single oversized stream is aborted
    mid-flight rather than being stored and then rejected.
    """
    if content_type:
        assert_content_type_allowed(content_type, config)

    max_upload = config["max_upload_size_bytes"] or 0

    # Admins are exempt from quotas, mirroring check_ownership_or_admin.
    if user is None or is_admin_user(user):
        return max_upload

    quotas = resolve_user_quotas(user, config)
    needs_usage = quotas["max_relics"] or quotas["max_relics_per_day"] or quotas["max_storage_bytes"]
    if not needs_usage:
        return max_upload

    usage = await get_user_usage(db, user.id)

    if quotas["max_relics"] and usage["relic_count"] >= quotas["max_relics"]:
        raise HTTPException(
            status_code=429,
            detail=f"Relic quota reached ({quotas['max_relics']}). Delete a relic to create another.",
        )
    if quotas["max_relics_per_day"] and usage["relics_today"] >= quotas["max_relics_per_day"]:
        raise HTTPException(
            status_code=429,
            detail=f"Daily relic limit reached ({quotas['max_relics_per_day']}). Try again later.",
        )

    if quotas["max_storage_bytes"]:
        remaining = quotas["max_storage_bytes"] - usage["storage_bytes"]
        if remaining <= 0:
            raise HTTPException(
                status_code=413,
                detail="Storage quota exhausted. Delete a relic to free space.",
            )
        if not max_upload or remaining < max_upload:
            return remaining

    return max_upload


async def assert_can_comment(db: AsyncSession, user: User, config: Dict[str, Any]) -> None:
    """Reject a comment that would exceed the user's daily comment quota."""
    if is_admin_user(user):
        return
    limit = resolve_user_quotas(user, config)["max_comments_per_day"]
    if not limit:
        return
    day_ago = datetime.utcnow() - timedelta(days=1)
    result = await db.execute(
        select(func.count(Comment.id)).where(
            Comment.user_id == user.id, Comment.created_at > day_ago
        )
    )
    if (result.scalar() or 0) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily comment limit reached ({limit}). Try again later.",
        )


def resolve_expiry(expires_in: Optional[str], config: Dict[str, Any]) -> Optional[datetime]:
    """Turn a client-supplied expiry into a datetime, applying retention policy.

    Note that parse_expiry_string treats unparseable input as "never", so with
    force_expiry on we reject bad strings outright rather than silently
    granting permanent storage.
    """
    from backend.utils import parse_duration_seconds, parse_expiry_string

    max_seconds = parse_duration_seconds(config["max_expiry"])

    if expires_in is None:
        expires_in = config["default_expiry"]

    if config["force_expiry"]:
        if max_seconds is None:
            raise HTTPException(
                status_code=500,
                detail="Expiry is required but no maximum expiry is configured",
            )
        if expires_in and expires_in != "never" and parse_duration_seconds(expires_in) is None:
            raise HTTPException(
                status_code=400,
                detail=f"Could not understand expiry '{expires_in}'. Use forms like 30m, 24h, or 7d.",
            )

    return parse_expiry_string(expires_in, max_seconds=max_seconds)


def assert_feature_enabled(config: Dict[str, Any], key: str, feature: str) -> None:
    """Reject a request for a feature an admin has switched off."""
    if not config[key]:
        raise HTTPException(status_code=403, detail=f"{feature} is disabled on this instance")


def usage_report(usage: Dict[str, int], quotas: Dict[str, int]) -> Dict[str, dict]:
    """Shape usage and quotas into {used, limit, unlimited} triples for the API,
    so no client has to reimplement the 0-means-unlimited rule."""
    def entry(used: int, limit: int) -> dict:
        return {"used": used, "limit": limit or None, "unlimited": not limit}

    return {
        "relics": entry(usage["relic_count"], quotas["max_relics"]),
        "relics_today": entry(usage["relics_today"], quotas["max_relics_per_day"]),
        "storage_bytes": entry(usage["storage_bytes"], quotas["max_storage_bytes"]),
    }
