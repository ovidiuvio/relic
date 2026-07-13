"""Check GitHub releases for newer versions of the application."""
import logging
import re
import time
from typing import Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

# Module-level cache: one entry per process, refreshed after UPDATE_CHECK_TTL
_cache: dict = {"data": None, "fetched_at": 0.0}


def _parse_version(tag: str) -> Optional[tuple]:
    match = _VERSION_RE.match(tag.strip())
    if not match:
        return None
    return tuple(int(g) for g in match.groups())


def _is_newer(candidate: str, current: str) -> bool:
    cand = _parse_version(candidate)
    curr = _parse_version(current)
    if cand is None:
        return False
    if curr is None:
        # Unreleased build ("dev"): any release counts as an update
        return True
    return cand > curr


async def get_update_info(force: bool = False) -> dict:
    """Return current/latest version info and recent releases, cached with a TTL."""
    now = time.time()
    if not force and _cache["data"] and now - _cache["fetched_at"] < settings.UPDATE_CHECK_TTL:
        return _cache["data"]

    url = f"https://api.github.com/repos/{settings.UPDATE_REPO}/releases"
    releases = []
    error = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                params={"per_page": 15},
                headers={"Accept": "application/vnd.github+json"},
            )
            response.raise_for_status()
            for release in response.json():
                tag = release.get("tag_name", "")
                if not _parse_version(tag):
                    continue
                body = release.get("body") or ""
                releases.append({
                    "tag": tag,
                    "name": release.get("name") or tag,
                    "published_at": release.get("published_at"),
                    "prerelease": release.get("prerelease", False),
                    "body_excerpt": body[:1000],
                    "url": release.get("html_url"),
                })
    except httpx.HTTPError as e:
        logger.error(f"Update check failed: {e}")
        error = str(e)

    current = settings.APP_VERSION
    stable = [r for r in releases if not r["prerelease"]]
    latest = stable[0]["tag"] if stable else None

    data = {
        "current_version": current,
        "latest_version": latest,
        "update_available": bool(latest and _is_newer(latest, current)),
        "checked_at": now,
        "releases": [
            {**r, "is_current": _parse_version(r["tag"]) == _parse_version(current)}
            for r in releases
        ],
        "error": error,
    }

    # Don't cache failures so a retry can succeed immediately
    if error is None:
        _cache["data"] = data
        _cache["fetched_at"] = now
    return data
