"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.config import settings
from backend.database import init_db, async_engine
from backend.storage import storage_service
from backend.backup import perform_backup
from backend.scheduler import start_scheduler, shutdown_scheduler

from backend.routes import health, clients, relics, bookmarks, comments, spaces, reports, admin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database, storage, and backup scheduler on startup."""
    import os
    if not os.getenv("SKIP_DB_INIT"):
        init_db()
    await storage_service.start()
    await storage_service.ensure_bucket()


    # Start background scheduler (handles backups and relic cleanup)
    await start_scheduler()

    # Create backup on startup if enabled
    if settings.BACKUP_ENABLED and settings.BACKUP_ON_STARTUP:
        logger.info("Creating startup backup...")
        await perform_backup(backup_type='startup')


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if settings.BACKUP_ENABLED:
        # Create backup on shutdown
        if settings.BACKUP_ON_SHUTDOWN:
            logger.info("Creating shutdown backup...")
            await perform_backup(backup_type='shutdown')

        # Stop scheduler
        await shutdown_scheduler()

    # Dispose async engine connection pool
    await async_engine.dispose()

    # Close S3 client
    await storage_service.close()


# Include routers - order matters: relics router has catch-all /{relic_id} routes
# so it must be included last
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(clients.router)
app.include_router(bookmarks.router)
app.include_router(comments.router)
app.include_router(spaces.router)
app.include_router(reports.router)
app.include_router(relics.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
