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
import time
import tempfile
import os
from datetime import datetime
from typing import List, Dict
from urllib.parse import urlparse

from sqlalchemy import text

from backend.config import settings
from backend.storage import storage_service

logger = logging.getLogger('relic.backup')


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


async def _run_restore(sql_bytes: bytes, engine, label: str) -> dict:
    """
    Core restore: terminate active connections, dispose pool, run psql.

    Returns:
        Dict with returncode, stdout, stderr, and detailed log lines from each phase
    """
    db_info = parse_database_url(settings.DATABASE_URL)
    log_lines = []
    t_start = time.monotonic()

    def log(msg: str):
        logger.info(msg)
        log_lines.append(msg)

    # ===== Phase 1: Initialization =====
    log(f"\n{'='*60}")
    log(f"[Phase 1] RESTORE INITIALIZATION")
    log(f"{'='*60}")
    log(f"Source: {label}")
    log(f"Target: {db_info['user']}@{db_info['host']}:{db_info['port']}/{db_info['database']}")
    log(f"Raw SQL size: {len(sql_bytes):,} bytes")

    # Count SQL statements
    sql_text_preview = sql_bytes.decode(errors='replace')
    stmt_count = sql_text_preview.count(';')
    log(f"Approximate statements: {stmt_count}")

    # ===== Phase 2: Connection Termination =====
    log(f"\n{'='*60}")
    log(f"[Phase 2] TERMINATE ACTIVE CONNECTIONS")
    log(f"{'='*60}")
    log(f"Querying pg_stat_activity for database: {db_info['database']}")

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # Get details of active connections before terminating
        result = conn.execute(
            text("""
                SELECT pid, usename, application_name, state, query_start
                FROM pg_stat_activity
                WHERE datname = :dbname
                  AND pid <> pg_backend_pid()
                  AND state IS NOT NULL
            """),
            {"dbname": db_info['database']}
        )
        active_conns = result.fetchall()
        log(f"Found {len(active_conns)} active connection(s):")
        for pid, user, app, state, query_start in active_conns:
            log(f"  - PID {pid}: {user}@{app} [{state}]")

        # Now terminate
        result = conn.execute(
            text("""
                SELECT count(*) FROM (
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :dbname
                      AND pid <> pg_backend_pid()
                      AND state IS NOT NULL
                ) t
            """),
            {"dbname": db_info['database']}
        )
        terminated = result.scalar() or 0

    log(f"Terminated {terminated} connection(s)")

    # ===== Phase 3: Connection Pool Management =====
    log(f"\n{'='*60}")
    log(f"[Phase 3] CONNECTION POOL MANAGEMENT")
    log(f"{'='*60}")
    log(f"Disposing SQLAlchemy connection pool...")
    engine.dispose()
    log(f"Pool disposed successfully")

    # ===== Phase 4: SQL Preprocessing & Analysis =====
    log(f"\n{'='*60}")
    log(f"[Phase 4] SQL PREPROCESSING & ANALYSIS")
    log(f"{'='*60}")

    # Strip incompatible parameters
    sql_text = re.sub(
        r'^\s*SET transaction_timeout\s*=\s*[^;]+;\s*$', '',
        sql_bytes.decode(errors='replace'),
        flags=re.MULTILINE
    )
    sql_bytes_cleaned = sql_text.encode()
    stripped_size = len(sql_bytes) - len(sql_bytes_cleaned)

    if stripped_size > 0:
        log(f"Stripped incompatible parameters: {stripped_size:,} bytes")
    log(f"Final SQL size: {len(sql_bytes_cleaned):,} bytes")

    # Parse SQL structure for informational logging
    sql_text = sql_bytes_cleaned.decode(errors='replace')

    # Log the SQL statements themselves (for visibility)
    log(f"\n[SQL STATEMENTS TO BE EXECUTED]")
    log(f"{'-'*60}")
    # Split by semicolon and log each statement (limit to reasonable output)
    statements = [s.strip() for s in sql_text.split(';') if s.strip()]
    log(f"Total statements: {len(statements)}")
    for i, stmt in enumerate(statements[:100], 1):  # Log first 100 statements in detail
        # Truncate very long statements
        if len(stmt) > 300:
            log(f"{i}. {stmt[:300]}...")
        else:
            log(f"{i}. {stmt}")
    if len(statements) > 100:
        log(f"... and {len(statements) - 100} more statements")
    log(f"{'-'*60}\n")

    # Extract CREATE TABLE statements (capture table name properly)
    create_tables = re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:public\.)?(\w+)', sql_text, re.IGNORECASE)
    if create_tables:
        log(f"\nTables to be created/restored: {len(set(create_tables))}")
        for tbl in sorted(set(create_tables)):
            log(f"  • {tbl}")

    # Extract ALTER TABLE statements (look for ADD CONSTRAINT, ADD COLUMN, etc. after table name)
    alter_tables = re.findall(r'ALTER TABLE\s+(?:ONLY\s+)?(?:public\.)?(\w+)\s+(?:ADD|DROP|ENABLE|DISABLE|OWNER|RENAME)', sql_text, re.IGNORECASE)
    if alter_tables:
        log(f"\nAlterations to apply: {len(set(alter_tables))} table(s)")
        for tbl in sorted(set(alter_tables)):
            log(f"  • {tbl}")

    # Extract COPY statements (data loading) with row counts
    copy_stmts = re.findall(r'COPY\s+(?:public\.)?(\w+)\s*\([^)]*\)\s+FROM\s+stdin', sql_text, re.IGNORECASE)
    if copy_stmts:
        log(f"\nData loading: {len(copy_stmts)} COPY statement(s)")
        for tbl in sorted(set(copy_stmts)):
            log(f"  • {tbl}")

    # Extract CREATE INDEX statements
    create_indexes = re.findall(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF NOT EXISTS\s+)?(\w+)\s+ON\s+(?:public\.)?(\w+)', sql_text, re.IGNORECASE)
    if create_indexes:
        log(f"\nIndexes to create: {len(create_indexes)}")
        idx_by_table = {}
        for idx_name, tbl in create_indexes:
            if tbl not in idx_by_table:
                idx_by_table[tbl] = []
            idx_by_table[tbl].append(idx_name)
        for tbl in sorted(idx_by_table.keys()):
            log(f"  • on table {tbl}: {len(idx_by_table[tbl])} index(es)")

    # Extract sequence operations
    sequences = re.findall(r'CREATE SEQUENCE\s+(?:IF NOT EXISTS\s+)?(?:public\.)?(\w+)', sql_text, re.IGNORECASE)
    if sequences:
        log(f"\nSequences to create: {len(set(sequences))}")
        for seq in sorted(set(sequences)):
            log(f"  • {seq}")

    # ===== Phase 5: psql Execution =====
    log(f"\n{'='*60}")
    log(f"[Phase 5] RUNNING PSQL RESTORE")
    log(f"{'='*60}")

    # Write SQL to temp file for better logging
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.sql', delete=False) as tmp:
        tmp.write(sql_bytes_cleaned)
        tmp_path = tmp.name

    try:
        log(f"SQL written to temp file: {tmp_path}")
        log(f"Command: psql -h {db_info['host']} -p {db_info['port']} -U {db_info['user']} -d {db_info['database']} -f {tmp_path} --echo-all --echo-errors --set=VERBOSITY=verbose")
        log(f"Starting psql subprocess...")

        t_psql = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            'psql',
            '--echo-all',
            '--echo-errors',
            f'--set=VERBOSITY=verbose',
            '-h', db_info['host'],
            '-p', str(db_info['port']),
            '-U', db_info['user'],
            '-d', db_info['database'],
            '-f', tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={'PGPASSWORD': db_info['password']}
        )

        log(f"psql process started (PID: {process.pid})")
        stdout, stderr = await process.communicate()
        psql_elapsed = time.monotonic() - t_psql
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file {tmp_path}: {e}")

    stdout_text = stdout.decode(errors='replace')
    stderr_text = stderr.decode(errors='replace')

    log(f"psql exited with code: {process.returncode}")
    log(f"psql execution time: {psql_elapsed:.2f}s")
    log(f"stdout size: {len(stdout_text):,} bytes ({len(stdout_text.splitlines())} lines)")
    log(f"stderr size: {len(stderr_text):,} bytes ({len(stderr_text.splitlines())} lines)")

    # Include full psql output in process log
    if stdout_text:
        log(f"\n{'-'*60}")
        log(f"[psql STDOUT - FULL OUTPUT]")
        log(f"{'-'*60}")
        for line in stdout_text.splitlines():
            log(line)

    if stderr_text:
        log(f"\n{'-'*60}")
        log(f"[psql STDERR - FULL OUTPUT]")
        log(f"{'-'*60}")
        for line in stderr_text.splitlines():
            log(line)

    if process.returncode != 0:
        logger.error(f"psql restore failed (rc={process.returncode}): {stderr_text}")
        raise RuntimeError(f"psql restore failed (rc={process.returncode}):\n{stderr_text}")

    # ===== Phase 6: Completion =====
    total_elapsed = time.monotonic() - t_start
    log(f"\n{'='*60}")
    log(f"[Phase 6] RESTORE COMPLETE")
    log(f"{'='*60}")
    log(f"Total elapsed time: {total_elapsed:.2f}s")
    log(f"Connections terminated: {terminated}")
    log(f"SQL bytes processed: {len(sql_bytes_cleaned):,}")
    log(f"Success: ✓")
    log(f"{'='*60}\n")

    return {
        'returncode': process.returncode,
        'stdout': stdout_text,
        'stderr': stderr_text,
        'log': '\n'.join(log_lines),
    }


