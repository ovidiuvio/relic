"""
Centralized background task scheduler.

Coordinates all periodic maintenance tasks including:
- Database backups
- Backup retention cleanup
- Expired relic cleanup

Note on log capture:
    Logs emitted by job functions (from modules under ``backend.*`` or
    ``relic.*``) are captured into the in-memory ``job_history`` entries via
    ``JobRunLogHandler``. Capture is keyed by ``current_run_id`` (a ContextVar
    bound inside ``wrap_job``). Log capture relies on the AsyncIOExecutor
    keeping the coroutine on the same task; if a job is ever scheduled on the
    threadpool executor, ContextVar propagation breaks and logs will silently
    miss. So: keep jobs asyncio-native and avoid ``run_in_executor`` inside
    them, or refactor log-capture to use thread-local detection.
"""
import inspect
import logging
import uuid
from collections import deque
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Optional

import asyncio

from apscheduler.events import EVENT_JOB_SUBMITTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import settings
from backend.backup import perform_backup, cleanup_old_backups
from backend.tasks import cleanup_expired_relics

logger = logging.getLogger('relic.scheduler')

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

# Context variable used by JobRunLogHandler to attribute log records to a run.
current_run_id: ContextVar = ContextVar("current_run_id", default=None)

# In-memory history of recent job runs (newest appended to the right).
# A bounded deque auto-evicts the oldest entries without O(N) pop(0).
job_history: "deque[dict]" = deque(maxlen=500)

# O(1) run_id -> entry index kept in sync with ``job_history``.
# Used by JobRunLogHandler.emit so log routing does not scan the deque.
job_runs_index: "dict[str, dict]" = {}

# Tracks active manual executions to prevent concurrent runs (TOCTOU safe).
_active_manual_runs: "set[str]" = set()

# Tracks explicitly-paused job IDs (set by admin endpoints). Unlike
# ``next_run_time is None``, this survives transient misfire/cron state and is
# the single source of truth for "paused".
paused_job_ids: "set[str]" = set()


def _append_history(entry: dict) -> dict:
    """Append a history entry to the deque and the O(1) index, evicting oldest."""
    if len(job_history) == job_history.maxlen:
        oldest = job_history[0]
        job_runs_index.pop(oldest.get("run_id"), None)
    job_history.append(entry)
    job_runs_index[entry["run_id"]] = entry
    return entry


def _finish_history(run_id: str, *, success: bool, error: Optional[str] = None,
                    traceback_str: Optional[str] = None) -> None:
    """Mark a run terminal and compute duration from its start_time."""
    entry = job_runs_index.get(run_id)
    if not entry:
        return
    entry["end_time"] = datetime.now(timezone.utc).isoformat()
    try:
        start = datetime.fromisoformat(entry["start_time"])
        end = datetime.fromisoformat(entry["end_time"])
        entry["duration"] = round((end - start).total_seconds(), 3)
    except Exception:
        entry["duration"] = None
    entry["status"] = "success" if success else "failed"
    if not success:
        entry["error"] = error
        entry["traceback"] = traceback_str


class JobRunLogHandler(logging.Handler):
    """Routes log records emitted during a job run into that run's entry.

    Only records whose logger name starts with ``backend`` or ``relic`` are
    captured (avoiding third-party library noise). Records outside any job
    run have ``current_run_id == None`` and are ignored.
    """

    def emit(self, record):  # noqa: D401 - logging Handler convention
        run_id = current_run_id.get()
        if not run_id:
            return
        if not (record.name.startswith("backend") or record.name.startswith("relic")):
            return
        # Recursion / bookkeeping failures must never raise back into the
        # logging machinery; swallow silently using handleError (which writes
        # to stderr) — never propagate out of emit.
        try:
            entry = job_runs_index.get(run_id)
            if entry is None:
                return
            logs = entry.setdefault("logs", [])
            logs.append(self.format(record))
            if len(logs) > 1000:
                del logs[: -1000]
        except Exception:
            self.handleError(record)


def _bind_run_id_for_scheduled_job(job_id: str) -> str:
    """Find the run_id of the most-recent SUBMITTED entry for this job.

    Falls back to appending a fresh entry if the SUBMITTED listener missed
    (e.g. job submitted before the listener was attached). Returns the
    run_id to set on ``current_run_id`` and to use when finalising.
    """
    for entry in reversed(job_history):
        if entry["job_id"] == job_id and entry["status"] == "running":
            return entry["run_id"]
    run_id = str(uuid.uuid4())
    _append_history({
        "run_id": run_id,
        "job_id": job_id,
        "job_name": job_id,  # best-effort; SUBMITTED normally supplies nicer
        "status": "running",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "duration": None,
        "error": None,
        "traceback": None,
        "trigger_type": "scheduled",
        "logs": [],
    })
    return run_id


