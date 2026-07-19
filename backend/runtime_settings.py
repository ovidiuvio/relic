"""Resolution and caching of runtime settings.

Effective value = database override if one exists, else the registry default.

The resolved map is cached in-process behind a short TTL. Relic runs as a
single backend container, so this is exact today; the TTL is what keeps it
eventually consistent should a second replica ever be added.
"""
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models import SiteSetting
from backend.settings_registry import (
    DEFAULTS,
    PRESETS,
    SETTINGS_BY_KEY,
    SettingError,
    coerce_and_validate,
)

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 5

_cache: Optional[Dict[str, Any]] = None
_cache_expires_at: float = 0.0


def invalidate_cache() -> None:
    """Drop the cached settings so the next read goes to the database."""
    global _cache, _cache_expires_at
    _cache = None
    _cache_expires_at = 0.0


async def _load_overrides(db: AsyncSession) -> Dict[str, Any]:
    """Read stored overrides, discarding any key no longer in the registry."""
    result = await db.execute(select(SiteSetting))
    overrides = {}
    for row in result.scalars().all():
        if row.key in SETTINGS_BY_KEY:
            overrides[row.key] = row.value
    return overrides


async def get_settings() -> Dict[str, Any]:
    """Return the effective settings map, using the cache when it is fresh.

    Never raises: if the database is unreachable this falls back to registry
    defaults, because failing open on a config read is preferable to taking
    every request down with it.
    """
    global _cache, _cache_expires_at

    now = time.monotonic()
    if _cache is not None and now < _cache_expires_at:
        return _cache

    resolved = dict(DEFAULTS)
    try:
        async with AsyncSessionLocal() as db:
            resolved.update(await _load_overrides(db))
    except Exception as exc:
        logger.warning("Falling back to default settings, could not load overrides: %s", exc)

    _cache = resolved
    _cache_expires_at = now + CACHE_TTL_SECONDS
    return resolved


async def get_setting(key: str) -> Any:
    """Return a single effective setting value."""
    return (await get_settings())[key]


async def set_settings(db: AsyncSession, updates: Dict[str, Any], updated_by: Optional[str] = None) -> Dict[str, Any]:
    """Validate and persist setting overrides, then invalidate the cache.

    Every value is validated before anything is written, so a bad key in a
    bulk update leaves the stored configuration untouched.
    """
    validated = {key: coerce_and_validate(key, value) for key, value in updates.items()}

    for key, value in validated.items():
        stmt = insert(SiteSetting).values(
            key=key, value=value, updated_at=datetime.utcnow(), updated_by=updated_by
        )
        await db.execute(stmt.on_conflict_do_update(
            index_elements=[SiteSetting.key],
            set_={"value": value, "updated_at": datetime.utcnow(), "updated_by": updated_by},
        ))
    await db.commit()

    invalidate_cache()
    return validated


async def reset_settings(db: AsyncSession, section: Optional[str] = None) -> int:
    """Delete overrides so the affected settings fall back to registry defaults.

    Returns the number of overrides removed. With no section, resets everything.
    """
    keys = [
        key for key, definition in SETTINGS_BY_KEY.items()
        if section is None or definition.section == section
    ]
    result = await db.execute(select(SiteSetting).where(SiteSetting.key.in_(keys)))
    rows = result.scalars().all()
    for row in rows:
        await db.delete(row)
    await db.commit()

    invalidate_cache()
    return len(rows)


async def apply_preset(db: AsyncSession, name: str, updated_by: Optional[str] = None) -> Dict[str, Any]:
    """Apply a named preset, replacing all existing overrides.

    Overrides are cleared first so a preset describes a complete state rather
    than layering on top of whatever was set before.
    """
    if name not in PRESETS:
        raise SettingError(f"Unknown preset: {name}")

    await reset_settings(db)
    values = PRESETS[name]
    if not values:
        return {}
    return await set_settings(db, dict(values), updated_by=updated_by)
