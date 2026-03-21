"""Utility functions."""
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import hashlib
from sqlalchemy import text
from sqlalchemy.orm import Session


def generate_relic_id() -> str:
    """
    Generate GitHub Gist-style 32-character hexadecimal ID.

    Provides 128 bits of entropy using cryptographically secure
    random number generation. Practically collision-proof and
    resistant to enumeration attacks.

    Format: 32 lowercase hexadecimal characters (0-9, a-f)
    Example: f47ac10b58cc4372a5670e02b2c3d479

    Returns:
        Cryptographically secure 32-character hex string

    Security properties:
        - 128 bits of entropy (16 bytes)
        - Uses os.urandom() via secrets.token_hex()
        - 50% collision probability: ~1.8×10^19 relics
        - Brute force at 1M attempts/sec: ~1.1×10^25 years
        - Same approach as GitHub Gists
    """
    return secrets.token_hex(16)  # 16 bytes = 32 hex characters


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def parse_expiry_string(expires_in: Optional[str]) -> Optional[datetime]:
    """
    Parse expiry string and return expiration datetime.

    Args:
        expires_in: "10m", "1h", "24h", "7d", "30d", "1y", or None

    Returns:
        Datetime object or None
    """
    if not expires_in or expires_in == "never":
        return None

    now = datetime.utcnow()
    multipliers = {
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
        "M": 2592000,  # 30 days
        "y": 31536000  # 365 days
    }

    try:
        value = int(expires_in[:-1])
        unit = expires_in[-1]

        if unit not in multipliers:
            return None

        seconds = value * multipliers[unit]
        return now + timedelta(seconds=seconds)
    except (ValueError, KeyError):
        return None


def is_expired(expires_at: Optional[datetime]) -> bool:
    """Check if a relic has expired."""
    if not expires_at:
        return False
    return datetime.utcnow() > expires_at


def get_fork_counts(db: Session, relic_ids: List[str]) -> Dict[str, int]:
    """
    Count all descendants (direct + indirect) for each relic using a single
    recursive CTE — mirrors GitHub's fork counter behaviour.

    Returns a dict of {relic_id: total_descendant_count}.
    """
    if not relic_ids:
        return {}
    result = db.execute(
        text("""
            WITH RECURSIVE fork_tree AS (
                SELECT fork_of AS root_id, id
                FROM relic
                WHERE fork_of = ANY(:ids)
                UNION ALL
                SELECT ft.root_id, r.id
                FROM relic r
                JOIN fork_tree ft ON r.fork_of = ft.id
            )
            SELECT root_id, COUNT(*) AS total
            FROM fork_tree
            GROUP BY root_id
        """),
        {"ids": relic_ids},
    ).fetchall()
    return {row[0]: row[1] for row in result}


def get_fork_count(db: Session, relic_id: str) -> int:
    """Count all descendants of a single relic using a recursive CTE."""
    row = db.execute(
        text("""
            WITH RECURSIVE fork_tree AS (
                SELECT id FROM relic WHERE fork_of = :relic_id
                UNION ALL
                SELECT r.id FROM relic r
                JOIN fork_tree ft ON r.fork_of = ft.id
            )
            SELECT COUNT(*) FROM fork_tree
        """),
        {"relic_id": relic_id},
    ).scalar()
    return row or 0


