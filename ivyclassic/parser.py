"""
Page parsing for Ivyclassic collector.

Extracts product data from HTML pages.
"""

import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup


class IvyclassicParser:
    """Parses Ivyclassic product pages."""

    def __init__(self, origin: str):
        """
        Initialize parser.

        Args:
            origin: Site origin URL
        """
        self.origin = origin

    @staticmethod
    def _clean_image_url(src: str, origin: str) -> str:
        """
        Clean and normalize image URL.

        Args:
            src: Image source URL
            origin: Site origin URL

        Returns:
            Cleaned image URL
        """
        if not src:
            return ""

        s = src.strip()
        if s.startswith("//"):
            s = "https:" + s
        elif s.startswith("/"):
            s = origin.rstrip("/") + s
        elif not s.startswith("http"):
            s = origin.rstrip("/") + "/" + s.lstrip("/")

        # Handle GetImage.ashx proxy
        if "GetImage.ashx" in s and "image=" in s:
            image_qs = s.split("image=", 1)[1]
            image_path = image_qs.split("&", 1)[0] if "&" in s else image_qs
            image_path = image_path.replace("+", " ").replace(" ", "%20")
            if not image_path.startswith("http"):
                if not image_path.startswith("/"):
                    image_path = "/" + image_path
                s = origin.rstrip("/") + image_path
            else:
                s = image_path
        else:
            s = s.split("?", 1)[0].split("#", 1)[0]

        return s.replace("http://", "https://")

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
        soup = BeautifulSoup(html_text or "", "html.parser")

        # Extract title
        h = soup.find(["h2", "h1"])
        title = (h.get_text(strip=True) if h else "") or ""

        # Extract benefits from "Features" tab only
        features_container = None

        # Path A: find the Features tab button and follow its data-bs-target
        btn = None
        for b in soup.find_all("button"):
            txt = (b.get_text() or "").strip().lower()
            if txt == "features":
                btn = b
                break
        if btn:
            target = btn.get("data-bs-target") or ""
            if target.startswith("#"):
                pane = soup.select_one(target)
                if pane:
                    features_container = pane

        # Path B (fallback): match a common id pattern
        if not features_container:
            features_container = soup.find("div", id=re.compile(r"item_swiftrizzo_tabs_\d+_1"))

        # Extract list items within the features pane
        benefits: List[Dict[str, str]] = []
        if features_container:
            ul = features_container.find("ul")
            if ul:
                for li in ul.find_all("li"):
                    text = li.get_text(separator=" ", strip=True)
                    if not text:
                        continue
                    # Skip spec table rows
                    if re.search(
                        r"^\s*(Product No\.|UPC Code|Box Qty|Case Qty|Weight)\b",
                        text,
                        re.I
                    ):
                        continue
                    benefits.append({"title": "", "description": text})

        # Extract gallery images
        gallery_images: List[str] = []
        for img in soup.find_all("img"):
            src = (img.get("src") or "").strip()
            if not src:
                continue

            # Skip status icons
            alt = (img.get("alt") or "").strip().lower()
            if alt in {"in stock", "on backorder"}:
                continue

            # Skip small images
            w = img.get("width")
            if (isinstance(w, str) and w.isdigit() and int(w) <= 200) or (
                isinstance(w, int) and w <= 200
            ):
                continue

            full = self._clean_image_url(src, self.origin)
            if not full:
                continue

            # Only include product images
            if ("Single%20Item%20Images" not in full) and ("Shared%20Images" not in full):
                continue

            if full not in gallery_images:
                gallery_images.append(full)

        return {
            "title": title,
            "description": "",
            "benefits": benefits,
            "gallery_images": gallery_images,
            "brand_hint": "Ivy Classic",
            "model_product": None,
        }
