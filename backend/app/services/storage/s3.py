from __future__ import annotations

import aioboto3
from botocore.config import Config
from typing import Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class S3Service:
    def __init__(self):
        self._session = aioboto3.Session()
        self._client_kwargs = {
            "endpoint_url": settings.S3_ENDPOINT_URL,
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": settings.S3_REGION,
            "config": Config(signature_version="s3v4"),
        }

    async def upload_bytes(self, data: bytes, key: str, content_type: str, bucket: Optional[str] = None) -> str:
        bucket = bucket or settings.S3_BUCKET_OUTPUTS
        async with self._session.client("s3", **self._client_kwargs) as s3:
            await s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        logger.debug("Uploaded to S3", bucket=bucket, key=key, size=len(data))
        return key

    async def upload_file(self, file_path: str, key: str, content_type: str, bucket: Optional[str] = None) -> str:
        bucket = bucket or settings.S3_BUCKET_UPLOADS
        async with self._session.client("s3", **self._client_kwargs) as s3:
            await s3.upload_file(file_path, bucket, key, ExtraArgs={"ContentType": content_type})
        return key

    async def download_bytes(self, key: str, bucket: Optional[str] = None) -> bytes:
        bucket = bucket or settings.S3_BUCKET_OUTPUTS
        async with self._session.client("s3", **self._client_kwargs) as s3:
            response = await s3.get_object(Bucket=bucket, Key=key)
            return await response["Body"].read()

    async def generate_presigned_url(self, key: str, bucket: Optional[str] = None, expiry: int = 3600) -> str:
        bucket = bucket or settings.S3_BUCKET_OUTPUTS
        async with self._session.client("s3", **self._client_kwargs) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiry,
            )
        return url

    async def delete_object(self, key: str, bucket: Optional[str] = None) -> None:
        bucket = bucket or settings.S3_BUCKET_OUTPUTS
        async with self._session.client("s3", **self._client_kwargs) as s3:
            await s3.delete_object(Bucket=bucket, Key=key)

    async def ensure_buckets(self) -> None:
        async with self._session.client("s3", **self._client_kwargs) as s3:
            for bucket in [settings.S3_BUCKET_UPLOADS, settings.S3_BUCKET_OUTPUTS]:
                try:
                    await s3.head_bucket(Bucket=bucket)
                except Exception:
                    await s3.create_bucket(Bucket=bucket)
                    logger.info("Created S3 bucket", bucket=bucket)
