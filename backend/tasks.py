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
            Relic.expires_at <= now
        ).all()

        for relic in expired_relics:
            try:
                # Delete from storage
                await storage_service.delete(relic.s3_key)
                # Hard delete from database
                db.delete(relic)
                db.commit()
                print(f"Expired relic {relic.id} permanently deleted")
            except Exception as e:
                print(f"Error cleaning up relic {relic.id}: {e}")
                db.rollback()

    finally:
        db.close()