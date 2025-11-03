"""
Page parsing for Purinamills collector.

Extracts product data from HTML pages.
"""

import re
import json
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import text_only


class PurinamillsParser:
    """Parses Purinamills product pages."""

    def __init__(self, origin: str):
        """
        Initialize parser.

        Args:
            origin: Site origin URL
        """
        self.origin = origin

    def _clean_url(self, url: str) -> str:
        """Clean and normalize image URL."""
        if not url:
            return ""
        url = url.strip().strip('"').strip("'")
        # Remove query parameters
        qpos = url.find("?")
        if qpos != -1:
            url = url[:qpos]
        # Make absolute
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = f"{self.origin.rstrip('/')}{url}"
        elif not url.startswith("http"):
            url = f"{self.origin.rstrip('/')}/{url.lstrip('/')}"
        return url.replace("http://", "https://")

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Returns:
            title: Product title
            brand_hint: Brand name
            benefits: List of product benefits
            description: Product description
            gallery_images: List of image URLs
            model_product: Parsed modelProduct JSON (or None)
            nutrition_text: Nutrition information (if available)
            directions_for_use: Directions text (if available)

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        soup = BeautifulSoup(html_text or "", "html.parser")

        # Extract title
        title = ""
        title_el = soup.find("h1")
        if title_el:
            title = text_only(title_el.get_text(strip=True))

        # Extract brand (usually first word before ®)
        brand_hint = "Purina"
        if "®" in title:
            brand_hint = title.split("®")[0].strip()

        # Extract description
        description = ""
        desc_el = soup.select_one(".product__description") or soup.select_one(".product-description")
        if desc_el:
            description = text_only(desc_el.get_text(" ", strip=True))

        # Extract benefits (bullet lists)
        benefits: List[Dict[str, str]] = []
        for ul in soup.find_all("ul"):
            # Skip navigation and footer lists
            if any(cls in str(ul.get("class", [])) for cls in ["nav", "menu", "footer"]):
                continue
            for li in ul.find_all("li"):
                benefit_text = text_only(li.get_text(" ", strip=True))
                if benefit_text and len(benefit_text) > 10:  # Filter out short items
                    benefits.append({"title": "", "description": benefit_text})
            if benefits:
                break  # Use first meaningful list

        # Extract gallery images
        gallery_images: List[str] = []
        seen = set()

        # Try to find model product JSON
        model_product = None
        for script in soup.find_all("script"):
            script_text = script.get_text()
            if "modelProduct" in script_text or "__PRODUCT_JSON__" in script_text:
                # Try to extract JSON
                for match in re.finditer(r'({[^{}]*"[^"]*(?:images?|media|gallery)[^"]*"[^{}]*})', script_text):
                    try:
                        potential_json = match.group(1)
                        model_product = json.loads(potential_json)
                        break
                    except:
                        continue

        # Extract images from model product if available
        if model_product and isinstance(model_product, dict):
            for key in ["images", "media", "gallery", "ProductImage", "LifestyleImages"]:
                imgs = model_product.get(key)
                if isinstance(imgs, list):
                    for img in imgs:
                        if isinstance(img, dict):
                            url = img.get("src") or img.get("url") or ""
                        else:
                            url = str(img)
                        if url:
                            clean = self._clean_url(url)
                            if clean and clean not in seen:
                                gallery_images.append(clean)
                                seen.add(clean)
                elif isinstance(imgs, str):
                    clean = self._clean_url(imgs)
                    if clean and clean not in seen:
                        gallery_images.append(clean)
                        seen.add(clean)

        # Extract images from DOM
        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src") or ""
            if src:
                clean = self._clean_url(src)
                # Filter out small icons and logos
                if clean and "product" in clean.lower() and clean not in seen:
                    gallery_images.append(clean)
                    seen.add(clean)

        # Extract nutrition and directions (if available)
        nutrition_text = ""
        directions_for_use = ""

        nutrition_section = soup.find(id=re.compile(r"nutrition", re.I)) or soup.find(
            string=re.compile(r"guaranteed analysis", re.I)
        )
        if nutrition_section:
            parent = nutrition_section.parent if hasattr(nutrition_section, 'parent') else nutrition_section
            if parent:
                nutrition_text = text_only(parent.get_text(" ", strip=True))

        directions_section = soup.find(id=re.compile(r"directions?|feeding", re.I)) or soup.find(
            string=re.compile(r"feeding directions?|directions for use", re.I)
        )
        if directions_section:
            parent = directions_section.parent if hasattr(directions_section, 'parent') else directions_section
            if parent:
                directions_for_use = text_only(parent.get_text(" ", strip=True))

        return {
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "gallery_images": gallery_images,
            "model_product": model_product,
            "nutrition_text": nutrition_text,
            "directions_for_use": directions_for_use,
        }
