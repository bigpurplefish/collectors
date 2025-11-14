"""
Shared image handling utilities for collectors.

Implements requirements from IMAGE_HANDLING_REQUIREMENTS.md including:
- URL querystring stripping
- Image URL verification
- Deduplication
- Alt tag generation for Shopify variant filtering
"""

import requests
from urllib.parse import urlparse, urlunparse
from typing import List, Dict, Any, Optional


def strip_querystring(url: str) -> str:
    """
    Strip querystring from URL while preserving fragment.

    Args:
        url: Image URL potentially containing querystring

    Returns:
        URL with querystring removed

    Examples:
        "https://example.com/image.jpg?v=123" -> "https://example.com/image.jpg"
        "https://example.com/image.jpg" -> "https://example.com/image.jpg"
        "https://example.com/image.jpg#section" -> "https://example.com/image.jpg#section"
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        # Remove query but keep fragment
        return urlunparse(parsed._replace(query=""))
    except:
        return url


def verify_image_url(url: str, timeout: int = 10) -> bool:
    """
    Verify image URL resolves correctly.

    Args:
        url: Image URL to verify
        timeout: Request timeout in seconds

    Returns:
        True if URL returns 200 OK, False otherwise
    """
    if not url:
        return False

    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code == 200
    except:
        # Try GET request as fallback (some servers don't support HEAD)
        try:
            response = requests.get(url, timeout=timeout, stream=True)
            return response.status_code == 200
        except:
            return False


def deduplicate_images(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate images from gallery while preserving order.

    Deduplication is case-insensitive to handle URLs that differ only in case
    (e.g., "image.JPG" vs "image.jpg").

    Args:
        images: List of image dictionaries with 'src' and 'alt' keys

    Returns:
        Deduplicated list with original order preserved
    """
    seen_urls = set()
    deduplicated = []

    for img in images:
        url = strip_querystring(img.get('src', ''))

        # Use lowercase URL for comparison to catch case variations
        url_lower = url.lower()

        if url and url_lower not in seen_urls:
            seen_urls.add(url_lower)
            # Update image to use cleaned URL
            img_copy = img.copy()
            img_copy['src'] = url
            deduplicated.append(img_copy)

    return deduplicated


def generate_variant_alt_tag(option1: str = "", option2: str = "", option3: str = "", option4: str = "") -> str:
    """
    Generate Shopify-compatible alt tag for variant images.

    Format: #option1#option2#option3#option4
    Only populated options are included, with single # separators.

    Args:
        option1: First variant option value (e.g., "Red")
        option2: Second variant option value (e.g., "Large")
        option3: Third variant option value
        option4: Fourth variant option value

    Returns:
        Formatted alt tag string

    Examples:
        ("Red", "", "", "") -> "#Red"
        ("Red", "Large", "", "") -> "#Red#Large"
        ("Blue", "Small", "Wood", "") -> "#Blue#Small#Wood"
    """
    alt_parts = []

    for option_value in [option1, option2, option3, option4]:
        if option_value:
            # Convert to string to handle numeric values from Excel data
            alt_parts.append(str(option_value))

    return "#" + "#".join(alt_parts) if alt_parts else ""


def generate_lifestyle_alt_tag(product_title: str, image_type: str = "Lifestyle") -> str:
    """
    Generate alt tag for lifestyle/hero images.

    Args:
        product_title: Product title
        image_type: Type of image (Hero, Lifestyle, Gallery, etc.)

    Returns:
        Alt tag string

    Examples:
        ("Sherwood Ledgestone", "Hero") -> "Sherwood Ledgestone - Hero"
        ("Sherwood Ledgestone", "Lifestyle") -> "Sherwood Ledgestone - Lifestyle"
    """
    return f"{product_title} - {image_type}"


def clean_and_verify_image_url(url: str, timeout: int = 10) -> Optional[str]:
    """
    Clean image URL and verify it works.

    Tries cleaned URL first, falls back to original if cleaned version fails.

    Args:
        url: Image URL to clean and verify
        timeout: Request timeout in seconds

    Returns:
        Working URL (cleaned or original) or None if both fail
    """
    if not url:
        return None

    # Try cleaned URL first
    cleaned = strip_querystring(url)
    if verify_image_url(cleaned, timeout):
        return cleaned

    # Fallback to original URL
    if verify_image_url(url, timeout):
        return url

    return None
