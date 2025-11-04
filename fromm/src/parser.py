"""
Page parsing for Fromm Family Foods collector.

Extracts product data from HTML pages.
"""

import re
from typing import Dict, Any, List
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import text_only
image_processor import FrommImageProcessor


class FrommParser:
    """Parses Fromm Family Foods product pages."""

    def __init__(self):
        """Initialize parser."""
        self.image_processor = FrommImageProcessor()

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data:
            - name: Product name
            - description: Product description
            - ingredients: Ingredients list
            - nutrition: Guaranteed analysis + caloric content
            - size_info: Available sizes
            - breadcrumbs: Category breadcrumbs
            - manufacturer_key: Manufacturer identifier
            - mpn: Manufacturer part number (empty)
            - media: List of image URLs
            - upc: Single UPC if only one found
            - key: Product key
            - variants: List of UPC variants if multiple found
        """
        data = {}

        # Product name
        name_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.I | re.DOTALL)
        data["name"] = text_only(name_match.group(1)) if name_match else ""

        # Description (primary lead block, with fallback just after H1)
        desc_html = ""
        desc_match = re.search(
            r'<div class="lead">\s*<p>(.*?)</p>',
            html_text,
            flags=re.I | re.DOTALL
        )
        if desc_match:
            desc_html = desc_match.group(1)
        else:
            desc_match2 = re.search(
                r"</h1>\s*<p[^>]*>(.*?)</p>",
                html_text,
                flags=re.I | re.DOTALL
            )
            desc_html = desc_match2.group(1) if desc_match2 else ""
        data["description"] = text_only(desc_html)

        # Ingredients
        ing_match = re.search(
            r"<h3>Ingredients</h3>(.*?)</div>",
            html_text,
            flags=re.I | re.DOTALL
        )
        ingredients = text_only(ing_match.group(1)) if ing_match else ""
        # Add spacing after commas
        ingredients = re.sub(r",(?=\S)", ", ", ingredients)
        data["ingredients"] = ingredients

        # Nutrition (Guaranteed Analysis + Caloric Content)
        nutrition_parts = []
        ga_match = re.search(
            r"<h3>Guaranteed Analysis</h3>(.*?)</ul>",
            html_text,
            flags=re.I | re.DOTALL
        )
        if ga_match:
            nutrition_parts.append(text_only(ga_match.group(1)))

        cal_match = re.search(
            r"<h3>Caloric Content</h3>(.*?)</section>",
            html_text,
            flags=re.I | re.DOTALL
        )
        if cal_match:
            nutrition_parts.append("Caloric Content: " + text_only(cal_match.group(1)))

        data["nutrition"] = "\n".join(p for p in nutrition_parts if p)

        # Sizes (trim trailing period + collapse whitespace)
        sizes_match = re.search(
            r"<h3>Available Sizes</h3>\s*<p>(.*?)</p>",
            html_text,
            flags=re.I
        )
        if sizes_match:
            sizes = sizes_match.group(1).strip()
            if sizes.endswith("."):
                sizes = sizes[:-1]
            data["size_info"] = re.sub(r"\s+", " ", sizes)
        else:
            data["size_info"] = ""

        # Breadcrumbs (normalize whitespace per crumb)
        crumbs = re.findall(
            r'<p class="breadcrumbs.*?">\s*(.*?)</p>',
            html_text,
            flags=re.I | re.DOTALL
        )
        breadcrumb_list = []
        if crumbs:
            breadcrumb_list = re.findall(r'>([^<]+)</a>', crumbs[0])
        data["breadcrumbs"] = [re.sub(r"\s+", " ", c).strip() for c in breadcrumb_list]

        # Manufacturer info
        data["manufacturer_key"] = "FROMM-FAMILY-FOODS"
        data["mpn"] = ""

        # Images (gallery only)
        data["media"] = self.image_processor.extract_gallery_images(html_text)

        # UPCs (derived from image filenames)
        upcs_found = set()
        for url in data["media"]:
            digits = re.findall(r"(\d{12,13})", url)
            for d in digits:
                # Normalize 13-digit to 12-digit if starts with 0
                if len(d) == 13 and d.startswith("0"):
                    d = d[1:]
                if len(d) == 12:
                    upcs_found.add(d)

        upc_list = sorted(upcs_found)

        # Single UPC vs multiple variants
        if len(upc_list) == 1:
            data["upc"] = upc_list[0]
            data["key"] = f"FROMM-FAMILY-FOODS-{upc_list[0]}"
        else:
            data["upc"] = None
            base_key = (
                f"FROMM-FAMILY-FOODS-{data['name'].upper().replace(' ', '-')}"
                if data.get("name")
                else "FROMM-FAMILY-FOODS-PRODUCT"
            )
            data["key"] = base_key
            data["variants"] = [{"upc": u} for u in upc_list]

        return data