async def perform_restore(filename: str, engine) -> dict:
    """
    Restore the database from a backup file stored in S3.

    Note: After restore, the DB reflects the backup's Alembic migration state.
    The service does NOT auto-run 'alembic upgrade head'.
    """
    if not filename.startswith('backup-') or not filename.endswith('.sql.gz'):
        raise ValueError(f"Invalid backup filename: {filename}")

    logger.info(f"Downloading backup from S3: db/{filename}")
    compressed = await storage_service.download(f"db/{filename}")
    sql_bytes = gzip.decompress(compressed)
    logger.info(f"Decompressed {len(compressed):,} -> {len(sql_bytes):,} bytes")

    psql_result = await _run_restore(sql_bytes, engine, label=filename)
    return {'success': True, 'filename': filename, 'message': 'Restore completed successfully', **psql_result}


async def perform_restore_upload(compressed: bytes, original_filename: str, engine) -> dict:
    """
    Restore the database from an uploaded .sql.gz file.

    Note: After restore, the DB reflects the backup's Alembic migration state.
    The service does NOT auto-run 'alembic upgrade head'.
    """
    sql_bytes = gzip.decompress(compressed)
    logger.info(f"Decompressed upload {original_filename}: {len(compressed):,} -> {len(sql_bytes):,} bytes")

    psql_result = await _run_restore(sql_bytes, engine, label=original_filename)
    return {'success': True, 'filename': original_filename, 'message': 'Restore completed successfully', **psql_result}


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
        objects = await storage_service.list_objects(prefix='db/')

        for obj in objects:
            try:
                # Parse timestamp from filename
                timestamp = parse_backup_timestamp(obj['key'])
                backups.append({
                    'key': obj['key'],
                    'timestamp': timestamp,
                    'size': obj['size'],
                    'last_modified': obj['last_modified'],
                })
            except ValueError:
                # Skip files that don't match backup naming pattern
                logger.debug(f"Skipping non-backup file: {obj['key']}")

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
