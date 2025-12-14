"""Utility functions."""
import string
import secrets
from datetime import datetime, timedelta
from typing import Optional
import hashlib


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
        expires_in: "1h", "24h", "7d", "30d", or None

    Returns:
        Datetime object or None
    """
    if not expires_in or expires_in == "never":
        return None

    now = datetime.utcnow()
    multipliers = {"h": 3600, "d": 86400}

    try:
        value = int(expires_in[:-1])
        unit = expires_in[-1]
        seconds = value * multipliers.get(unit, 0)
        return now + timedelta(seconds=seconds)
    except (ValueError, KeyError):
        return None


def is_expired(expires_at: Optional[datetime]) -> bool:
    """Check if a relic has expired."""
    if not expires_at:
        return False
    return datetime.utcnow() > expires_at


def generate_client_id() -> str:
    """
    Generate client identification key.

    Uses the same approach as relic IDs - cryptographically secure
    32-character hexadecimal string with 128 bits of entropy.

    Returns:
        Cryptographically secure 32-character hex string
    """
    return secrets.token_hex(16)


