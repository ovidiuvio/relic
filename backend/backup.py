"""
Database backup service with tiered retention.

Handles:
- Automatic PostgreSQL backups (pg_dump via subprocess)
- Gzip compression (~70-90% reduction)
- S3/MinIO storage under db/ folder
- Tiered retention (daily/weekly/monthly)
- APScheduler integration for twice-daily backups
- Startup/shutdown backups
"""

import logging
import gzip
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings
from backend.storage import storage_service

logger = logging.getLogger('relic.backup')

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


# ===== Core Backup Functions =====

async def perform_backup(backup_type: str = 'scheduled') -> bool:
    """
    Execute a single backup operation.

    Args:
        backup_type: Type of backup ('scheduled', 'startup', 'shutdown', 'manual')

    Returns:
        True if backup succeeded, False otherwise
    """
    logger.info(f"Starting {backup_type} backup...")

    for attempt in range(1, 4):  # 3 attempts with exponential backoff
        try:
            # Parse DATABASE_URL for connection details
            db_info = parse_database_url(settings.DATABASE_URL)

            # Execute pg_dump as subprocess
            logger.debug(f"Executing pg_dump (attempt {attempt}/3)...")
            process = await asyncio.create_subprocess_exec(
                'pg_dump',
                '-h', db_info['host'],
                '-p', str(db_info['port']),
                '-U', db_info['user'],
                '-d', db_info['database'],
                '--clean',
                '--if-exists',
                '--no-owner',
                '--no-acl',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={'PGPASSWORD': db_info['password']}
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"pg_dump failed with exit code {process.returncode}: {error_msg}")

            # Compress with gzip
            logger.debug("Compressing backup...")
            compressed = gzip.compress(stdout, compresslevel=9)
            compression_ratio = (1 - len(compressed) / len(stdout)) * 100 if len(stdout) > 0 else 0

            # Generate filename and upload to S3
            key = generate_backup_filename(backup_type)
            logger.debug(f"Uploading to S3: {key}")
            await storage_service.upload(key, compressed, 'application/gzip')

            logger.info(
                f"Backup completed successfully: {key} "
                f"({len(compressed):,} bytes compressed from {len(stdout):,} bytes, "
                f"{compression_ratio:.1f}% reduction)"
            )
            return True

        except Exception as e:
            logger.warning(f"Backup attempt {attempt} failed: {e}")
            if attempt < 3:
                wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s
                logger.debug(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Backup failed after {attempt} attempts", exc_info=True)
                return False

    return False


async def cleanup_old_backups() -> None:
    """
    Delete expired backups based on retention policy.

    Retention tiers:
    - Daily: Keep all backups for 7 days
    - Weekly: Keep one backup per week for 30 days
    - Monthly: Keep one backup per month forever
    """
    logger.info("Starting backup retention cleanup...")

    try:
        # List all backups from S3
        backups = await list_all_backups()

        if not backups:
            logger.info("No backups found to clean up")
            return

        # Classify backups into keep/delete buckets
        result = classify_backups(backups)
        to_keep = result['to_keep']
        to_delete = result['to_delete']

        if not to_delete:
            logger.info(f"All {len(backups)} backups are within retention policy")
            return

        # Delete expired backups
        deleted_count = 0
        deleted_bytes = 0

        for backup in to_delete:
            try:
                await storage_service.delete(backup['key'])
                deleted_count += 1
                deleted_bytes += backup['size']
                logger.debug(f"Deleted expired backup: {backup['key']}")
            except Exception as e:
                logger.error(f"Failed to delete {backup['key']}: {e}")

        logger.info(
            f"Cleanup completed: {deleted_count} backups deleted "
            f"({deleted_bytes / 1024 / 1024:.2f} MB freed), "
            f"{len(to_keep)} backups retained"
        )

    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)


