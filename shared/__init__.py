"""
Shared utilities for product collectors.

This package provides common functionality used across multiple collectors.
"""

from .text_utils import (
    text_only,
    plain_text,
    normalize_whitespace,
    extract_bullet_points,
)

from .image_utils import (
    normalize_to_https,
    strip_query_params,
    strip_shopify_size_suffix,
    convert_webp_to_jpg,
    make_absolute_url,
    deduplicate_urls,
    normalize_image_url,
)

from .upc_utils import (
    normalize_upc,
    is_valid_upc,
    upc_12_to_13,
    upc_13_to_12,
    extract_upcs_from_text,
)

from .http_utils import (
    build_browser_headers,
    RateLimiter,
    retry_request,
)

from .json_utils import (
    extract_json_from_script,
    load_json_file,
    save_json_file,
    build_catalog_index,
)

__all__ = [
    # Text utilities
    "text_only",
    "plain_text",
    "normalize_whitespace",
    "extract_bullet_points",
    # Image utilities
    "normalize_to_https",
    "strip_query_params",
    "strip_shopify_size_suffix",
    "convert_webp_to_jpg",
    "make_absolute_url",
    "deduplicate_urls",
    "normalize_image_url",
    # UPC utilities
    "normalize_upc",
    "is_valid_upc",
    "upc_12_to_13",
    "upc_13_to_12",
    "extract_upcs_from_text",
    # HTTP utilities
    "build_browser_headers",
    "RateLimiter",
    "retry_request",
    # JSON utilities
    "extract_json_from_script",
    "load_json_file",
    "save_json_file",
    "build_catalog_index",
]
