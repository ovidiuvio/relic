from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models import Relic, ClientKey, ClientBookmark, RelicReport
from backend.app.services.storage import storage_service
from backend.app.services.backup import list_all_backups, perform_backup
from backend.app.api.deps import get_admin_client, is_admin_client

router = APIRouter()

@router.get("/check")
async def admin_check(request: Request, db: Session = Depends(get_db)):
    """
    Check if current client has admin privileges.

    Returns admin status without throwing error.
    """
    # We use get_client_key indirectly or just manually check
    # But since we have get_admin_client which raises exception, we need a gentler check here
    from backend.app.api.deps import get_client_key
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
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all relics including private ones.
    """
    get_admin_client(request, db)  # Verify admin

    query = db.query(Relic)

    if access_level:
        query = query.filter(Relic.access_level == access_level)

    if client_id:
        query = query.filter(Relic.client_id == client_id)

    total = query.count()
    relics = query.order_by(Relic.created_at.desc()).offset(offset).limit(limit).all()

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
                "created_at": r.created_at,
                "expires_at": r.expires_at
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
    """
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
    [ADMIN] Get application configuration.
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
async def admin_list_backups_endpoint(
    request: Request,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all database backups.
    """
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
        return {
            "total": 0,
            "total_size_bytes": 0,
            "backups": [],
            "error": str(e)
        }


@router.post("/backups", response_model=dict)
async def admin_create_backup(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Trigger a manual database backup.
    """
    get_admin_client(request, db)

    try:
        success = await perform_backup(backup_type='manual')
        if success:
            return {"success": True, "message": "Backup completed successfully"}
        else:
            return {"success": False, "message": "Backup failed - check server logs"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/backups/{filename}/download")
async def admin_download_backup(
    filename: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Download a specific backup file.
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
        raise HTTPException(status_code=404, detail=f"Backup not found: {str(e)}")


@router.get("/reports", response_model=dict)
async def admin_list_reports(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    [ADMIN] List all reports.
    """
    get_admin_client(request, db)

    total = db.query(RelicReport).count()
    reports = db.query(RelicReport).order_by(
        RelicReport.created_at.desc()
    ).offset(offset).limit(limit).all()

    # Enrich with relic names
    report_responses = []
    for r in reports:
        relic = db.query(Relic).filter(Relic.id == r.relic_id).first()
        report_responses.append({
            "id": r.id,
            "relic_id": r.relic_id,
            "reason": r.reason,
            "created_at": r.created_at,
            "relic_name": relic.name if relic else "Unknown (Deleted)"
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
    """
    get_admin_client(request, db)

    report = db.query(RelicReport).filter(RelicReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()

    return {"message": "Report dismissed successfully"}
