"""Background tasks for paste expiration and cleanup."""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import delete
from backend.database import SessionLocal
from backend.models import Paste
from backend.storage import storage_service


async def cleanup_expired_pastes():
    """
    Background task to delete expired pastes.

    Runs periodically to hard-delete pastes that have expired.
    Soft-deleted pastes are hard-deleted after 30 days.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find expired pastes
        expired_pastes = db.query(Paste).filter(
            Paste.expires_at <= now,
            Paste.deleted_at == None
        ).all()

        for paste in expired_pastes:
            try:
                # Delete from storage
                await storage_service.delete(paste.s3_key)
                # Mark as deleted
                paste.deleted_at = now
                db.commit()
                print(f"Expired paste {paste.id} marked for deletion")
            except Exception as e:
                print(f"Error cleaning up paste {paste.id}: {e}")
                db.rollback()

        # Find soft-deleted pastes older than 30 days
        soft_deleted_cutoff = now - timedelta(days=30)
        old_deleted = db.query(Paste).filter(
            Paste.deleted_at <= soft_deleted_cutoff
        ).all()

        for paste in old_deleted:
            try:
                # Delete from storage if exists
                if await storage_service.exists(paste.s3_key):
                    await storage_service.delete(paste.s3_key)
                # Hard delete from database
                db.query(Paste).filter(Paste.id == paste.id).delete()
                db.commit()
                print(f"Permanently deleted paste {paste.id}")
            except Exception as e:
                print(f"Error permanently deleting paste {paste.id}: {e}")
                db.rollback()

    finally:
        db.close()


async def start_background_tasks():
    """Start background task scheduler."""
    # Run cleanup every hour
    while True:
        try:
            await cleanup_expired_pastes()
        except Exception as e:
            print(f"Error in cleanup task: {e}")

        # Wait 1 hour before next run
        await asyncio.sleep(3600)


# For scheduling with APScheduler (if needed in future)
def get_cleanup_job_config():
    """Return APScheduler job configuration for expiration cleanup."""
    return {
        'func': 'backend.tasks:cleanup_expired_pastes',
        'trigger': 'interval',
        'hours': 1
    }
