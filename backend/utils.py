"""Utility functions."""
import string
import random
from datetime import datetime, timedelta
from typing import Optional
import hashlib


def generate_paste_id(length: int = 8) -> str:
    """
    Generate a base62 paste ID.

    Args:
        length: Length of ID

    Returns:
        Random base62 string
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed


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
    """Check if a paste has expired."""
    if not expires_at:
        return False
    return datetime.utcnow() > expires_at


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
