"""Storage service for S3/MinIO integration using aiobotocore."""
import logging
from typing import Optional, List, Dict

from aiobotocore.session import AioSession
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Async service for storing and retrieving relic content via S3-compatible APIs."""

    def __init__(self):
        """Initialize storage service configuration. Call start() to create the async client."""
        self.bucket_name: str = settings.S3_BUCKET_NAME
        self._session: Optional[AioSession] = None
        self._client = None
        self._client_context = None

    async def start(self) -> None:
        """Create the aiobotocore session and S3 client. Call during app startup."""
        self._session = AioSession()
        self._client_context = self._session.create_client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )
        self._client = await self._client_context.__aenter__()

    async def close(self) -> None:
        """Dispose the S3 client. Call during app shutdown."""
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None
            self._client = None

    @property
    def client(self):
        """Access the underlying S3 client."""
        if self._client is None:
            raise RuntimeError("StorageService not started. Call await storage_service.start() first.")
        return self._client

    async def ensure_bucket(self) -> None:
        """Ensure the target bucket exists, create if not."""
        try:
            await self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                kwargs = {'Bucket': self.bucket_name}
                if settings.S3_REGION != 'us-east-1':
                    kwargs['CreateBucketConfiguration'] = {
                        'LocationConstraint': settings.S3_REGION
                    }
                await self.client.create_bucket(**kwargs)
            else:
                logger.error(f"Error ensuring bucket exists: {e}")
                raise

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
            await self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return key
        except ClientError as e:
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
            response = await self.client.get_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            async with response['Body'] as stream:
                return await stream.read()
        except ClientError as e:
            raise Exception(f"Failed to download from S3: {e}")

    async def delete(self, key: str) -> None:
        """Delete object from S3."""
        try:
            await self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )
        except ClientError as e:
            raise Exception(f"Failed to delete from S3: {e}")

    async def exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            await self.client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Error checking object: {e}")

    async def list_objects(self, prefix: str = '', recursive: bool = True) -> List[Dict]:
        """
        List objects under a prefix.

        Args:
            prefix: S3 key prefix to filter by
            recursive: If False, use delimiter to list only immediate children

        Returns:
            List of dicts with keys: key, size, last_modified
        """
        objects = []
        paginator = self.client.get_paginator('list_objects_v2')
        kwargs = {'Bucket': self.bucket_name, 'Prefix': prefix}
        if not recursive:
            kwargs['Delimiter'] = '/'
        async for page in paginator.paginate(**kwargs):
            for obj in page.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                })
        return objects


# Global storage service instance (client created lazily during startup)
storage_service = StorageService()