def wrap_job(func, job_id: str):
    """Bind ``current_run_id`` while a scheduled job runs and finalise its entry.

    This wrapper is the single source of truth for run completion state. It
    guarantees:
      * only the entry bound to *this* execution is finalised (no
        interference with concurrent runs of the same job_id);
      * the APScheduler EXECUTED/ERROR listener stays a no-op so concurrent
        runs cannot be cross-attributed by "most-recent running" matching.
    """
    is_async = inspect.iscoroutinefunction(func)

    if is_async:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            run_id = _bind_run_id_for_scheduled_job(job_id)
            token = current_run_id.set(run_id)
            try:
                await func(*args, **kwargs)
                _finish_history(run_id, success=True)
            except Exception as exc:
                import traceback as _tb
                _finish_history(run_id, success=False,
                                error=str(exc), traceback_str=_tb.format_exc())
                raise
            finally:
                current_run_id.reset(token)
        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        run_id = _bind_run_id_for_scheduled_job(job_id)
        token = current_run_id.set(run_id)
        try:
            func(*args, **kwargs)
            _finish_history(run_id, success=True)
        except Exception as exc:
            import traceback as _tb
            _finish_history(run_id, success=False,
                            error=str(exc), traceback_str=_tb.format_exc())
            raise
        finally:
            current_run_id.reset(token)
    return sync_wrapper


def scheduler_listener(event):
    """APScheduler event listener: creates entries on SUBMITTED only.

    Run-completion (success/error + duration) is handled by ``wrap_job``
    itself so concurrent executions of the same job_id cannot be cross-
    attributed by "most-recent running" matching. EXECUTED/ERROR events
    are accepted but ignored.
    """
    try:
        if event.code == EVENT_JOB_SUBMITTED:
            job = scheduler.get_job(event.job_id) if scheduler else None
            job_name = job.name if job else event.job_id
            _append_history({
                "run_id": str(uuid.uuid4()),
                "job_id": event.job_id,
                "job_name": job_name,
                "status": "running",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": None,
                "duration": None,
                "error": None,
                "traceback": None,
                "trigger_type": "scheduled",
                "logs": [],
            })
    except Exception:
        # Never raise from a logging listener: it can deadlock/recurse the
        # logging machinery. current_run_id is None here (listener runs
        # outside job context), so our own capture handler skips it anyway.
        logger.exception("Error in scheduler listener")


def manual_run_locked(job_id: str) -> bool:
    """True when a manual run of ``job_id`` is currently in flight."""
    return job_id in _active_manual_runs


def create_manual_run_entry(job_id: str) -> Optional[str]:
    """Synchronously append a ``running`` manual-run entry; return its run_id.

    Callers schedule ``run_manual_job_wrapper(run_id, ...)`` as FastAPI
    BackgroundTasks *after* invoking this so the entry is visible from
    /admin/jobs before the background coroutine starts — fixing the
    "history empty immediately after run" race the frontend saw.
    """
    if scheduler is None:
        return None
    if job_id in _active_manual_runs:
        return None
    _active_manual_runs.add(job_id)
    job = scheduler.get_job(job_id)
    job_name = job.name if job else job_id
    run_id = str(uuid.uuid4())
    _append_history({
        "run_id": run_id,
        "job_id": job_id,
        "job_name": job_name,
        "status": "running",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "duration": None,
        "error": None,
        "traceback": None,
        "trigger_type": "manual",
        "logs": [],
    })
    return run_id


async def run_manual_job_wrapper(run_id: str, job_id: str, func, *args, **kwargs):
    """Execute a job's function under ``current_run_id=run_id`` for log capture.

    Re-entrancy is guarded by ``_active_manual_runs`` set; concurrent 
    manual triggers return 409 from the route.
    """
    token = current_run_id.set(run_id)
    try:
        if inspect.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)
        _finish_history(run_id, success=True)
    except Exception as exc:
        import traceback as _tb
        _finish_history(
            run_id,
            success=False,
            error=str(exc),
            traceback_str=_tb.format_exc(),
        )
        logger.exception(f"Manual job {job_id} failed")
    finally:
        _active_manual_runs.discard(job_id)
        current_run_id.reset(token)


