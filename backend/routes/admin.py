"""Admin endpoints."""
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response

logger = logging.getLogger(__name__)
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload, joinedload
from typing import Optional

from backend.config import settings
from backend.database import get_db
from backend.models import Relic, ClientKey, ClientBookmark, RelicReport, Comment, Tag
from backend.storage import storage_service
from backend.dependencies import get_client_key, get_admin_client, is_admin_client
from backend.utils import get_fork_counts, clamp_limit

router = APIRouter(prefix="/api/v1/admin")


@router.get("/check")
async def admin_check(request: Request, db: Session = Depends(get_db)):
    """
    Check if current client has admin privileges.

    Returns admin status without throwing error.
    """
    client = get_client_key(request, db)
    return {
        "client_id": client.id if client else None,
        "is_admin": is_admin_client(client)
    }


@router.get("/relics", response_model=dict)
async def admin_list_all_relics(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    access_level: Optional[str] = None,
    client_id: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all relics including private ones.

    Requires admin privileges.
    Optional filters: access_level, client_id, search, tag
    """
    limit = clamp_limit(limit)
    get_admin_client(request, db)  # Verify admin

    query = db.query(Relic).options(selectinload(Relic.tags))

    if access_level:
        query = query.filter(Relic.access_level == access_level)

    if client_id:
        query = query.filter(Relic.client_id == client_id)

    if search:
        term = f"%{search}%"
        tag_subquery = db.query(Relic.id).join(Relic.tags).filter(Tag.name.ilike(term)).subquery()
        query = query.filter(
            Relic.name.ilike(term) |
            Relic.id.ilike(term) |
            Relic.description.ilike(term) |
            Relic.id.in_(tag_subquery)
        )

    if tag:
        query = query.join(Relic.tags).filter(Tag.name.ilike(tag))

    if search or tag:
        query = query.distinct()

    total = query.count()
    relics = query.order_by(Relic.created_at.desc()).offset(offset).limit(limit).all()

    # Fetch all counts in bulk (2 queries instead of N*2)
    relic_ids = [r.id for r in relics]
    comments_counts = {}

    if relic_ids:
        comments_counts = {
            row[0]: row[1]
            for row in db.query(Comment.relic_id, func.count(Comment.id)).filter(
                Comment.relic_id.in_(relic_ids)
            ).group_by(Comment.relic_id).all()
        }
    forks_counts = get_fork_counts(db, relic_ids)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "client_id": client_id,
        "relics": [
            {
                "id": r.id,
                "name": r.name,
                "client_id": r.client_id,
                "content_type": r.content_type,
                "size_bytes": r.size_bytes,
                "access_level": r.access_level,
                "access_count": r.access_count,
                "bookmark_count": r.bookmark_count,
                "comments_count": comments_counts.get(r.id, 0),
                "forks_count": forks_counts.get(r.id, 0),
                "created_at": r.created_at,
                "expires_at": r.expires_at,
                "tags": [{"id": t.id, "name": t.name} for t in r.tags]
            }
            for r in relics
        ]
    }


@router.get("/clients", response_model=dict)
async def admin_list_clients(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all registered clients.

    Requires admin privileges.
    """
    limit = clamp_limit(limit)
    get_admin_client(request, db)

    total = db.query(ClientKey).count()
    clients = db.query(ClientKey).order_by(
        ClientKey.created_at.desc()
    ).offset(offset).limit(limit).all()

    admin_ids = settings.get_admin_client_ids()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "clients": [
            {
                "id": c.id,
                "public_id": c.public_id,
                "name": c.name,
                "created_at": c.created_at,
                "relic_count": c.relic_count,
                "is_admin": c.id in admin_ids
            }
            for c in clients
        ]
    }


