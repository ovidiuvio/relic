"""Health and version endpoints."""
from fastapi import APIRouter

from backend.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/api/v1/version")
async def get_version():
    """Get application version."""
    return {"version": settings.APP_VERSION}
