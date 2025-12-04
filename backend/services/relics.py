from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import Relic
from backend.utils import generate_relic_id

def generate_unique_relic_id(db: Session, max_retries: int = 5) -> str:
    """
    Generate a unique relic ID with collision handling.
    """
    for attempt in range(max_retries):
        relic_id = generate_relic_id()
        existing = db.query(Relic).filter(Relic.id == relic_id).first()
        if not existing:
            return relic_id
    raise HTTPException(
        status_code=500,
        detail="Failed to generate unique relic ID after multiple attempts"
    )
