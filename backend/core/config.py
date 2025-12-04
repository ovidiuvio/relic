"""Configuration for the relic application."""
import os
import json
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "Relic"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://relic_user:relic_password@postgres:5432/relic_db")

    # Storage (S3/MinIO) - support both S3_* and MINIO_* env var names
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL") or os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY") or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY") or os.getenv("MINIO_SECRET_KEY", "minioadmin")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME") or os.getenv("MINIO_BUCKET", "relics")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

    # Upload limits
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100 MB

    # Database Backup Configuration
    BACKUP_ENABLED: bool = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
    BACKUP_TIMES: str = os.getenv("BACKUP_TIMES", "02:00,14:00")  # Comma-separated HH:MM
    BACKUP_TIMEZONE: str = os.getenv("BACKUP_TIMEZONE", "UTC")
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))
    BACKUP_RETENTION_WEEKS: int = int(os.getenv("BACKUP_RETENTION_WEEKS", "30"))
    BACKUP_CLEANUP_ENABLED: bool = os.getenv("BACKUP_CLEANUP_ENABLED", "true").lower() == "true"
    BACKUP_ON_STARTUP: bool = os.getenv("BACKUP_ON_STARTUP", "true").lower() == "true"
    BACKUP_ON_SHUTDOWN: bool = os.getenv("BACKUP_ON_SHUTDOWN", "true").lower() == "true"

    # CORS - accept as string from env, parse in validator
    ALLOWED_ORIGINS: str = '["http://localhost:3000", "http://localhost:8000"]'

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        # If it's already a list, convert to JSON string for storage
        if isinstance(v, list):
            return json.dumps(v)
        # If it's a string, try to parse as JSON first
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return json.dumps(parsed)
            except json.JSONDecodeError:
                pass
            # Fallback: split by comma, strip whitespace, and return as JSON string
            origins = [origin.strip() for origin in v.split(",")]
            return json.dumps(origins)
        return json.dumps([])

    class Config:
        env_file = ".env"

    def get_allowed_origins(self) -> List[str]:
        """Get ALLOWED_ORIGINS as a list."""
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        return json.loads(self.ALLOWED_ORIGINS) if isinstance(self.ALLOWED_ORIGINS, str) else []

    def get_backup_times(self) -> List[tuple]:
        """
        Parse BACKUP_TIMES into list of (hour, minute) tuples.

        Example: "02:00,14:00" -> [(2, 0), (14, 0)]

        Returns:
            List of (hour, minute) tuples
        """
        times = []
        for time_str in self.BACKUP_TIMES.split(','):
            time_str = time_str.strip()
            if ':' in time_str:
                hour, minute = time_str.split(':')
                times.append((int(hour), int(minute)))
        return times


settings = Settings()
