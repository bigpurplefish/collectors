"""
Page parsing for KONG collector.

Extracts product data from HTML pages.
"""

import re
import html
from typing import Dict, Any, List
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import text_only


class KongParser:
    """Parses KONG Company product pages."""

    def __init__(self, origin: str):
        """
        Initialize parser.

        Args:
            origin: Site origin URL
        """
        self.origin = origin

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Returns:
            title: Product title
            brand_hint: Brand name
            benefits: List of product benefits
            description: Product description
            gallery_images: List of image URLs

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        # Extract title
        title = ""
        m_title = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.DOTALL | re.I)
        if m_title:
            title = text_only(m_title.group(1))

        # Extract description
        description = ""
        m_desc = re.search(r"</h1>\s*<p[^>]*>(.*?)</p>", html_text, re.DOTALL | re.I)
        if m_desc:
            description = text_only(m_desc.group(1))

        # Extract bullet point features (benefits)
        benefits: List[str] = []
        m_ul = re.search(r"</p>\s*<ul>(.*?)</ul>", html_text, re.DOTALL | re.I)
        if m_ul:
            ul_content = m_ul.group(1)
            for m in re.finditer(
                r"<li[^>]*>(.*?)</li>", ul_content, re.DOTALL | re.I
            ):
                text = text_only(m.group(1))
                if text:
                    benefits.append(text)

        # Extract gallery images (all variants)
        gallery: List[str] = []
        seen_ids = set()

        # Look for data-media attributes for variant image sets
        for m in re.finditer(r'data-media="([^"]+)"', html_text, re.DOTALL | re.I):
            data_str = html.unescape(m.group(1))
            # data-media string format: "key1:GUID1;key2:GUID2;..."
            parts = [p.strip() for p in data_str.split(";") if p.strip()]
            for part in parts:
                if ":" in part:
                    guid = part.split(":", 1)[1]
                else:
                    guid = part
                guid = guid.strip()
                if guid and guid not in seen_ids:
                    seen_ids.add(guid)

        # Fallback: parse image URLs in HTML
        if not seen_ids:
            for m in re.finditer(
                r"//cdn\.amplifi\.pattern\.com/([0-9a-f\-]+)_(?:small|medium)",
                html_text,
                re.I,
            ):
                guid = m.group(1)
                if guid and guid not in seen_ids:
                    seen_ids.add(guid)

        # Construct image URLs (use _medium size for better resolution)
        for guid in seen_ids:
            gallery.append(f"https://cdn.amplifi.pattern.com/{guid}_medium")

        return {
            "title": title,
            "brand_hint": "KONG",
            "benefits": benefits,
            "description": description,
            "model_product": None,
            "gallery_images": gallery,
        }
