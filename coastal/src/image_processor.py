"""
Image processing for Coastal Pet collector.

Handles Coastal-specific image URL normalization and extraction.
"""

import re
from typing import Optional, List
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import normalize_to_https, strip_query_params, deduplicate_urls


def deproxy_coastal_image(src: Optional[str]) -> str:
    """
    Normalize Coastal Pet image URLs.

    Handles:
    - /remote.axd/ proxy paths
    - Salsify CDN URLs
    - HTTP to HTTPS conversion
    - Query parameter stripping

    Args:
        src: Raw image URL

    Returns:
        Normalized image URL
    """
    if not src or not isinstance(src, str):
        return ""

    s = src.strip()

    # Remove proxy path
    if s.startswith("/remote.axd/"):
        s = s[len("/remote.axd/"):]

    # Handle Salsify CDN
    if s.startswith("images.salsify.com/"):
        s = "https://" + s

    # Convert to HTTPS
    if s.startswith("http://"):
        s = "https://" + s[len("http://"):]

    # Strip query params
    return strip_query_params(s)


def extract_gallery_from_model_product(model_product: dict, origin: str) -> List[str]:
    """
    Extract gallery images from modelProduct JSON.

    Args:
        model_product: Parsed modelProduct JavaScript object
        origin: Site origin URL

    Returns:
        List of normalized, deduplicated image URLs
    """
    gallery = []
    swatch_urls = set()

    def add_swatch(url: Optional[str]):
        """Add URL to swatch set (to exclude from gallery)."""
        if not url:
            return
        normalized = deproxy_coastal_image(url)
        if normalized:
            swatch_urls.add(normalized)

    def add_image(url: Optional[str]):
        """Add URL to gallery if not a swatch."""
        if not url:
            return
        normalized = deproxy_coastal_image(url)
        if normalized and normalized not in swatch_urls:
            gallery.append(normalized)

    def add_list(nodes):
        """Add images from a list of nodes."""
        if isinstance(nodes, list):
            for item in nodes:
                if isinstance(item, dict):
                    add_image(item.get("salsify_url"))
                elif isinstance(item, str):
                    add_image(item)

    def harvest_gallery(node: Optional[dict]):
        """Extract all gallery images from a node."""
        if not isinstance(node, dict):
            return
        # Main product image
        product_img = node.get("ProductImage")
        if isinstance(product_img, dict):
            add_image(product_img.get("salsify_url"))
        # Additional image sets
        add_list(node.get("LifestyleImages"))
        add_list(node.get("MultiAngleImages"))

    # First, collect swatch images to exclude from gallery
    if isinstance(model_product.get("SwatchAsset"), dict):
        add_swatch(model_product["SwatchAsset"].get("salsify_url"))

    for child in (model_product.get("ChildProducts") or []):
        swatch = child.get("SwatchAsset")
        if isinstance(swatch, dict):
            add_swatch(swatch.get("salsify_url"))

    # Then, collect gallery images
    harvest_gallery(model_product)

    return deduplicate_urls(gallery)


def extract_dom_gallery_fallback(html_text: str, origin: str) -> List[str]:
    """
    Fallback gallery extraction from DOM elements.

    Searches for product image elements in the HTML when
    modelProduct data is unavailable or incomplete.

    Args:
        html_text: HTML content
        origin: Site origin URL

    Returns:
        List of normalized image URLs
    """
    urls = []

    def add_url(url: Optional[str]):
        """Add URL to collection."""
        if not url:
            return
        normalized = deproxy_coastal_image(url)
        if normalized:
            urls.append(normalized)

    # Extract image container blocks
    blocks = []
    for match in re.finditer(
        r'<div[^>]+class="[^"]*product-details__preview-images[^"]*"[^>]*>(.*?)</div>',
        html_text,
        re.I | re.DOTALL
    ):
        blocks.append(match.group(1))

    for match in re.finditer(
        r'<div[^>]+class="[^"]*product-details__product-image[^"]*"[^>]*>(.*?)</div>',
        html_text,
        re.I | re.DOTALL
    ):
        blocks.append(match.group(1))

    # Extract image URLs from blocks
    for block in blocks:
        for tag in re.finditer(r'<img[^>]*>', block, re.I):
            img_tag = tag.group(0)

            # Try src attribute
            m_src = re.search(r'\bsrc="([^"]+)"', img_tag, re.I)
            if m_src:
                add_url(m_src.group(1))

            # Try data-src attribute
            m_dsrc = re.search(r'\bdata-src="([^"]+)"', img_tag, re.I)
            if m_dsrc:
                add_url(m_dsrc.group(1))

            # Try srcset (pick largest)
            m_srcset = re.search(r'\bsrcset="([^"]+)"', img_tag, re.I)
            if m_srcset:
                parts = [p.strip() for p in m_srcset.group(1).split(",") if p.strip()]
                if parts:
                    # Get last entry (usually largest)
                    add_url(parts[-1].split()[0])

    return deduplicate_urls(urls)
