"""In-process API metrics: request rates, latencies, and DB timings.

Each worker accumulates counters into 10-second in-memory buckets and a
background flusher writes one row per bucket to the api_metrics table, so
stats can be aggregated across all gunicorn workers (a single worker only
sees its share of the traffic).
"""
import asyncio
import logging
import os
import time
from collections import deque
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import event, insert, select

from backend.config import settings

logger = logging.getLogger(__name__)

BUCKET_SECONDS = 10
SLOW_QUERY_MS = 100.0
MAX_SLOW_QUERIES_PER_FLUSH = 50

# Per-request DB accounting, set by the middleware for the request's lifetime
_db_acc: ContextVar[Optional[dict]] = ContextVar("metrics_db_acc", default=None)

# Current 10s bucket and closed buckets awaiting flush (single event loop per
# worker, so no locking needed)
_current_bucket: Optional[dict] = None
_pending_buckets: deque = deque(maxlen=120)
_pending_slow_queries: deque = deque(maxlen=MAX_SLOW_QUERIES_PER_FLUSH)

_flusher_task: Optional[asyncio.Task] = None


def _new_bucket(ts: int) -> dict:
    return {
        "ts": ts,
        "requests": 0,
        "errors": 0,
        "client_errors": 0,
        "total_ms": 0.0,
        "max_ms": 0.0,
        "db_ms": 0.0,
        "db_queries": 0,
        "routes": {},
    }


def _record_request(route: str, method: str, status: int, duration_ms: float, db_acc: dict):
    global _current_bucket
    bucket_ts = int(time.time()) // BUCKET_SECONDS * BUCKET_SECONDS
    if _current_bucket is None or _current_bucket["ts"] != bucket_ts:
        if _current_bucket is not None:
            _pending_buckets.append(_current_bucket)
        _current_bucket = _new_bucket(bucket_ts)

    b = _current_bucket
    b["requests"] += 1
    if status >= 500:
        b["errors"] += 1
    elif status >= 400:
        b["client_errors"] += 1
    b["total_ms"] += duration_ms
    b["max_ms"] = max(b["max_ms"], duration_ms)
    b["db_ms"] += db_acc["ms"]
    b["db_queries"] += db_acc["queries"]

    key = f"{method} {route}"
    r = b["routes"].setdefault(key, {"count": 0, "total_ms": 0.0, "errors": 0})
    r["count"] += 1
    r["total_ms"] += duration_ms
    if status >= 500:
        r["errors"] += 1


