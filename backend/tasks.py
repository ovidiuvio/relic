"""Background tasks for relic expiration and cleanup."""
from datetime import datetime
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models import Relic
from backend.storage import storage_service


async def cleanup_expired_relics():
    """
    Background task to delete expired relics.

    Runs periodically to hard-delete relics that have expired.
    Soft-deleted relics are hard-deleted after 30 days.
    """
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()

        # Find expired relics
        result = await db.execute(
            select(Relic).where(Relic.expires_at <= now)
        )
        expired_relics = result.scalars().all()

        for relic in expired_relics:
            try:
                # Delete from storage
                await storage_service.delete(relic.s3_key)
                # Hard delete from database
                await db.delete(relic)
                await db.commit()
                print(f"Expired relic {relic.id} permanently deleted")
            except Exception as e:
                print(f"Error cleaning up relic {relic.id}: {e}")
                await db.rollback()
