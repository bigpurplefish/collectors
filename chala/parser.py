"""
Page parsing for Chala Handbags collector.

Extracts product data from Shopify product pages.
"""

import re
import json as _json
from typing import Dict, Any, List, Optional
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import text_only
from .image_processor import ChalaImageProcessor


class ChalaParser:
    """Parses Chala Handbags product pages."""

    def __init__(self, origin: str):
        """
        Initialize parser.

        Args:
            origin: Site origin URL
        """
        self.origin = origin
        self.image_processor = ChalaImageProcessor(origin)

    def _extract_json_ld_images(self, html_text: str) -> List[str]:
        """
        Extract product images from JSON-LD structured data.

        Args:
            html_text: HTML content

        Returns:
            List of image URLs from Product JSON-LD
        """
        images = []

        for match in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_text,
            flags=re.I | re.DOTALL
        ):
            block = match.group(1).strip()
            if not block:
                continue

            try:
                data = _json.loads(block)
            except Exception:
                continue

            def extract_images(obj):
                """Recursively extract images from JSON-LD."""
                if isinstance(obj, dict):
                    if obj.get("@type") == "Product":
                        imgs = obj.get("image")
                        if isinstance(imgs, str):
                            images.append(imgs)
                        elif isinstance(imgs, list):
                            images.extend(u for u in imgs if isinstance(u, str))
                    # Recurse into nested objects
                    for value in obj.values():
                        extract_images(value)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_images(item)

            extract_images(data)

        return images

    def _extract_data_full_images(self, html_text: str) -> List[str]:
        """
        Extract gallery images from data-full attributes.

        Args:
            html_text: HTML content

        Returns:
            List of image URLs from data-full attributes
        """
        images = []
        for match in re.finditer(r'\bdata-full="([^"]+)"', html_text, flags=re.I):
            images.append(match.group(1))
        return images

    def _extract_og_image(self, html_text: str) -> Optional[str]:
        """
        Extract OpenGraph image.

        Args:
            html_text: HTML content

        Returns:
            OG image URL or None
        """
        match = re.search(
            r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            html_text,
            flags=re.I
        )
        return match.group(1) if match else None

    def _extract_description_and_benefits(self, html_text: str) -> tuple[str, List[str]]:
        """
        Extract description and benefits from product details.

        Args:
            html_text: HTML content

        Returns:
            Tuple of (description, benefits)
        """
        desc_segment = ""

        # Try to find product description block
        match = re.search(
            r'(<div[^>]+class="[^"]*(product[^"]*description|description[^"]*product)[^"]*"[^>]*>.*?</div>)',
            html_text,
            flags=re.I | re.DOTALL
        )

        if match:
            desc_segment = match.group(1)
        else:
            # Fallback: look between known markers
            idx_start = html_text.find("MSRP:")
            idx_end = html_text.find("Share this")
            if idx_start != -1 and idx_end != -1:
                desc_segment = html_text[idx_start:idx_end]
            elif idx_start != -1:
                desc_segment = html_text[idx_start:]

        # Extract text and split into lines
        full_text = text_only(desc_segment)
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

        # Filter out noise lines
        lines = [
            ln for ln in lines
            if not re.match(r'^(Default Title\b|MSRP\b|Price\b)', ln, flags=re.I)
        ]

        # Separate details (material, color, etc.) from benefits
        benefits = []
        details = []

        for line in lines:
            if re.match(
                r'^(Materials?:|Color:|Approx(?:\.|) Measurements?:|Strap|'
                r'Designed in|Made in|Colors may|Lining patterns)',
                line,
                flags=re.I
            ):
                details.append(line)
            else:
                if line not in benefits:
                    benefits.append(line)

        description = " ".join(details).strip()

        return description, benefits

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data:
            - title: Product title
            - brand_hint: Brand name ("Chala")
            - benefits: List of product features
            - description: Product description (materials, measurements, etc.)
            - gallery_images: List of normalized image URLs
        """
        # Extract title
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, flags=re.I | re.DOTALL)
        title = text_only(title_match.group(1)) if title_match else ""

        # Brand is always Chala
        brand_hint = "Chala"

        # Extract description and benefits
        description, benefits = self._extract_description_and_benefits(html_text)

        # Extract gallery images from multiple sources
        json_ld_images = self._extract_json_ld_images(html_text)
        data_full_images = self._extract_data_full_images(html_text)
        og_image = self._extract_og_image(html_text)

        gallery = self.image_processor.extract_gallery(
            json_ld_images,
            data_full_images,
            og_image
        )

        return {
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "gallery_images": gallery
        }