class MetricsMiddleware:
    """Raw ASGI middleware (safe with streaming bodies, unlike BaseHTTPMiddleware)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not settings.METRICS_ENABLED or scope.get("path") == "/health":
            return await self.app(scope, receive, send)

        start = time.perf_counter()
        status_holder = {"status": 500}
        db_acc = {"ms": 0.0, "queries": 0}
        token = _db_acc.set(db_acc)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            _db_acc.reset(token)
            duration_ms = (time.perf_counter() - start) * 1000
            # scope["route"] is set by FastAPI's router during dispatch
            route = scope.get("route")
            route_path = getattr(route, "path", None) or "(unmatched)"
            _record_request(route_path, scope.get("method", "GET"), status_holder["status"], duration_ms, db_acc)


# ---------------------------------------------------------------------------
# DB timing via cursor events (works for the async engine through sync_engine)
# ---------------------------------------------------------------------------

def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._metrics_start = time.perf_counter()


def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start = getattr(context, "_metrics_start", None)
    if start is None:
        return
    duration_ms = (time.perf_counter() - start) * 1000

    acc = _db_acc.get()
    if acc is not None:
        acc["ms"] += duration_ms
        acc["queries"] += 1

    # Ignore our own flush/aggregation statements to avoid self-noise
    if duration_ms >= SLOW_QUERY_MS and "api_metrics" not in statement[:500]:
        _pending_slow_queries.append({
            "statement": " ".join(statement.split())[:300],
            "ms": round(duration_ms, 1),
            "ts": datetime.now(timezone.utc).isoformat(),
        })


def setup_metrics(app):
    """Install the middleware and DB event listeners. Call before app startup."""
    if not settings.METRICS_ENABLED:
        return
    from backend.database import async_engine

    app.add_middleware(MetricsMiddleware)
    event.listen(async_engine.sync_engine, "before_cursor_execute", _before_cursor_execute)
    event.listen(async_engine.sync_engine, "after_cursor_execute", _after_cursor_execute)


# ---------------------------------------------------------------------------
# Flusher
# ---------------------------------------------------------------------------

async def _flush_once():
    """Write closed buckets (plus slow queries collected since last flush) to the DB."""
    global _current_bucket
    from backend.database import AsyncSessionLocal
    from backend.models import ApiMetricBucket

    # Rotate the current bucket if its window has passed
    if _current_bucket is not None and _current_bucket["ts"] + BUCKET_SECONDS <= int(time.time()):
        _pending_buckets.append(_current_bucket)
        _current_bucket = None

    if not _pending_buckets:
        return

    slow = list(_pending_slow_queries)
    _pending_slow_queries.clear()

    rows = []
    while _pending_buckets:
        b = _pending_buckets.popleft()
        rows.append({
            "bucket_ts": datetime.utcfromtimestamp(b["ts"]),
            "worker_pid": os.getpid(),
            "requests": b["requests"],
            "errors": b["errors"],
            "client_errors": b["client_errors"],
            "total_ms": round(b["total_ms"], 2),
            "max_ms": round(b["max_ms"], 2),
            "db_ms": round(b["db_ms"], 2),
            "db_queries": b["db_queries"],
            "routes": {k: {**v, "total_ms": round(v["total_ms"], 2)} for k, v in b["routes"].items()},
            "slow_queries": None,
        })
    # Attach the slow-query batch to the newest row
    if slow:
        rows[-1]["slow_queries"] = slow

    async with AsyncSessionLocal() as session:
        await session.execute(insert(ApiMetricBucket), rows)
        await session.commit()


async def _flusher_loop():
    while True:
        try:
            await asyncio.sleep(BUCKET_SECONDS)
            await _flush_once()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Metrics flush failed: {e}")


async def start_metrics_flusher():
    global _flusher_task
    if settings.METRICS_ENABLED and _flusher_task is None:
        _flusher_task = asyncio.create_task(_flusher_loop())
        logger.info("API metrics flusher started")


async def stop_metrics_flusher():
    global _flusher_task
    if _flusher_task is not None:
        _flusher_task.cancel()
        _flusher_task = None
        try:
            await _flush_once()
        except Exception as e:
            logger.error(f"Final metrics flush failed: {e}")


# ---------------------------------------------------------------------------
# Aggregation for the admin endpoint
# ---------------------------------------------------------------------------

WINDOWS = {"5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "24h": 86400}


async def aggregate_metrics(db, window: str = "15m") -> dict:
    """Aggregate api_metrics rows across workers into headline stats,
    a zero-filled time series, per-route totals, and recent slow queries."""
    from backend.models import ApiMetricBucket

    window_s = WINDOWS.get(window, 900)
    bin_s = BUCKET_SECONDS if window_s <= 900 else (60 if window_s <= 21600 else 300)

    now_ts = int(time.time()) // BUCKET_SECONDS * BUCKET_SECONDS
    cutoff_ts = now_ts - window_s
    cutoff = datetime.utcfromtimestamp(cutoff_ts)

    result = await db.execute(
        select(ApiMetricBucket).where(ApiMetricBucket.bucket_ts >= cutoff).order_by(ApiMetricBucket.bucket_ts)
    )
    buckets = result.scalars().all()

    totals = {"requests": 0, "errors": 0, "client_errors": 0, "total_ms": 0.0,
              "max_ms": 0.0, "db_ms": 0.0, "db_queries": 0}
    last_minute_requests = 0
    last_minute_cutoff = datetime.utcfromtimestamp(now_ts - 60)
    bins: dict = {}
    routes: dict = {}
    slow_queries: list = []

    for b in buckets:
        totals["requests"] += b.requests
        totals["errors"] += b.errors
        totals["client_errors"] += b.client_errors
        totals["total_ms"] += b.total_ms
        totals["max_ms"] = max(totals["max_ms"], b.max_ms)
        totals["db_ms"] += b.db_ms
        totals["db_queries"] += b.db_queries

        if b.bucket_ts >= last_minute_cutoff:
            last_minute_requests += b.requests

        bin_ts = int(b.bucket_ts.replace(tzinfo=timezone.utc).timestamp()) // bin_s * bin_s
        entry = bins.setdefault(bin_ts, {"requests": 0, "errors": 0, "total_ms": 0.0, "db_ms": 0.0})
        entry["requests"] += b.requests
        entry["errors"] += b.errors
        entry["total_ms"] += b.total_ms
        entry["db_ms"] += b.db_ms

        for key, r in (b.routes or {}).items():
            agg = routes.setdefault(key, {"count": 0, "total_ms": 0.0, "errors": 0})
            agg["count"] += r.get("count", 0)
            agg["total_ms"] += r.get("total_ms", 0.0)
            agg["errors"] += r.get("errors", 0)

        if b.slow_queries:
            slow_queries.extend(b.slow_queries)

    # Zero-filled series over the whole window
    series = []
    for ts in range(cutoff_ts // bin_s * bin_s, now_ts + 1, bin_s):
        entry = bins.get(ts, {"requests": 0, "errors": 0, "total_ms": 0.0, "db_ms": 0.0})
        series.append({
            "ts": ts,
            "req_per_s": round(entry["requests"] / bin_s, 3),
            "errors": entry["errors"],
            "avg_ms": round(entry["total_ms"] / entry["requests"], 2) if entry["requests"] else 0,
            "avg_db_ms": round(entry["db_ms"] / entry["requests"], 2) if entry["requests"] else 0,
        })

    def _route_list(sort_key):
        items = []
        for key, r in routes.items():
            items.append({
                "route": key,
                "count": r["count"],
                "total_ms": round(r["total_ms"], 1),
                "avg_ms": round(r["total_ms"] / r["count"], 2) if r["count"] else 0,
                "errors": r["errors"],
            })
        items.sort(key=lambda x: x[sort_key], reverse=True)
        return items[:10]

    slow_queries.sort(key=lambda q: q.get("ms", 0), reverse=True)

    req = totals["requests"]
    return {
        "window": window,
        "bin_seconds": bin_s,
        "summary": {
            "requests": req,
            "req_per_s": round(req / window_s, 3),
            "req_per_s_now": round(last_minute_requests / 60, 3),
            "errors": totals["errors"],
            "client_errors": totals["client_errors"],
            "error_rate": round(totals["errors"] / req, 4) if req else 0,
            "avg_ms": round(totals["total_ms"] / req, 2) if req else 0,
            "max_ms": round(totals["max_ms"], 2),
            "avg_db_ms": round(totals["db_ms"] / req, 2) if req else 0,
            "db_queries_per_s": round(totals["db_queries"] / window_s, 3),
        },
        "series": series,
        "top_routes_by_count": _route_list("count"),
        "top_routes_by_time": _route_list("total_ms"),
        "slow_queries": slow_queries[:20],
    }


async def cleanup_old_metrics():
    """Delete api_metrics rows older than the retention window (scheduled job)."""
    from sqlalchemy import delete
    from backend.database import AsyncSessionLocal
    from backend.models import ApiMetricBucket

    cutoff = datetime.utcnow() - timedelta(hours=settings.METRICS_RETENTION_HOURS)
    async with AsyncSessionLocal() as session:
        result = await session.execute(delete(ApiMetricBucket).where(ApiMetricBucket.bucket_ts < cutoff))
        await session.commit()
    logger.info(f"Metrics cleanup: deleted {result.rowcount} buckets older than {settings.METRICS_RETENTION_HOURS}h")
