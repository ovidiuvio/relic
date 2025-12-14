"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.services.storage import storage_service
from backend.app.services.backup import start_backup_scheduler, shutdown_backup_scheduler, perform_backup
from backend.app.routers import relics, clients, admin, comments, bookmarks, reports


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
    init_db()
    storage_service.ensure_bucket()

    # Start backup scheduler
    if settings.BACKUP_ENABLED:
        await start_backup_scheduler()

        # Create backup on startup
        if settings.BACKUP_ON_STARTUP:
            import logging
            logger = logging.getLogger('relic.main')
            logger.info("Creating startup backup...")
            await perform_backup(backup_type='startup')


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if settings.BACKUP_ENABLED:
        # Create backup on shutdown
        if settings.BACKUP_ON_SHUTDOWN:
            import logging
            logger = logging.getLogger('relic.main')
            logger.info("Creating shutdown backup...")
            await perform_backup(backup_type='shutdown')

        # Stop scheduler
        await shutdown_backup_scheduler()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/v1/version")
async def get_version():
    """Get application version."""
    return {"version": settings.APP_VERSION}


# Include Routers
app.include_router(relics.router, prefix="/api/v1/relics", tags=["relics"])
app.include_router(clients.router, prefix="/api/v1/client", tags=["clients"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(bookmarks.router, prefix="/api/v1/bookmarks", tags=["bookmarks"])
app.include_router(comments.router, prefix="/api/v1/relics", tags=["comments"]) # Note: comments routes are /api/v1/relics/{id}/comments, router defines {relic_id}/comments
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
