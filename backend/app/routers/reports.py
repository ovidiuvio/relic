from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.models import RelicReport, Relic
from backend.app.schemas import ReportCreate

router = APIRouter()

@router.post("", response_model=dict)
async def create_report(
    report: ReportCreate,
    db: Session = Depends(get_db)
):
    """
    Report a relic for inappropriate content.
    """
    # Verify relic exists
    relic = db.query(Relic).filter(Relic.id == report.relic_id).first()
    if not relic:
        raise HTTPException(status_code=404, detail="Relic not found")

    # Create report
    new_report = RelicReport(
        relic_id=report.relic_id,
        reason=report.reason,
        created_at=datetime.utcnow()
    )

    db.add(new_report)
    db.commit()

    return {"message": "Report submitted successfully"}
