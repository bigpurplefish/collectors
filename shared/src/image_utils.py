"""
Image URL processing utilities for product collectors.

Provides URL normalization, deduplication, and format conversion.
"""

import re
from typing import Optional
from urllib.parse import urljoin


def normalize_to_https(url: Optional[str]) -> str:
    """
    Normalize image URL to HTTPS.

    Converts http:// to https:// and handles protocol-relative URLs.

    Args:
        url: Image URL to normalize

    Returns:
        HTTPS URL or empty string if invalid
    """
    if not url or not isinstance(url, str):
        return ""
    u = url.strip()
    # Protocol-relative URLs
    if u.startswith("//"):
        u = "https:" + u
    # Convert http to https
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    return u


def strip_query_params(url: str) -> str:
    """
    Remove query parameters from URL.

    Args:
        url: URL with potential query params

    Returns:
        URL without query string or fragment
    """
    if not url:
        return ""
    return url.split("?", 1)[0].split("#", 1)[0]


def strip_shopify_size_suffix(url: str) -> str:
    """
    Remove Shopify size suffixes from image URLs.

    Removes size tokens like _pico, _icon, _thumb, _small, _compact,
    _medium, _large, _grande, _NNNxMMM from Shopify CDN URLs.

    Args:
        url: Shopify image URL

    Returns:
        URL without size suffix (original size)
    """
    if not url:
        return ""
    # Strip query params first
    base = strip_query_params(url)
    # Remove size suffixes before extension
    base = re.sub(
        r'_(?:pico|icon|thumb|small|compact|medium|large|grande|[0-9]+x[0-9]+|[0-9]+x)'
        r'(?:_[a-z0-9-]+)*\.(jpe?g|png|gif|webp)$',
        r'.\1',
        base,
        flags=re.I
    )
    return base


def convert_webp_to_jpg(url: str) -> str:
    """
    Convert .webp extension to .jpg.

    Many CDNs serve the same image in both formats.

    Args:
        url: Image URL

    Returns:
        URL with .jpg extension if it was .webp, otherwise unchanged
    """
    if not url:
        return ""
    return re.sub(r'\.webp$', '.jpg', url, flags=re.I)


def make_absolute_url(base_url: str, maybe_relative: str) -> str:
    """
    Convert potentially relative URL to absolute URL.

    Args:
        base_url: Base URL for the site
        maybe_relative: URL that might be relative

    Returns:
        Absolute URL
    """
    if not maybe_relative:
        return ""
    # Already absolute
    if maybe_relative.startswith(("http://", "https://")):
        return maybe_relative
    # Protocol-relative
    if maybe_relative.startswith("//"):
        return "https:" + maybe_relative
    # Use urljoin for root-relative and relative paths
    return urljoin(base_url.rstrip("/") + "/", maybe_relative.lstrip("/"))


def deduplicate_urls(urls: list[str]) -> list[str]:
    """
    Remove duplicate URLs while preserving order.

    Args:
        urls: List of URLs (may contain duplicates)

    Returns:
        Deduplicated list in original order
    """
    seen = set()
    result = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def normalize_image_url(
    url: Optional[str],
    base_url: str = "",
    strip_size: bool = False,
    convert_webp: bool = False
) -> str:
    """
    Comprehensive image URL normalization.

    Applies multiple normalization steps:
    - Makes URL absolute if base_url provided
    - Converts to HTTPS
    - Strips query parameters
    - Optionally strips Shopify size suffixes
    - Optionally converts webp to jpg

    Args:
        url: Image URL to normalize
        base_url: Base URL for making relative URLs absolute
        strip_size: Whether to strip Shopify size suffixes
        convert_webp: Whether to convert .webp to .jpg

    Returns:
        Normalized image URL
    """
    if not url or not isinstance(url, str):
        return ""

    # Make absolute if needed
    if base_url and not url.startswith(("http://", "https://", "//")):
        url = make_absolute_url(base_url, url)

    # Normalize to HTTPS
    url = normalize_to_https(url)

    # Strip query params
    url = strip_query_params(url)

    # Optional: strip size suffixes
    if strip_size:
        url = strip_shopify_size_suffix(url)

    # Optional: convert webp to jpg
    if convert_webp:
        url = convert_webp_to_jpg(url)

    return url
