"""Screenshot capture and S3 upload for evidence items.

Decodes base64-encoded screenshots from browser agents and uploads
them to S3 (or local MinIO for development). Generates presigned
GET URLs for frontend display.
"""

from __future__ import annotations

import base64
import logging
from uuid import UUID

import boto3
from botocore.config import Config as BotoConfig

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Create an S3 client with MinIO support for local development.

    Returns a tuple of (s3_client, bucket_name).
    When AWS_ENDPOINT_URL_S3 is set (to MinIO), uses path-style access
    and the provided credentials.
    """
    try:
        from config import settings  # type: ignore[import]

        kwargs = {
            "region_name": settings.aws_region,
            "config": BotoConfig(signature_version="s3v4"),
        }

        endpoint = settings.aws_endpoint_url_s3
        if endpoint:
            kwargs["endpoint_url"] = endpoint
            kwargs["aws_access_key_id"] = settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            # MinIO requires path-style addressing
            kwargs["config"] = BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )

        return boto3.client("s3", **kwargs), settings.s3_bucket_evidence
    except Exception:
        import os

        return (
            boto3.client("s3", region_name="us-east-1"),
            os.environ.get("S3_BUCKET_EVIDENCE", "evidence"),
        )


async def upload_screenshot(
    evidence_id: UUID | str,
    mission_id: UUID | str,
    base64_data: str,
) -> str:
    """Decode base64 screenshot and upload to S3/MinIO.

    Args:
        evidence_id: UUID of the evidence item.
        mission_id: UUID of the mission.
        base64_data: Base64-encoded PNG image data.

    Returns:
        The S3 object key for the uploaded screenshot.

    Raises:
        Exception: On S3 upload failure (logged, not suppressed).
    """
    s3, bucket = _get_s3_client()
    key = f"evidence/{mission_id}/{evidence_id}.png"
    image_bytes = base64.b64decode(base64_data)

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=image_bytes,
        ContentType="image/png",
    )
    logger.info(
        "Uploaded screenshot: s3://%s/%s (%d bytes)", bucket, key, len(image_bytes)
    )
    return key


def get_screenshot_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned GET URL for a screenshot.

    Args:
        key: The S3 object key.
        expires_in: URL expiry time in seconds (default 1 hour).

    Returns:
        A presigned URL string for downloading the screenshot.
    """
    s3, bucket = _get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
