"""Storage service for S3/MinIO integration using aiobotocore."""
import asyncio
import logging
from typing import Optional

from aiobotocore.session import AioSession
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)

# Multipart part size: S3 minimum is 5 MiB (except last part), max 10,000 parts.
# 16 MiB parts allow objects up to 156 GiB while keeping memory usage per upload at one part.
MULTIPART_CHUNK_SIZE = 16 * 1024 * 1024
# copy_object is limited to 5 GiB; larger objects need multipart upload_part_copy
S3_MAX_COPY_SIZE = 5 * 1024 * 1024 * 1024
MULTIPART_COPY_CHUNK_SIZE = 1024 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class FileTooLargeError(Exception):
    """Raised when a streaming upload exceeds the allowed maximum size."""


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

    @staticmethod
    async def _read_part(read, size: int) -> bytes:
        """Read up to `size` bytes from an async read(n) callable, tolerating short reads."""
        buf = bytearray()
        while len(buf) < size:
            chunk = await read(size - len(buf))
            if not chunk:
                break
            buf.extend(chunk)
        return bytes(buf)

    async def upload_stream(
        self,
        key: str,
        read,
        content_type: str = "application/octet-stream",
        max_size: Optional[int] = None,
        max_concurrency: int = 3,
    ) -> int:
        """
        Stream content to S3 via multipart upload with bounded memory.

        Args:
            key: S3 object key
            read: async callable read(n) -> bytes returning b'' at EOF
                  (e.g. UploadFile.read)
            content_type: MIME type
            max_size: if set, abort and raise FileTooLargeError once exceeded
            max_concurrency: parts uploaded in parallel; memory per upload is
                bounded by (max_concurrency + 1) * MULTIPART_CHUNK_SIZE

        Returns:
            Total bytes uploaded
        """
        first = await self._read_part(read, MULTIPART_CHUNK_SIZE)
        if max_size is not None and len(first) > max_size:
            raise FileTooLargeError()

        # Content fits in a single part — plain PUT is cheaper than multipart
        if len(first) < MULTIPART_CHUNK_SIZE:
            await self.client.put_object(
                Bucket=self.bucket_name, Key=key, Body=first, ContentType=content_type,
            )
            return len(first)

        mpu = await self.client.create_multipart_upload(
            Bucket=self.bucket_name, Key=key, ContentType=content_type,
        )
        upload_id = mpu['UploadId']

        # Up to max_concurrency parts in flight; the semaphore bounds memory
        # to (max_concurrency + 1) parts per upload
        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = []

        async def put_part(part_number: int, body: bytes) -> dict:
            try:
                part = await self.client.upload_part(
                    Bucket=self.bucket_name, Key=key,
                    PartNumber=part_number, UploadId=upload_id, Body=body,
                )
                return {'ETag': part['ETag'], 'PartNumber': part_number}
            finally:
                semaphore.release()

        try:
            total = 0
            part_number = 1
            chunk = first
            while chunk:
                total += len(chunk)
                if max_size is not None and total > max_size:
                    raise FileTooLargeError()
                # Surface part failures early instead of reading the rest of the body
                for t in tasks:
                    if t.done() and t.exception():
                        raise t.exception()
                await semaphore.acquire()
                tasks.append(asyncio.create_task(put_part(part_number, chunk)))
                part_number += 1
                chunk = await self._read_part(read, MULTIPART_CHUNK_SIZE)
            parts = list(await asyncio.gather(*tasks))
            await self.client.complete_multipart_upload(
                Bucket=self.bucket_name, Key=key, UploadId=upload_id,
                MultipartUpload={'Parts': parts},
            )
            return total
        except BaseException:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await self.client.abort_multipart_upload(
                    Bucket=self.bucket_name, Key=key, UploadId=upload_id,
                )
            except Exception as abort_err:
                logger.warning(f"Failed to abort multipart upload {upload_id} for {key}: {abort_err}")
            raise

    async def stream(self, key: str, chunk_size: int = DOWNLOAD_CHUNK_SIZE):
        """
        Open an object for streaming download.

        Returns:
            (async chunk iterator, content length in bytes)
        """
        response = await self.client.get_object(Bucket=self.bucket_name, Key=key)
        body = response['Body']

        async def iterator():
            try:
                while True:
                    chunk = await body.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                body.close()

        return iterator(), response['ContentLength']

    async def copy(self, src_key: str, dst_key: str, size: int, content_type: str) -> None:
        """
        Server-side copy of an object — no data flows through the application.

        Objects over 5 GiB use multipart upload_part_copy (copy_object's hard limit).
        """
        source = {'Bucket': self.bucket_name, 'Key': src_key}
        if size <= S3_MAX_COPY_SIZE:
            await self.client.copy_object(
                Bucket=self.bucket_name, Key=dst_key, CopySource=source,
                MetadataDirective='REPLACE', ContentType=content_type,
            )
            return

        mpu = await self.client.create_multipart_upload(
            Bucket=self.bucket_name, Key=dst_key, ContentType=content_type,
        )
        upload_id = mpu['UploadId']
        try:
            parts = []
            part_number = 1
            for start in range(0, size, MULTIPART_COPY_CHUNK_SIZE):
                end = min(start + MULTIPART_COPY_CHUNK_SIZE, size) - 1
                part = await self.client.upload_part_copy(
                    Bucket=self.bucket_name, Key=dst_key,
                    PartNumber=part_number, UploadId=upload_id,
                    CopySource=source, CopySourceRange=f"bytes={start}-{end}",
                )
                parts.append({'ETag': part['CopyPartResult']['ETag'], 'PartNumber': part_number})
                part_number += 1
            await self.client.complete_multipart_upload(
                Bucket=self.bucket_name, Key=dst_key, UploadId=upload_id,
                MultipartUpload={'Parts': parts},
            )
        except Exception:
            try:
                await self.client.abort_multipart_upload(
                    Bucket=self.bucket_name, Key=dst_key, UploadId=upload_id,
                )
            except Exception as abort_err:
                logger.warning(f"Failed to abort multipart copy {upload_id} for {dst_key}: {abort_err}")
            raise

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

    async def list_objects(self, prefix: str = '', recursive: bool = True):
        """
        List objects under a prefix as an async generator.

        Args:
            prefix: S3 key prefix to filter by
            recursive: If False, use delimiter to list only immediate children

        Yields:
            Dicts with keys: key, size, last_modified
        """
        paginator = self.client.get_paginator('list_objects_v2')
        kwargs = {'Bucket': self.bucket_name, 'Prefix': prefix}
        if not recursive:
            kwargs['Delimiter'] = '/'
        async for page in paginator.paginate(**kwargs):
            for obj in page.get('Contents', []):
                yield {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                }


# Global storage service instance (client created lazily during startup)
storage_service = StorageService()