async def list_all_backups() -> List[Dict]:
    """
    List all backups from S3 with metadata.

    Returns:
        List of dicts with keys: key, timestamp, size, last_modified
    """
    backups = []

    try:
        # List objects in db/ folder
        objects = storage_service.client.list_objects(
            bucket_name=storage_service.bucket_name,
            prefix='db/',
            recursive=True
        )

        for obj in objects:
            try:
                # Parse timestamp from filename
                timestamp = parse_backup_timestamp(obj.object_name)
                backups.append({
                    'key': obj.object_name,
                    'timestamp': timestamp,
                    'size': obj.size,
                    'last_modified': obj.last_modified
                })
            except ValueError:
                # Skip files that don't match backup naming pattern
                logger.debug(f"Skipping non-backup file: {obj.object_name}")

        logger.debug(f"Found {len(backups)} backups in S3")
        return backups

    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return []


# ===== Retention Logic =====

def classify_backups(backups: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Classify backups into daily/weekly/monthly retention tiers.

    Retention strategy:
    - Monthly: Keep oldest backup per month (forever)
    - Weekly: Keep oldest backup per week (for 30 days)
    - Daily: Keep all backups (for 7 days)
    - Expired: Delete backups older than 7 days that aren't weekly/monthly

    Args:
        backups: List of backup dicts with 'timestamp' key

    Returns:
        Dict with 'to_keep' and 'to_delete' lists
    """
    now = datetime.utcnow()
    to_keep = []
    to_delete = []

    # Track what we've kept per tier
    kept_weeks = set()   # (year, week_number)
    kept_months = set()  # (year, month)

    # Sort by timestamp (newest first) for consistent tie-breaking
    sorted_backups = sorted(backups, key=lambda x: x['timestamp'], reverse=True)

    for backup in sorted_backups:
        age_days = (now - backup['timestamp']).days
        year = backup['timestamp'].year
        week = backup['timestamp'].isocalendar()[1]  # ISO week number
        month = backup['timestamp'].month

        # Priority 1: Monthly (keep forever, one per month)
        if (year, month) not in kept_months:
            backup['retention_type'] = 'monthly'
            to_keep.append(backup)
            kept_months.add((year, month))

        # Priority 2: Weekly (keep 30 days, one per week)
        elif age_days <= settings.BACKUP_RETENTION_WEEKS and (year, week) not in kept_weeks:
            backup['retention_type'] = 'weekly'
            to_keep.append(backup)
            kept_weeks.add((year, week))

        # Priority 3: Daily (keep 7 days, all backups)
        elif age_days <= settings.BACKUP_RETENTION_DAYS:
            backup['retention_type'] = 'daily'
            to_keep.append(backup)

        # Older than 7 days and not weekly/monthly
        else:
            backup['retention_type'] = 'expired'
            to_delete.append(backup)

    # Log retention summary
    daily_count = sum(1 for b in to_keep if b.get('retention_type') == 'daily')
    weekly_count = sum(1 for b in to_keep if b.get('retention_type') == 'weekly')
    monthly_count = sum(1 for b in to_keep if b.get('retention_type') == 'monthly')

    logger.debug(
        f"Retention classification: {len(to_keep)} to keep "
        f"({daily_count} daily, {weekly_count} weekly, {monthly_count} monthly), "
        f"{len(to_delete)} to delete"
    )

    return {'to_keep': to_keep, 'to_delete': to_delete}


# ===== Scheduling =====

async def start_backup_scheduler() -> None:
    """Initialize and start the backup scheduler."""
    global scheduler

    if not settings.BACKUP_ENABLED:
        logger.info("Backups disabled via BACKUP_ENABLED=false")
        return

    logger.info("Starting backup scheduler...")

    scheduler = AsyncIOScheduler(timezone=settings.BACKUP_TIMEZONE)

    # Parse backup times from config and add cron jobs
    backup_times = settings.get_backup_times()
    logger.info(f"Scheduling backups for times: {backup_times}")

    for hour, minute in backup_times:
        job_id = f'backup_{hour:02d}{minute:02d}'
        scheduler.add_job(
            func=perform_backup,
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
            func=cleanup_old_backups,
            trigger=CronTrigger(hour=3, minute=0, timezone=settings.BACKUP_TIMEZONE),
            id='backup_cleanup',
            name='Backup Retention Cleanup',
            replace_existing=True
        )
        logger.debug("Scheduled cleanup job: backup_cleanup at 03:00")
    else:
        logger.info("Backup cleanup disabled via BACKUP_CLEANUP_ENABLED=false")

    scheduler.start()
    logger.info("Backup scheduler started successfully")


async def shutdown_backup_scheduler() -> None:
    """Gracefully shutdown the backup scheduler."""
    global scheduler

    if scheduler:
        logger.info("Shutting down backup scheduler...")
        scheduler.shutdown(wait=True)
        logger.info("Backup scheduler stopped")


# ===== Utilities =====

def parse_database_url(url: str) -> Dict[str, any]:
    """
    Parse DATABASE_URL into connection components.

    Args:
        url: PostgreSQL connection URL
             (e.g., postgresql://user:pass@host:5432/dbname)

    Returns:
        Dict with keys: user, password, host, port, database

    Raises:
        ValueError: If URL format is invalid
    """
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ('postgresql', 'postgres'):
            raise ValueError(f"Invalid scheme: {parsed.scheme} (expected postgresql)")

        return {
            'user': parsed.username,
            'password': parsed.password,
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/')
        }
    except Exception as e:
        raise ValueError(f"Failed to parse DATABASE_URL: {e}")


def generate_backup_filename(backup_type: str = 'scheduled') -> str:
    """
    Generate S3 key for backup file.

    Naming convention:
    - Scheduled: db/backup-YYYY-MM-DD-HH-MM-SS.sql.gz
    - Startup/Shutdown: db/backup-YYYY-MM-DD-{type}.sql.gz
    - Manual: db/backup-YYYY-MM-DD-HH-MM-SS.sql.gz

    Args:
        backup_type: Type of backup (scheduled, startup, shutdown, manual)

    Returns:
        S3 key (e.g., "db/backup-2024-01-15-02-00-00.sql.gz")
    """
    now = datetime.utcnow()

    if backup_type in ('startup', 'shutdown'):
        # For startup/shutdown, use type in filename instead of exact timestamp
        # This prevents multiple backups if service restarts multiple times same day
        return f"db/backup-{now.strftime('%Y-%m-%d')}-{backup_type}.sql.gz"
    else:
        # For scheduled and manual backups, use exact timestamp
        return f"db/backup-{now.strftime('%Y-%m-%d-%H-%M-%S')}.sql.gz"


def parse_backup_timestamp(s3_key: str) -> datetime:
    """
    Extract timestamp from backup filename.

    Supports two formats:
    1. db/backup-YYYY-MM-DD-HH-MM-SS.sql.gz (scheduled/manual)
    2. db/backup-YYYY-MM-DD-{type}.sql.gz (startup/shutdown)

    Args:
        s3_key: S3 object key (e.g., "db/backup-2024-01-15-02-00-00.sql.gz")

    Returns:
        datetime object (UTC)

    Raises:
        ValueError: If filename doesn't match expected pattern
    """
    # Try full timestamp pattern first (scheduled/manual backups)
    pattern_full = r'backup-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})\.sql\.gz'
    match = re.search(pattern_full, s3_key)

    if match:
        year, month, day, hour, minute, second = map(int, match.groups())
        return datetime(year, month, day, hour, minute, second)

    # Try date-only pattern (startup/shutdown backups)
    pattern_date = r'backup-(\d{4})-(\d{2})-(\d{2})-(startup|shutdown)\.sql\.gz'
    match = re.search(pattern_date, s3_key)

    if match:
        year, month, day, _ = match.groups()
        year, month, day = int(year), int(month), int(day)
        # For startup/shutdown, use midday as representative time
        return datetime(year, month, day, 12, 0, 0)

    raise ValueError(f"Invalid backup filename format: {s3_key}")
