"""Health and version endpoints."""
from fastapi import APIRouter

from backend.config import settings
from backend.runtime_settings import get_settings

router = APIRouter()

# Settings the client needs to render correctly or to pre-validate input.
# Everything else stays admin-only — this endpoint is unauthenticated, so it
# must not become a way to enumerate the instance's security posture.
PUBLIC_SETTING_KEYS = (
    "render_html",
    "render_svg_inline",
    "max_upload_size_bytes",
    "max_comment_length",
    "allow_comments",
    "allow_forking",
    "allow_spaces",
    "allow_reports",
)


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/api/v1/version")
async def get_version():
    """Get application version."""
    return {"version": settings.APP_VERSION}


@router.get("/api/v1/settings")
async def get_public_settings():
    """Get the client-facing subset of runtime settings.

    Unauthenticated: these only describe what the UI should offer, and each is
    also enforced server-side. The client copy is never the security boundary.
    """
    config = await get_settings()
    return {key: config[key] for key in PUBLIC_SETTING_KEYS}
