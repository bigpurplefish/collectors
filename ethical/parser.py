"""
Page parsing for Ethical Products collector.

Extracts product data from HTML pages.
"""

import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import text_only, deduplicate_urls
from .image_processor import EthicalImageProcessor


class EthicalParser:
    """Parses Ethical Products pages."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize parser.

        Args:
            config: Site configuration
        """
        self.origin = config.get("origin", "")
        parsing_config = config.get("parsing", {})
        self.desc_selectors = parsing_config.get("desc_selectors", [])

        gallery_selectors = parsing_config.get("gallery_selectors", {})
        self.carousel_selector = gallery_selectors.get(
            "carousel_images",
            "div.elastislide-carousel ul.elastislide-list li img[data-largeimg]"
        )
        self.carousel_alternates = [
            "#demo2carousel img[data-largeimg]",
            ".elastislide-carousel .elastislide-list img[data-largeimg]"
        ]

        self.image_processor = EthicalImageProcessor(self.origin)

    def parse_page(self, html: str) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Args:
            html: HTML content of product page

        Returns:
            Dictionary with extracted product data:
            - title: Product title
            - brand_hint: Brand name ("Ethical Products")
            - description: Product description
            - gallery_images: List of image URLs
            - gallery_summary: Summary of image extraction
            - log_lines: Processing log entries
            - manufacturer: Complete manufacturer data block
        """
        soup = BeautifulSoup(html or "", "html.parser")

        # Extract title
        title = self._extract_title(html)

        # Extract description
        description = self._extract_description(html)

        # Extract gallery images
        hires_map = self.image_processor.extract_hires_map(soup)
        images = []

        # Try Elastislide carousel first
        if soup.select_one("div.elastislide-carousel"):
            carousel_images = self.image_processor.extract_carousel_images(
                soup,
                [self.carousel_selector] + self.carousel_alternates
            )
            images.extend(carousel_images)

        # Fallback methods if carousel is empty
        if not images:
            fallback_images = self.image_processor.extract_fallback_images(soup, html)
            images.extend(fallback_images)

        # Normalize images to max size
        images = deduplicate_urls([
            self.image_processor.upsize_wp_image(url, hires_map)
            for url in images
        ])

        gallery_summary = f"found {len(images)} images"
        if images:
            gallery_summary += f"; first={images[0]}"

        return {
            "title": title or "",
            "brand_hint": "Ethical Products",
            "description": description or "",
            "gallery_images": images,
            "gallery_summary": gallery_summary,
            "log_lines": [f"[ethical] Gallery: {gallery_summary}"],
            "manufacturer": {
                "site_key": "ethical",
                "brand": "Ethical Products",
                "name": title or "",
                "product_name": title or "",
                "description": description or "",
                "images": images,
                "product_url": "",
                "_gallery_summary": gallery_summary,
            },
        }

    def _extract_title(self, html: str) -> str:
        """Extract product title from HTML."""
        patterns = [
            r'<div[^>]+class="summary[^"]*"[^>]*>.*?<h4[^>]*>(.*?)</h4>',
            r'<h1[^>]*class="product_title[^"]*"[^>]*>(.*?)</h1>',
            r'<h1[^>]*class="entry-title[^"]*"[^>]*>(.*?)</h1>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.I | re.DOTALL)
            if match:
                return text_only(match.group(1))

        match = re.search(r'<meta[^>]+itemprop="name"[^>]+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1).strip()

        match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
        return match.group(1).strip() if match else ""

    def _extract_description(self, html: str) -> str:
        """Extract product description from HTML."""
        patterns = [
            r'<div[^>]+class="woocommerce-product-details__short-description"[^>]*>(.*?)</div>',
            r'<div[^>]+class="description"[^>]*>.*?<p[^>]*>(.*?)</p>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.I | re.DOTALL)
            if match:
                return text_only(match.group(1))

        match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, re.I)
        return match.group(1).strip() if match else ""
