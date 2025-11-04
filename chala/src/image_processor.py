"""
Image processing for Chala Handbags collector.

Handles Shopify-specific image URL normalization.
"""

import re
from typing import Optional, List, Set
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import (
    normalize_image_url,
    strip_shopify_size_suffix,
    convert_webp_to_jpg,
    deduplicate_urls
)


class ChalaImageProcessor:
    """Handles Chala Handbags (Shopify) image processing."""

    def __init__(self, origin: str):
        """
        Initialize image processor.

        Args:
            origin: Site origin URL
        """
        self.origin = origin

    def is_gallery_candidate(self, url: str) -> bool:
        """
        Check if URL is a valid gallery image.

        Accepts Shopify product images from either the store domain
        (/cdn/shop/…) or cdn.shopify.com.

        Args:
            url: Image URL to check

        Returns:
            True if URL is a valid gallery candidate
        """
        if not url:
            return False
        u = url.lower()
        return ("/cdn/shop/" in u) or ("cdn.shopify.com" in u)

    def normalize_image(self, url: str) -> str:
        """
        Comprehensive Shopify image normalization.

        - Forces HTTPS
        - Expands root-relative URLs
        - Drops query params
        - Strips Shopify size tokens (_320x, _960x_crop_center, _grande, etc.)
        - Converts .webp to .jpg for compatibility

        Args:
            url: Raw image URL

        Returns:
            Normalized image URL
        """
        return normalize_image_url(
            url,
            base_url=self.origin,
            strip_size=True,
            convert_webp=True
        )

    def extract_from_srcset(self, srcset: str) -> str:
        """
        Extract largest image from srcset and normalize.

        Args:
            srcset: HTML srcset attribute value

        Returns:
            Normalized URL of largest image or empty string
        """
        try:
            parts = [p.strip() for p in srcset.split(",") if p.strip()]
            pairs = []

            for part in parts:
                segments = part.split()
                url = segments[0]
                width = 0

                if len(segments) > 1 and segments[1].endswith("w"):
                    try:
                        width = int(re.sub(r'\D', '', segments[1]))
                    except ValueError:
                        width = 0

                pairs.append((url, width))

            # Sort by width descending
            pairs.sort(key=lambda t: t[1], reverse=True)

            if pairs:
                candidate = self.normalize_image(pairs[0][0])
                return candidate if self.is_gallery_candidate(candidate) else ""

        except Exception:
            pass

        return ""

    def extract_gallery(
        self,
        json_ld_images: List[str],
        data_full_attrs: List[str],
        og_image: Optional[str]
    ) -> List[str]:
        """
        Extract gallery images from multiple sources.

        Combines images from:
        1. Product JSON-LD (@type: Product) images
        2. Gallery markup (data-full attributes)
        3. OpenGraph image (as fallback)

        Args:
            json_ld_images: Images from Product JSON-LD
            data_full_attrs: Images from data-full attributes
            og_image: OpenGraph image URL

        Returns:
            List of normalized, deduplicated gallery images
        """
        gallery = []
        seen: Set[str] = set()

        def try_add(url: Optional[str]) -> None:
            """Add URL to gallery if valid and not duplicate."""
            if not url:
                return
            normalized = self.normalize_image(str(url))
            if self.is_gallery_candidate(normalized) and normalized not in seen:
                seen.add(normalized)
                gallery.append(normalized)

        # Add JSON-LD images
        for url in json_ld_images:
            try_add(url)

        # Add data-full images
        for url in data_full_attrs:
            try_add(url)

        # Add OG image as fallback
        if og_image:
            try_add(og_image)

        return gallery
