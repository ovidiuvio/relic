"""Storage service for S3/MinIO integration."""
import io
import asyncio
from typing import Optional, Tuple, Union, BinaryIO
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
from backend.config import settings


class StorageService:
    """Service for storing and retrieving relic content."""

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
            if not self.client.bucket_exists(bucket_name=self.bucket_name):
                self.client.make_bucket(bucket_name=self.bucket_name)
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")

    async def upload(self, key: str, data: Union[bytes, BinaryIO], content_type: str = "application/octet-stream", length: Optional[int] = None) -> str:
        """
        Upload content to S3.

        Args:
            key: S3 object key
            data: Content as bytes or file-like object
            content_type: MIME type
            length: Content length (required if data is a stream)

        Returns:
            S3 key
        """
        try:
            if isinstance(data, bytes):
                data_stream = io.BytesIO(data)
                length = len(data)
            else:
                data_stream = data
                if length is None:
                    # Try to determine length if not provided
                    try:
                        data.seek(0, 2)
                        length = data.tell()
                        data.seek(0)
                    except (AttributeError, io.UnsupportedOperation):
                         raise ValueError("Length must be provided for stream upload")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=key,
                    data=data_stream,
                    length=length,
                    content_type=content_type
                )
            )
            return key
        except S3Error as e:
            raise Exception(f"Failed to upload to S3: {e}")

    async def copy(self, source_key: str, dest_key: str) -> None:
        """
        Copy object within S3 (server-side copy).

        Args:
            source_key: Source S3 key
            dest_key: Destination S3 key
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.copy_object(
                    bucket_name=self.bucket_name,
                    object_name=dest_key,
                    source=CopySource(self.bucket_name, source_key)
                )
            )
        except S3Error as e:
            raise Exception(f"Failed to copy S3 object: {e}")

    async def download(self, key: str) -> bytes:
        """
        Download content from S3 (loads into memory).

        Args:
            key: S3 object key

        Returns:
            Content as bytes
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.get_object(
                    bucket_name=self.bucket_name,
                    object_name=key
                )
            )
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            raise Exception(f"Failed to download from S3: {e}")

    async def download_stream(self, key: str):
        """
        Get download stream from S3.

        Args:
            key: S3 object key

        Returns:
            MinIO response object (stream)
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.client.get_object(
                    bucket_name=self.bucket_name,
                    object_name=key
                )
            )
        except S3Error as e:
            raise Exception(f"Failed to download stream from S3: {e}")

    async def delete(self, key: str) -> None:
        """Delete object from S3."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.remove_object(
                    bucket_name=self.bucket_name,
                    object_name=key
                )
            )
        except S3Error as e:
            raise Exception(f"Failed to delete from S3: {e}")

    async def exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.stat_object(
                    bucket_name=self.bucket_name,
                    object_name=key
                )
            )
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise Exception(f"Error checking object: {e}")


# Global storage service instance
storage_service = StorageService()
