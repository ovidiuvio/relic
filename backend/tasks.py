"""Background tasks for relic expiration and cleanup."""
import logging
from datetime import datetime
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models import Relic
from backend.storage import storage_service

logger = logging.getLogger(__name__)


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
            relic_id = relic.id
            s3_key = relic.s3_key
            try:
                # Delete DB record first — if S3 delete later fails, the orphaned
                # S3 object is harmless and reclaimable. The reverse order risks a
                # zombie DB row that retries forever against a missing S3 object.
                await db.delete(relic)
                await db.commit()
                try:
                    await storage_service.delete(s3_key)
                except Exception as s3_err:
                    logger.warning(f"Relic {relic_id} removed from DB but S3 delete failed (orphaned object {s3_key}): {s3_err}")
                logger.info(f"Expired relic {relic_id} permanently deleted")
            except Exception as e:
                logger.error(f"Error cleaning up relic {relic_id}: {e}")
                await db.rollback()