@router.get("/stats", response_model=dict)
async def admin_get_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Get system statistics.

    Requires admin privileges.
    """
    get_admin_client(request, db)

    total_relics = db.query(func.count(Relic.id)).scalar() or 0
    total_clients = db.query(func.count(ClientKey.id)).scalar() or 0
    total_size = db.query(func.sum(Relic.size_bytes)).scalar() or 0
    public_relics = db.query(func.count(Relic.id)).filter(
        Relic.access_level == "public"
    ).scalar() or 0
    private_relics = db.query(func.count(Relic.id)).filter(
        Relic.access_level == "private"
    ).scalar() or 0

    return {
        "total_relics": total_relics,
        "total_clients": total_clients,
        "total_size_bytes": total_size,
        "public_relics": public_relics,
        "private_relics": private_relics,
        "admin_count": len(settings.get_admin_client_ids())
    }


@router.delete("/clients/{client_id}")
async def admin_delete_client(
    client_id: str,
    request: Request,
    delete_relics: bool = False,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Delete a client and optionally their relics.

    Requires admin privileges.

    Args:
        delete_relics: If True, also delete all relics owned by this client
    """
    get_admin_client(request, db)

    client = db.query(ClientKey).filter(ClientKey.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Prevent deleting admin clients
    if client_id in settings.get_admin_client_ids():
        raise HTTPException(
            status_code=403,
            detail="Cannot delete admin client"
        )

    if delete_relics:
        # Delete all relics owned by this client
        client_relics = db.query(Relic).filter(Relic.client_id == client_id).all()
        for relic in client_relics:
            try:
                await storage_service.delete(relic.s3_key)
            except Exception as e:
                print(f"Failed to delete file from S3: {e}")
            db.delete(relic)
    else:
        # Just disassociate relics from client
        db.query(Relic).filter(Relic.client_id == client_id).update(
            {Relic.client_id: None}
        )

    # Delete bookmarks
    db.query(ClientBookmark).filter(ClientBookmark.client_id == client_id).delete()

    # Delete client
    db.delete(client)
    db.commit()

    return {"message": f"Client {client_id} deleted successfully"}


@router.get("/config", response_model=dict)
async def admin_get_config(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Get application configuration (environment variables).

    Requires admin privileges.
    """
    get_admin_client(request, db)

    return {
        "app": {
            "APP_NAME": settings.APP_NAME,
            "APP_VERSION": settings.APP_VERSION,
            "DEBUG": settings.DEBUG
        },
        "database": {
            "DATABASE_URL": settings.DATABASE_URL
        },
        "storage": {
            "S3_ENDPOINT_URL": settings.S3_ENDPOINT_URL,
            "S3_ACCESS_KEY": settings.S3_ACCESS_KEY,
            "S3_SECRET_KEY": settings.S3_SECRET_KEY,
            "S3_BUCKET_NAME": settings.S3_BUCKET_NAME,
            "S3_REGION": settings.S3_REGION
        },
        "upload": {
            "MAX_UPLOAD_SIZE": settings.MAX_UPLOAD_SIZE,
            "MAX_UPLOAD_SIZE_MB": settings.MAX_UPLOAD_SIZE / 1024 / 1024
        },
        "backup": {
            "BACKUP_ENABLED": settings.BACKUP_ENABLED,
            "BACKUP_TIMES": settings.BACKUP_TIMES,
            "BACKUP_TIMEZONE": settings.BACKUP_TIMEZONE,
            "BACKUP_RETENTION_DAYS": settings.BACKUP_RETENTION_DAYS,
            "BACKUP_RETENTION_WEEKS": settings.BACKUP_RETENTION_WEEKS,
            "BACKUP_CLEANUP_ENABLED": settings.BACKUP_CLEANUP_ENABLED,
            "BACKUP_ON_STARTUP": settings.BACKUP_ON_STARTUP,
            "BACKUP_ON_SHUTDOWN": settings.BACKUP_ON_SHUTDOWN
        },
        "admin": {
            "ADMIN_CLIENT_IDS": settings.get_admin_client_ids()
        },
        "cors": {
            "ALLOWED_ORIGINS": settings.get_allowed_origins()
        }
    }


@router.get("/backups", response_model=dict)
async def admin_list_backups(
    request: Request,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all database backups.

    Requires admin privileges.
    """
    limit = clamp_limit(limit)
    from backend.backup import list_all_backups

    get_admin_client(request, db)

    try:
        backups = await list_all_backups()

        # Sort by timestamp descending (newest first)
        backups_sorted = sorted(backups, key=lambda x: x['timestamp'], reverse=True)

        total = len(backups_sorted)
        total_size = sum(b['size'] for b in backups_sorted)

        # Apply pagination
        paginated = backups_sorted[offset:offset + limit]

        # Format for response
        formatted = []
        for backup in paginated:
            formatted.append({
                "key": backup['key'],
                "filename": backup['key'].split('/')[-1],
                "timestamp": backup['timestamp'].isoformat(),
                "size_bytes": backup['size'],
                "last_modified": backup['last_modified'].isoformat() if backup.get('last_modified') else None
            })

        return {
            "total": total,
            "total_size_bytes": total_size,
            "limit": limit,
            "offset": offset,
            "backups": formatted
        }
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return {
            "total": 0,
            "total_size_bytes": 0,
            "backups": [],
            "error": "Failed to list backups"
        }


@router.post("/backups", response_model=dict)
async def admin_create_backup(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Trigger a manual database backup.

    Requires admin privileges.
    """
    from backend.backup import perform_backup

    get_admin_client(request, db)

    try:
        success = await perform_backup(backup_type='manual')
        if success:
            return {"success": True, "message": "Backup completed successfully"}
        else:
            return {"success": False, "message": "Backup failed - check server logs"}
    except Exception as e:
        logger.error(f"Manual backup failed: {e}")
        return {"success": False, "message": "Backup operation failed"}


@router.get("/backups/{filename}/download")
async def admin_download_backup(
    filename: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Download a specific backup file.

    Requires admin privileges.
    """
    get_admin_client(request, db)

    # Validate filename format
    if not filename.startswith('backup-') or not filename.endswith('.sql.gz'):
        raise HTTPException(status_code=400, detail="Invalid backup filename")

    key = f"db/{filename}"

    try:
        # Get the backup file from S3
        data = await storage_service.download(key)

        return Response(
            content=data,
            media_type="application/gzip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Failed to download backup: {e}")
        raise HTTPException(status_code=404, detail="Backup not found or an error occurred")


@router.post("/backups/{filename}/restore", response_model=dict)
async def admin_restore_backup(
    filename: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Restore the database from a backup file. DESTRUCTIVE.

    Terminates active connections, replaces all current data with backup content,
    then recycles the SQLAlchemy connection pool.

    Note: After restore, the DB reflects the backup's Alembic migration state.
    The service does NOT auto-run 'alembic upgrade head'.

    Requires admin privileges.
    """
    from backend.backup import perform_restore
    from backend.database import engine

    get_admin_client(request, db)

    if not filename.startswith('backup-') or not filename.endswith('.sql.gz'):
        raise HTTPException(status_code=400, detail="Invalid backup filename")

    # Close the db session before restore terminates all connections.
    # get_db's finally block will call db.close() again, which is safe (idempotent).
    db.close()

    logger.warning(f"Admin restore initiated: {filename}")
    try:
        result = await perform_restore(filename, engine)
        return {"success": True, "message": result['message'], "filename": filename,
                "log": result.get('log', ''), "stdout": result.get('stdout', ''), "stderr": result.get('stderr', '')}
    except Exception as e:
        logger.error(f"Restore failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/restore-upload", response_model=dict)
async def admin_restore_from_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Restore the database from an uploaded .sql.gz file. DESTRUCTIVE.

    Accepts a gzip-compressed SQL dump (as produced by pg_dump).
    Terminates active connections, replaces all current data, recycles the pool.

    Requires admin privileges.
    """
    from backend.backup import perform_restore_upload
    from backend.database import engine

    get_admin_client(request, db)

    if not file.filename or not file.filename.endswith('.sql.gz'):
        raise HTTPException(status_code=400, detail="File must be a .sql.gz backup")

    compressed = await file.read()
    if len(compressed) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    db.close()

    logger.warning(f"Admin restore from upload initiated: {file.filename} ({len(compressed):,} bytes)")
    try:
        result = await perform_restore_upload(compressed, file.filename, engine)
        return {"success": True, "message": result['message'], "filename": file.filename,
                "log": result.get('log', ''), "stdout": result.get('stdout', ''), "stderr": result.get('stderr', '')}
    except Exception as e:
        logger.error(f"Restore from upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports", response_model=dict)
async def admin_list_reports(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all reports.

    Requires admin privileges.
    """
    limit = clamp_limit(limit)
    get_admin_client(request, db)

    total = db.query(RelicReport).count()

    # ⚡ Bolt: Use joinedload(RelicReport.relic) to prevent N+1 queries when accessing relic.name later
    reports = db.query(RelicReport).options(
        joinedload(RelicReport.relic).joinedload(Relic.owner_client)
    ).order_by(
        RelicReport.created_at.desc()
    ).offset(offset).limit(limit).all()

    # Enrich with relic names and owners
    report_responses = []
    for r in reports:
        relic = r.relic
        report_responses.append({
            "id": r.id,
            "relic_id": r.relic_id,
            "reason": r.reason,
            "created_at": r.created_at,
            "relic_name": relic.name if relic else "Unknown (Deleted)",
            "relic_owner_id": relic.client_id if relic else None,
            "relic_owner_name": relic.owner_client.name if relic and relic.owner_client else "Anonymous"
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "reports": report_responses
    }


@router.delete("/reports/{report_id}")
async def admin_delete_report(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Dismiss (delete) a report.

    Requires admin privileges.
    """
    get_admin_client(request, db)

    report = db.query(RelicReport).filter(RelicReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()

    return {"message": "Report dismissed successfully"}
