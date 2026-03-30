"""Report endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from backend.database import get_db
from backend.models import Relic, RelicReport
from backend.schemas import ReportCreate

router = APIRouter(prefix="/api/v1")


@router.post("/reports", response_model=dict)
async def create_report(
    report: ReportCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Report a relic for inappropriate content.
    """
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
