"""Background tasks for relic expiration and cleanup."""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import delete
from backend.database import SessionLocal
from backend.models import Relic
from backend.storage import storage_service


async def cleanup_expired_relics():
    """
    Background task to delete expired relics.

    Runs periodically to hard-delete relics that have expired.
    Soft-deleted relics are hard-deleted after 30 days.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find expired relics
        expired_relics = db.query(Relic).filter(
            Relic.expires_at <= now,
            Relic.deleted_at == None
        ).all()

        for relic in expired_relics:
            try:
                # Delete from storage
                await storage_service.delete(relic.s3_key)
                # Mark as deleted
                relic.deleted_at = now
                db.commit()
                print(f"Expired relic {relic.id} marked for deletion")
            except Exception as e:
                print(f"Error cleaning up relic {relic.id}: {e}")
                db.rollback()

        # Find soft-deleted relics older than 30 days
        soft_deleted_cutoff = now - timedelta(days=30)
        old_deleted = db.query(Relic).filter(
            Relic.deleted_at <= soft_deleted_cutoff
        ).all()

        for relic in old_deleted:
            try:
                # Delete from storage if exists
                if await storage_service.exists(relic.s3_key):
                    await storage_service.delete(relic.s3_key)
                # Hard delete from database
                db.query(Relic).filter(Relic.id == relic.id).delete()
                db.commit()
                print(f"Permanently deleted relic {relic.id}")
            except Exception as e:
                print(f"Error permanently deleting relic {relic.id}: {e}")
                db.rollback()

    finally:
        db.close()


async def start_background_tasks():
    """Start background task scheduler."""
    # Run cleanup every hour
    while True:
        try:
            await cleanup_expired_relics()
        except Exception as e:
            print(f"Error in cleanup task: {e}")

        # Wait 1 hour before next run
        await asyncio.sleep(3600)


# For scheduling with APScheduler (if needed in future)
def get_cleanup_job_config():
    """Return APScheduler job configuration for expiration cleanup."""
    return {
        'func': 'backend.tasks:cleanup_expired_relics',
        'trigger': 'interval',
        'hours': 1
    }
