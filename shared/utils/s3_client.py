"""
Shared S3 Client for Collectors.

Simplified S3 client for uploading local images and returning public URLs.
Based on upscaler/src/storage/s3_client.py but without retry decorator dependencies.
"""

import logging
import mimetypes
from typing import Callable, Dict, Optional

import boto3
from botocore.client import BaseClient
from botocore.config import Config as BotocoreConfig


def get_s3_client(cfg: Dict[str, str]) -> BaseClient:
    """Create authenticated S3 client from config credentials.

    Args:
        cfg: Config dict with AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME

    Returns:
        Authenticated boto3 S3 client
    """
    retry_config = BotocoreConfig(
        retries={
            "max_attempts": 5,
            "mode": "adaptive",
        }
    )
    return boto3.client(
        "s3",
        aws_access_key_id=cfg["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["AWS_SECRET_ACCESS_KEY"],
        region_name=cfg["AWS_REGION_NAME"],
        config=retry_config,
    )


def upload_image_to_s3(
    s3_client: BaseClient,
    bucket: str,
    folder: str,
    file_path: str,
    status_fn: Optional[Callable] = None,
) -> str:
    """Upload a local image file to S3 and return its public URL.

    Args:
        s3_client: Authenticated boto3 S3 client
        bucket: S3 bucket name
        folder: S3 key prefix (e.g. "techobloc/images")
        file_path: Absolute path to local image file
        status_fn: Optional status callback

    Returns:
        Public URL: https://{bucket}.s3.amazonaws.com/{folder}/{filename}

    Raises:
        FileNotFoundError: If local file doesn't exist
        botocore.exceptions.ClientError: If S3 upload fails
    """
    import os

    filename = os.path.basename(file_path)
    key = f"{folder}/{filename}" if folder else filename

    # Detect content type from extension
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = "application/octet-stream"

    with open(file_path, "rb") as f:
        file_data = f.read()

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_data,
        ContentType=content_type,
    )

    public_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    logging.info(f"Uploaded {filename} -> {public_url}")

    return public_url
