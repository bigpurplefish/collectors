"""
S3 Client for Aggregates Converter.

Re-exports from shared location. The canonical implementation lives at
collectors/shared/utils/s3_client.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from utils.s3_client import get_s3_client, upload_image_to_s3  # noqa: E402, F401

__all__ = ["get_s3_client", "upload_image_to_s3"]
