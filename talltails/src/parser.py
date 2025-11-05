"""
Page parsing for Talltails collector.

Extracts product data from HTML pages with variant-aware gallery handling.
"""

import re
import json
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import text_only


class TalltailsParser:
    """Parses Talltails product pages."""

    def __init__(self, origin: str):
        """
        Initialize parser.

        Args:
            origin: Site origin URL
        """
        self.origin = origin

    @staticmethod
    def _https_no_query(u: str) -> str:
        """Force https and strip query/fragment."""
        try:
            from urllib.parse import urlsplit, urlunsplit
            p = list(urlsplit(u))
            p[0] = "https"
            p[3] = ""
            p[4] = ""
            return urlunsplit(p)
        except Exception:
            return u

    def _extract_gallery_mage_json(self, html: str) -> List[Dict]:
        """Pull the Magento gallery "data" list if present."""
        # 1) <script data-gallery-role="gallery">...</script>
        m = re.search(
            r'<script[^>]*data-gallery-role="gallery"[^>]*>(.*?)</script>',
            html,
            re.I | re.DOTALL,
        )
        if m:
            try:
                blob = (m.group(1) or "").strip()
                j = json.loads(blob)
                if isinstance(j, list):
                    return j
                if isinstance(j, dict) and isinstance(j.get("data"), list):
                    return j["data"]
            except Exception:
                pass

        # 2) <script type="text/x-magento-init"> ... "mage/gallery/gallery": {data:[...]}
        for mm in re.finditer(
            r'<script[^>]*type="text/x-magento-init"[^>]*>(.*?)</script>',
            html,
            re.I | re.DOTALL,
        ):
            blob = (mm.group(1) or "").strip()
            try:
                root = json.loads(blob)
            except Exception:
                continue

            def _find_gallery(node):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if k == "mage/gallery/gallery" and isinstance(v, dict):
                            if isinstance(v.get("data"), list):
                                return v["data"]
                        found = _find_gallery(v)
                        if found is not None:
                            return found
                elif isinstance(node, list):
                    for v in node:
                        found = _find_gallery(v)
                        if found is not None:
                            return found
                return None

            data = _find_gallery(root)
            if isinstance(data, list):
                return data

        return []

    def _gallery_from_items(self, items: List[Dict]) -> List[str]:
        """Convert Magento gallery items list to image URLs."""
        images: List[str] = []
        for it in items or []:
            mtype = (it.get("mediaType") or it.get("type") or "").lower()
            if mtype == "image" or (not mtype and ("img" in (it.get("thumb", "") + it.get("img", "")).lower())):
                src = it.get("full") or it.get("img") or it.get("thumb") or ""
                if src:
                    images.append(self._https_no_query(src))

        # dedupe keep order
        seen = set()
        out = []
        for u in images:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _gallery_from_fotorama_dom(self, html: str) -> List[str]:
        """Parse the Fotorama gallery container only."""
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one('[data-gallery-role="gallery"]')
        if not container:
            return []

        images: List[str] = []

        # Stage frames
        for frame in container.select(".fotorama__stage__frame"):
            img = frame.find("img", class_=re.compile(r"\bfotorama__img\b"))
            if img and img.get("src"):
                images.append(self._https_no_query(img.get("src")))

        # Thumbs
        for nav_img in container.select(".fotorama__nav__frame img"):
            src = nav_img.get("src") or ""
            if src:
                images.append(self._https_no_query(src))

        # dedupe
        seen = set()
        out = []
        for u in images:
            if u and u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _extract_materials_and_care(self, html: str) -> tuple:
        """Extract materials and care instructions from Materials tab."""
        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one("#materials")
        if not root:
            return "", ""

        def _after_h3_with_text(htext: str) -> str:
            for h3 in root.find_all("h3"):
                t = h3.get_text(" ", strip=True).lower()
                if htext.lower() in t:
                    p = h3.find_next_sibling("p")
                    while p and not p.get_text(strip=True):
                        p = p.find_next_sibling("p")
                    if p:
                        return text_only(p.get_text(" ", strip=True))
            return ""

        materials = _after_h3_with_text("material")
        care = _after_h3_with_text("care")
        return materials, care

    def parse_page(
        self,
        html_text: str,
        variant_handler=None,
        variant_query_text: str = "",
        variant_tokens: set = None
    ) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Returns:
            title: Product title
            brand_hint: Brand name
            benefits: List of product benefits
            description: Product description
            gallery_images: List of image URLs (variant-aware)
            model_product: Additional metadata

        Args:
            html_text: HTML content of product page
            variant_handler: VariantHandler instance (optional)
            variant_query_text: Query text for variant matching
            variant_tokens: Token set for variant matching

        Returns:
            Dictionary with extracted product data
        """
        soup = BeautifulSoup(html_text or "", "html.parser")
        variant_tokens = variant_tokens or set()

        # Extract title
        title_el = soup.select_one("h1") or soup.select_one("[data-product-title]")
        title = (title_el.get_text(" ", strip=True) if title_el else "").strip()

        # Extract description (plain text)
        desc_el = soup.select_one(".product.attribute.description .value") or soup.select_one(
            ".product.attribute.description"
        )
        description_html_raw = str(desc_el) if desc_el else ""
        description_text = text_only(description_html_raw)

        # Extract benefits (bullets under .product-info-main)
        bullets: List[str] = []
        for ul in soup.select(".product-info-main ul"):
            for li in ul.select("li"):
                t = li.get_text(" ", strip=True)
                if t:
                    bullets.append(t)
        seen = set()
        benefits = []
        for b in bullets:
            if b not in seen:
                seen.add(b)
                benefits.append({"title": "", "description": b})

        # Extract materials / care
        ingredients_text, directions_for_use = self._extract_materials_and_care(html_text)

        # Gallery extraction (variant-aware if handler provided)
        images: List[str] = []
        chosen_child: str = ""

        if variant_handler:
            # Extract swatch/config
            swatch = variant_handler.extract_swatch_renderer(html_text)
            product_labels = swatch.get("product_labels") or {}
            product_media = swatch.get("product_media") or {}
            style_opt_to_children = swatch.get("style_opt_to_children") or {}
            style_opt_label = swatch.get("style_opt_label") or {}
            style_labels_dom = swatch.get("style_labels_dom") or []

            # Resolve best style label
            chosen_label, _ = variant_handler.fuzzy_style_from_name(
                style_labels_dom, variant_query_text, variant_tokens
            )

            # Resolve to child id
            if chosen_label and style_opt_label and style_opt_to_children:
                best_oid = variant_handler.best_style_option(style_opt_label, chosen_label)
                if best_oid and style_opt_to_children.get(best_oid):
                    chosen_child = style_opt_to_children[best_oid][0]

            if not chosen_child:
                chosen_child = variant_handler.select_variant_child(
                    product_labels, chosen_label, variant_tokens
                )

            # Build gallery (variant-specific if available)
            if chosen_child and product_media.get(str(chosen_child)):
                child_items = product_media[str(chosen_child)]
                images = self._gallery_from_items(child_items)
            else:
                # Fallback: single-variant gallery
                mg_items = self._extract_gallery_mage_json(html_text)
                if mg_items:
                    images = self._gallery_from_items(mg_items)
                else:
                    images = self._gallery_from_fotorama_dom(html_text)
        else:
            # No variant handler: use simple gallery extraction
            mg_items = self._extract_gallery_mage_json(html_text)
            if mg_items:
                images = self._gallery_from_items(mg_items)
            else:
                images = self._gallery_from_fotorama_dom(html_text)

        # dedupe images
        seen_i = set()
        images = [u for u in images if (u and not (u in seen_i or seen_i.add(u)))]

        return {
            "model_product": {
                "ingredients_text": ingredients_text,
                "directions_for_use": directions_for_use,
            },
            "title": title or "",
            "brand_hint": "Tall Tails",
            "benefits": benefits,
            "description": description_text,
            "gallery_images": images,
        }
