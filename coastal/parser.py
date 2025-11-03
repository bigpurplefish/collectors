"""
Page parsing for Coastal Pet collector.

Extracts product data from HTML pages.
"""

import re
from typing import Dict, Any, List
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import text_only, extract_json_from_script
from .image_processor import (
    extract_gallery_from_model_product,
    extract_dom_gallery_fallback
)


class CoastalParser:
    """Parses Coastal Pet product pages."""

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
            model_product: Parsed modelProduct JSON (or None)
            gallery_images: List of image URLs

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        # Extract modelProduct JSON
        model_product = extract_json_from_script(html_text, "modelProduct")

        # Extract title
        title_match = re.search(
            r'<h4[^>]*class="[^"]*product-details__product-name[^"]*"[^>]*>(.*?)</h4>',
            html_text,
            re.DOTALL | re.I
        )
        title = text_only(title_match.group(1)) if title_match else ""

        # Extract brand
        brand_hint = ""
        if model_product and isinstance(model_product.get("Brand"), str):
            brand_hint = text_only(model_product["Brand"])
        else:
            brand_match = re.search(
                r'/products/search/\?[^"]*brand=([^"&]+)"[^>]*>(.*?)</a>',
                html_text,
                re.DOTALL | re.I
            )
            if brand_match:
                brand_hint = text_only(brand_match.group(2))

        # Extract benefits (key bullet points)
        benefits = []
        for match in re.finditer(
            r'<li[^>]*class="[^"]*key-benefits[^"]*"[^>]*>(.*?)</li>',
            html_text,
            re.DOTALL | re.I
        ):
            benefit = text_only(match.group(1))
            if benefit and benefit not in benefits:
                benefits.append(benefit)

        # Extract description
        desc_match = re.search(
            r'<h3[^>]*>\s*Description\s*</h3>\s*<p[^>]*>(.*?)</p>',
            html_text,
            re.DOTALL | re.I
        )
        if not desc_match:
            desc_match = re.search(
                r'<div[^>]+id="description"[^>]*>.*?<p[^>]*>(.*?)</p>',
                html_text,
                re.DOTALL | re.I
            )
        description = text_only(desc_match.group(1)) if desc_match else ""

        # Extract gallery images
        gallery = []
        if model_product:
            gallery = extract_gallery_from_model_product(model_product, self.origin)

        # Fallback to DOM extraction if gallery is thin
        if len(gallery) < 2:
            dom_urls = extract_dom_gallery_fallback(html_text, self.origin)
            if dom_urls:
                seen = set(gallery)
                for url in dom_urls:
                    if url and url not in seen:
                        gallery.append(url)
                        seen.add(url)

        return {
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "model_product": model_product,
            "gallery_images": gallery
        }
