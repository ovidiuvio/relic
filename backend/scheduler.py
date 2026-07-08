"""
Centralized background task scheduler.

Coordinates all periodic maintenance tasks including:
- Database backups
- Backup retention cleanup
- Expired relic cleanup
"""
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings
from backend.backup import perform_backup, cleanup_old_backups
from backend.tasks import cleanup_expired_relics

logger = logging.getLogger('relic.scheduler')

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

import uuid
import inspect
from functools import wraps
from datetime import datetime, timezone
from contextvars import ContextVar
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_SUBMITTED

# Context variable to track the active job run ID
current_run_id = ContextVar("current_run_id", default=None)

# Thread-safe in-memory history log
job_history = []

class JobRunLogHandler(logging.Handler):
    """Custom logging handler to route logs from a specific job run back to its history entry."""
    def emit(self, record):
        run_id = current_run_id.get()
        if not run_id:
            return
        # Only capture logs from our own backend/relic modules to avoid third-party library noise
        if not record.name.startswith("backend") and not record.name.startswith("relic"):
            return
        try:
            msg = self.format(record)
            for entry in reversed(job_history):
                if entry.get("run_id") == run_id:
                    if "logs" not in entry:
                        entry["logs"] = []
                    entry["logs"].append(msg)
                    if len(entry["logs"]) > 1000:
                        entry["logs"].pop(0)
                    break
        except Exception:
            self.handleError(record)


def wrap_job(func, job_id: str):
    """Wrapper function to bind the active job run_id to contextvars for log capturing."""
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            run_id = None
            for entry in reversed(job_history):
                if entry["job_id"] == job_id and entry["status"] == "running":
                    run_id = entry["run_id"]
                    break
            if not run_id:
                run_id = str(uuid.uuid4())
            token = current_run_id.set(run_id)
            try:
                return await func(*args, **kwargs)
            finally:
                current_run_id.reset(token)
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            run_id = None
            for entry in reversed(job_history):
                if entry["job_id"] == job_id and entry["status"] == "running":
                    run_id = entry["run_id"]
                    break
            if not run_id:
                run_id = str(uuid.uuid4())
            token = current_run_id.set(run_id)
            try:
                return func(*args, **kwargs)
            finally:
                current_run_id.reset(token)
        return sync_wrapper


def scheduler_listener(event):
    global job_history
    try:
        if event.code == EVENT_JOB_SUBMITTED:
            job = scheduler.get_job(event.job_id) if scheduler else None
            job_name = job.name if job else event.job_id
            
            entry = {
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
                "logs": []
            }
            job_history.append(entry)
            if len(job_history) > 500:
                job_history.pop(0)
                
        elif event.code in (EVENT_JOB_EXECUTED, EVENT_JOB_ERROR):
            found = False
            for entry in reversed(job_history):
                if entry["job_id"] == event.job_id and entry["status"] == "running":
                    entry["end_time"] = datetime.now(timezone.utc).isoformat()
                    start = datetime.fromisoformat(entry["start_time"])
                    end = datetime.fromisoformat(entry["end_time"])
                    entry["duration"] = round((end - start).total_seconds(), 3)
                    
                    if event.code == EVENT_JOB_EXECUTED:
                        entry["status"] = "success"
                    else:
                        entry["status"] = "failed"
                        entry["error"] = str(event.exception)
                        entry["traceback"] = str(event.traceback) if event.traceback else None
                    found = True
                    break
            
            if not found:
                job = scheduler.get_job(event.job_id) if scheduler else None
                job_name = job.name if job else event.job_id
                entry = {
                    "run_id": str(uuid.uuid4()),
                    "job_id": event.job_id,
                    "job_name": job_name,
                    "status": "success" if event.code == EVENT_JOB_EXECUTED else "failed",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "duration": 0.0,
                    "error": str(event.exception) if event.code == EVENT_JOB_ERROR else None,
                    "traceback": str(event.traceback) if event.code == EVENT_JOB_ERROR and event.traceback else None,
                    "trigger_type": "scheduled",
                    "logs": []
                }
                job_history.append(entry)
                if len(job_history) > 500:
                    job_history.pop(0)
    except Exception as e:
        logger.exception("Error in scheduler listener")


async def run_manual_job_wrapper(job_id: str, func, *args, **kwargs):
    global job_history
    
    run_id = str(uuid.uuid4())
    job = scheduler.get_job(job_id) if scheduler else None
    job_name = job.name if job else job_id
    
    entry = {
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
        "logs": []
    }
    job_history.append(entry)
    if len(job_history) > 500:
        job_history.pop(0)
        
    start_time = datetime.now(timezone.utc)
    token = current_run_id.set(run_id)
    try:
        import inspect
        if inspect.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)
            
        for e in reversed(job_history):
            if e["run_id"] == run_id:
                e["status"] = "success"
                e["end_time"] = datetime.now(timezone.utc).isoformat()
                e["duration"] = round((datetime.now(timezone.utc) - start_time).total_seconds(), 3)
                break
    except Exception as exc:
        import traceback
        for e in reversed(job_history):
            if e["run_id"] == run_id:
                e["status"] = "failed"
                e["end_time"] = datetime.now(timezone.utc).isoformat()
                e["duration"] = round((datetime.now(timezone.utc) - start_time).total_seconds(), 3)
                e["error"] = str(exc)
                e["traceback"] = traceback.format_exc()
                break
        raise exc
    finally:
        current_run_id.reset(token)


async def start_scheduler() -> None:
    """Initialize and start the background task scheduler."""
    global scheduler

    logger.info("Starting background task scheduler...")

    # Configure log capture handler
    if not any(isinstance(h, JobRunLogHandler) for h in logging.getLogger().handlers):
        capture_handler = JobRunLogHandler()
        capture_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
        capture_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(capture_handler)

    scheduler = AsyncIOScheduler(timezone=settings.BACKUP_TIMEZONE)
    scheduler.add_listener(
        scheduler_listener,
        EVENT_JOB_SUBMITTED | EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
    )

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