def serialize_trigger(trigger) -> dict:
    """Stable, structured serialisation of an APScheduler trigger.

    Prefer this over parsing ``str(trigger)`` on the frontend, as the str
    representation is not a guaranteed-stable contract and uses quoted-syntax
    with whitespace variants across versions.
    """
    if isinstance(trigger, IntervalTrigger):
        # APScheduler exposes both: ``interval`` (timedelta) and
        # ``interval_length`` (float seconds, in 3.10+). Prefer timedelta.
        td = getattr(trigger, "interval", None)
        seconds = int(td.total_seconds()) if td is not None else None
        return {
            "type": "interval",
            "seconds": seconds,
            "timezone": str(trigger.timezone) if getattr(trigger, "timezone", None) else None,
            "repr": str(trigger),
            "human": f"Every {seconds}s" if seconds is not None else str(trigger),
        }
    if isinstance(trigger, CronTrigger):
        fields = {}
        for f in trigger.fields:
            fields[str(f.name)] = str(f)
        return {
            "type": "cron",
            "fields": fields,
            "timezone": str(trigger.timezone) if getattr(trigger, "timezone", None) else None,
            "repr": str(trigger),
        }
    if isinstance(trigger, DateTrigger):
        return {
            "type": "date",
            "run_date": trigger.run_date.isoformat() if trigger.run_date else None,
            "timezone": str(trigger.timezone) if getattr(trigger, "timezone", None) else None,
            "repr": str(trigger),
        }
    return {"type": "unknown", "repr": str(trigger)}


async def start_scheduler() -> None:
    """Initialize and start the background task scheduler."""
    global scheduler

    logger.info("Starting background task scheduler...")

    # Attach log-capture handler exactly once, even across restarts.
    root = logging.getLogger()
    if not any(isinstance(h, JobRunLogHandler) for h in root.handlers):
        capture_handler = JobRunLogHandler()
        capture_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
        capture_handler.setLevel(logging.DEBUG)
        root.addHandler(capture_handler)

    scheduler = AsyncIOScheduler(timezone=settings.BACKUP_TIMEZONE)
    scheduler.add_listener(scheduler_listener, EVENT_JOB_SUBMITTED)

    # 1. Schedule Database Backups (if enabled)
    if settings.BACKUP_ENABLED:
        backup_times = settings.get_backup_times()
        logger.info(f"Scheduling backups for times: {backup_times}")

        for hour, minute in backup_times:
            job_id = f'backup_{hour:02d}{minute:02d}'
            scheduler.add_job(
                func=wrap_job(perform_backup, job_id),
                trigger=CronTrigger(hour=hour, minute=minute, timezone=settings.BACKUP_TIMEZONE),
                id=job_id,
                name=f'Database Backup {hour:02d}:{minute:02d}',
                kwargs={'backup_type': 'scheduled'},
                replace_existing=True
            )
            logger.debug(f"Scheduled backup job: {job_id}")

        # Add daily cleanup job at 3 AM (if enabled)
        if settings.BACKUP_CLEANUP_ENABLED:
            scheduler.add_job(
                func=wrap_job(cleanup_old_backups, 'backup_cleanup'),
                trigger=CronTrigger(hour=3, minute=0, timezone=settings.BACKUP_TIMEZONE),
                id='backup_cleanup',
                name='Backup Retention Cleanup',
                replace_existing=True
            )
            logger.debug("Scheduled cleanup job: backup_cleanup at 03:00")
        else:
            logger.info("Backup cleanup disabled via BACKUP_CLEANUP_ENABLED=false")
    else:
        logger.info("Database backups disabled via BACKUP_ENABLED=false")

    # 2. Schedule Relic Expiration Cleanup
    scheduler.add_job(
        func=wrap_job(cleanup_expired_relics, 'relic_cleanup'),
        trigger='interval',
        minutes=settings.RELIC_CLEANUP_INTERVAL,
        id='relic_cleanup',
        name='Expired Relic Cleanup',
        replace_existing=True
    )
    logger.info(f"Scheduled relic cleanup every {settings.RELIC_CLEANUP_INTERVAL} minutes")

    scheduler.start()
    logger.info("Background task scheduler started successfully")


async def shutdown_scheduler() -> None:
    """Gracefully shutdown the background task scheduler."""
    global scheduler

    if scheduler:
        logger.info("Shutting down background task scheduler...")
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("Background task scheduler stopped")