"""Storage service for S3/MinIO integration."""
import io
import asyncio
from typing import Optional, Tuple
from minio import Minio
from minio.error import S3Error
from backend.config import settings


class StorageService:
    """Service for storing and retrieving paste content."""

    def __init__(self):
        """Initialize MinIO/S3 client."""
        self.client = Minio(
            endpoint=settings.S3_ENDPOINT_URL.replace("http://", "").replace("https://", ""),
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            secure="https" in settings.S3_ENDPOINT_URL
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def ensure_bucket(self) -> None:
        """Ensure bucket exists, create if not."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Upload content to S3.

        Args:
            key: S3 object key
            data: Content as bytes
            content_type: MIME type

        Returns:
            S3 key
        """
        try:
            data_stream = io.BytesIO(data)
            self.client.put_object(
                self.bucket_name,
                key,
                data_stream,
                length=len(data),
                content_type=content_type
            )
            return key
        except S3Error as e:
            raise Exception(f"Failed to upload to S3: {e}")

    async def download(self, key: str) -> bytes:
        """
        Download content from S3.

        Args:
            key: S3 object key

        Returns:
            Content as bytes
        """
        try:
            response = self.client.get_object(self.bucket_name, key)
            return response.read()
        except S3Error as e:
            raise Exception(f"Failed to download from S3: {e}")

    async def delete(self, key: str) -> None:
        """Delete object from S3."""
        try:
            self.client.remove_object(self.bucket_name, key)
        except S3Error as e:
            raise Exception(f"Failed to delete from S3: {e}")

    async def exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.client.stat_object(self.bucket_name, key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise Exception(f"Error checking object: {e}")


# Global storage service instance
storage_service = StorageService()
