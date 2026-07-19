"""Report endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from backend.database import get_db
from backend.models import Relic, RelicReport
from backend.schemas import ReportCreate
from backend.dependencies import get_current_user
from backend.runtime_settings import get_settings
from backend.limits import assert_feature_enabled

router = APIRouter(prefix="/api/v1")


@router.post("/reports", response_model=dict)
async def create_report(
    report: ReportCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Report a relic for inappropriate content.
    """
    config = await get_settings()
    assert_feature_enabled(config, "allow_reports", "Reporting")

    # Reporting is unauthenticated by default, which makes the admin queue
    # trivial to flood; instances can require a user key instead.
    if config["require_auth_for_reports"]:
        if not await get_current_user(request, db):
            raise HTTPException(status_code=401, detail="Authentication required to report")

    # Verify relic exists
    result = await db.execute(select(Relic).where(Relic.id == report.relic_id))
    relic = result.scalar_one_or_none()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Create report
    new_report = RelicReport(
        relic_id=report.relic_id,
        reason=report.reason,
        created_at=datetime.utcnow()
    )

    db.add(new_report)
    await db.commit()

    return {"message": "Report submitted successfully"}
