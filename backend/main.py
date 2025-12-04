"""Main FastAPI application."""
from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
import io

from backend.core.config import settings
from backend.database import init_db, get_db, SessionLocal
from backend.models import Relic, ClientKey, ClientBookmark
from backend.schemas import (
    RelicCreate, RelicResponse, RelicListResponse,
    RelicFork
)
from backend.storage import storage_service
from backend.utils import generate_relic_id, parse_expiry_string, is_expired, hash_password, generate_client_id
from backend.backup import start_backup_scheduler, shutdown_backup_scheduler, perform_backup


from backend.core.app import create_app

app = create_app()


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


from backend.api import relics, clients, bookmarks

app.include_router(relics.router, prefix="/api/v1", tags=["relics"])
app.include_router(clients.router, prefix="/api/v1", tags=["clients"])
app.include_router(bookmarks.router, prefix="/api/v1", tags=["bookmarks"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
