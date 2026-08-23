"""Request-level policy enforcement.

Handles the concerns that apply uniformly across routes — availability modes,
the write-auth requirement, and rate limiting. Anything needing per-route
context (quotas, content types, expiry) is enforced in the routes via limits.py.
"""
import logging
import re
import time
from datetime import datetime
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from backend.database import AsyncSessionLocal
from backend.dependencies import is_admin_user_id
from backend.models import RateLimitCounter
from backend.runtime_settings import get_settings

logger = logging.getLogger(__name__)

# Paths that policy never blocks.
#
# Admin routes are exempt so an admin can always undo a restriction they just
# applied — without this, switching on maintenance or read-only mode would lock
# the dashboard and leave a restart as the only recovery.
# /api/v1/settings and /api/v1/version are always reachable so the client
# can read maintenance_mode on startup and display the maintenance page.
BYPASS_PREFIXES = ("/api/v1/admin", "/health", "/api/v1/settings", "/api/v1/version")

# Requests that create stored content, limited separately from ordinary writes.
UPLOAD_PATH_PATTERN = re.compile(r"^/api/v1/relics(/raw|/[a-f0-9]{32}/fork)?/?$")

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

_last_sweep = 0.0
SWEEP_INTERVAL_SECONDS = 300


async def _sweep_expired(db, now: datetime) -> None:
    """Delete counter rows whose window has passed, so the table stays small."""
    global _last_sweep
    monotonic = time.monotonic()
    if monotonic - _last_sweep < SWEEP_INTERVAL_SECONDS:
        return
    _last_sweep = monotonic
    await db.execute(delete(RateLimitCounter).where(RateLimitCounter.expires_at < now))


async def _check_windows(checks: list, client_key: str, now: datetime) -> Optional[int]:
    """Increment fixed-window counters and return seconds to wait if any is over.

    Counters live in Postgres rather than memory because the app runs several
    gunicorn workers; per-process counters would each grant the full limit.
    The window boundary is part of the row key, so a new window starts clean.

    Fails open: if the counter store is unreachable, requests are allowed
    rather than the whole instance going down with it.
    """
    epoch = now.timestamp()
    try:
        async with AsyncSessionLocal() as db:
            await _sweep_expired(db, now)

            for bucket, limit, window in checks:
                if not limit:
                    continue
                window_start = int(epoch // window) * window
                key = f"{bucket}:{client_key}:{window_start}"
                expires_at = datetime.utcfromtimestamp(window_start + window)

                stmt = insert(RateLimitCounter).values(key=key, count=1, expires_at=expires_at)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[RateLimitCounter.key],
                    set_={"count": RateLimitCounter.count + 1},
                ).returning(RateLimitCounter.count)

                count = (await db.execute(stmt)).scalar()
                if count > limit:
                    await db.commit()
                    return max(1, int(window_start + window - epoch) + 1)

            await db.commit()
    except Exception as exc:
        logger.warning("Rate limit check failed, allowing request: %s", exc)
    return None


def _client_key(request: Request) -> str:
    """Identify the caller for rate-limiting purposes.

    Prefers the user key; falls back to client IP for anonymous traffic.

    The IP must come from a header the client cannot forge. nginx sets
    X-Real-IP from $remote_addr, overwriting anything the client sent, so it is
    trustworthy. X-Forwarded-For is NOT: nginx uses $proxy_add_x_forwarded_for,
    which appends to a client-supplied value, so its first entry is attacker
    controlled — reading that would let anyone reset their own limit by
    spoofing a new address. We therefore take the last entry, which is the one
    our proxy appended.
    """
    user_key = request.headers.get("X-User-Key")
    if user_key:
        return f"user:{user_key}"

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return f"ip:{real_ip.strip()}"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[-1].strip()}"

    return f"ip:{request.client.host if request.client else 'unknown'}"


async def _is_admin_request(request: Request) -> bool:
    """Return True if the request carries an admin user key."""
    user_key = request.headers.get("X-User-Key")
    if not user_key:
        return False
    try:
        async with AsyncSessionLocal() as db:
            return await is_admin_user_id(db, user_key)
    except Exception as exc:
        logger.warning("Could not resolve admin status for a request: %s", exc)
        return False


def _deny(status_code: int, detail: str, headers: Optional[dict] = None) -> JSONResponse:
    """Build an error response matching FastAPI's {"detail": ...} shape."""
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers or {})


async def policy_middleware(request: Request, call_next):
    """Apply availability, write-auth, and rate-limit policy to every request."""
    path = request.url.path

    if path.startswith(BYPASS_PREFIXES) or request.method == "OPTIONS":
        return await call_next(request)

    config = await get_settings()
    is_write = request.method not in SAFE_METHODS

    if config["maintenance_mode"] and not await _is_admin_request(request):
        return _deny(503, config["maintenance_message"], {"Retry-After": "3600"})

    if is_write and config["read_only_mode"]:
        return _deny(503, "This instance is currently read-only")

    if is_write and config["require_auth_for_writes"] and not request.headers.get("X-User-Key"):
        return _deny(401, "A user key is required to make changes on this instance")

    if config["rate_limit_enabled"]:
        checks = [("requests", config["rate_limit_requests_per_minute"], 60)]
        if is_write:
            checks.append(("writes", config["rate_limit_writes_per_minute"], 60))
            if UPLOAD_PATH_PATTERN.match(path):
                checks.append(("uploads", config["rate_limit_uploads_per_hour"], 3600))

        retry_after = await _check_windows(checks, _client_key(request), datetime.utcnow())
        if retry_after is not None:
            return _deny(
                429,
                "Rate limit exceeded. Please slow down.",
                {"Retry-After": str(retry_after)},
            )

    return await call_next(request)
