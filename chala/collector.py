#!/usr/bin/env python3
"""
Chala Handbags Product Collector

Collects product data from https://www.chalahandbags.com.
"""

import os
import re
import json
import html
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

# Site Configuration (embedded from profile)
SITE_CONFIG = {
    "key": "chala",
    "display_name": "Chala Handbags",
    "origin": "https://www.chalahandbags.com",
    "referer": "https://www.chalahandbags.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
    "search": {
        "html_search_path": "/search?q={QUERY}"
    }
}

# strategies/chala.py

from __future__ import annotations
from .base import SiteStrategy
from typing import Optional, Dict, Any, List
import re, html

class ChalaHandbagsStrategy(SiteStrategy):
    @staticmethod
    def _text_only(s: str) -> str:
        """Strip HTML tags and replace <br> with newline; unescape HTML entities."""
        s = re.sub(r'<\s*br\s*/?>', '\n', s, flags=re.I)
        s = re.sub(r'<[^>]+>', '', s)
        return html.unescape(s).strip()

    @staticmethod
    def _deproxy_image_url(src: Optional[str]) -> str:
        """Normalize image URL (ensure HTTPS and remove query parameters)."""
        if not src or not isinstance(src, str):
            return ""
        url = src.strip()
        # If protocol-relative or http, convert to https
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http://"):
            url = "https://" + url[7:]
        # Remove any query parameters for a clean URL
        return url.split("?", 1)[0]

    def _is_gallery_candidate(self, url: str) -> bool:
        """Accept Shopify product images from either the store domain (/cdn/shop/…) or cdn.shopify.com."""
        if not url:
            return False
        u = url.lower()
        return ("/cdn/shop/" in u) or ("cdn.shopify.com" in u)

    def _normalize_img(self, url: str) -> str:
        """
        Force https, expand root-relative (/cdn/shop/...), drop query params,
        strip Shopify size tokens (_320x, _960x_crop_center, _grande, etc.),
        and convert .webp to .jpg for downstream compatibility.
        """
        if not url:
            return ""
        u = url.strip()
        if u.startswith("//"):
            u = "https:" + u
        if u.startswith("http://"):
            u = "https://" + u[7:]
        if u.startswith("/"):                               # (suggestion #1) handle root-relative
            u = (self.origin.rstrip("/") + u)
        # strip query
        u = u.split("?", 1)[0]
        # remove size suffixes before extension (also handle .webp)
        u = re.sub(
            r'_(?:pico|icon|thumb|small|compact|medium|large|grande|\d+x\d+|\d+x)'
            r'(?:_[a-z0-9-]+)*\.(jpe?g|png|gif|webp)$',
            r'.\1',
            u,
            flags=re.I,
        )
        # Convert webp → jpg (best-effort; Shopify usually has a jpg of the same key)
        u = re.sub(r'\.webp$', '.jpg', u, flags=re.I)
        return u

    def _strip_shopify_size(self, url: str) -> str:
        """
        Convert Shopify CDN image URL to 'original' full size:
        - removes size tokens like _pico,_icon,_thumb,_small,_compact,_medium,_large,_grande,_xNNNxMMM
        - keeps the original extension (includes webp)
        - strips query params (?v=...)
        """
        if not url:
            return ""
        base = url.split("?", 1)[0]
        base = re.sub(
            r'_(?:pico|icon|thumb|small|compact|medium|large|grande|[0-9]+x[0-9]+)\.(jpg|jpeg|png|gif|webp)$',
            r'.\1', base, flags=re.I
        )
        return base

    def _fullsize_from_srcset(self, srcset: str) -> str:
        """
        Given a srcset string, pick the largest candidate and normalize to full size.
        """
        try:
            parts = [p.strip() for p in srcset.split(",") if p.strip()]
            pairs: List[tuple[str, int]] = []
            for p in parts:
                seg = p.split()
                url = seg[0]
                w = 0
                if len(seg) > 1 and seg[1].endswith("w"):
                    try:
                        w = int(re.sub(r'\D', '', seg[1]))
                    except:
                        w = 0
                pairs.append((url, w))
            pairs.sort(key=lambda t: t[1], reverse=True)
            if pairs:
                # normalize handles size stripping, root-relative and webp→jpg
                candidate = self._normalize_img(pairs[0][0])
                return candidate if self._is_gallery_candidate(candidate) else ""
        except:
            pass
        return ""

    def find_product_page_url_for_upc(self, upc: str, http_get, timeout: int, log) -> str:
        """Locate the product page URL for the given UPC by searching the site or using known patterns."""
        upc_str = re.sub(r'\D', '', str(upc or ""))  # clean UPC to digits only
        if not upc_str:
            return ""
        # Check for any explicit overrides in profile
        overrides = ((self.profile.get("search") or {}).get("upc_overrides") or {})
        if upc_str in overrides:
            return overrides[upc_str]

        # Attempt site search by UPC (if site search supports it)
        search_path = (self.profile.get("search") or {}).get("html_search_path")
        if search_path and self.origin:
            search_url = f"{self.origin}{search_path.format(QUERY=upc_str)}"
            log(f"Site search for UPC: {search_url}")
            try:
                r = http_get(search_url, timeout=timeout)
            except Exception as e:
                r = None
            if r and r.status_code == 200:
                # Look for a product link in search results
                m = re.search(r'href="(/products/[^"<>]+)"', r.text, flags=re.I)
                if m:
                    return m.group(1)

        # Fallback partial search by last digits
        partial_query = upc_str[-5:] if len(upc_str) >= 5 else upc_str
        if search_path and self.origin and partial_query:
            search_url2 = f"{self.origin}{search_path.format(QUERY=partial_query)}"
            log(f"Site search for partial UPC: {search_url2}")
            try:
                r2 = http_get(search_url2, timeout=timeout)
            except Exception as e:
                r2 = None
            if r2 and r2.status_code == 200:
                m2 = re.search(r'href="(/products/[^"<>]+)"', r2.text, flags=re.I)
                if m2:
                    return m2.group(1)
        return ""

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Extract full product info from a Chala Handbags product page.
        Returns: {title, brand_hint, benefits[], description, gallery_images[]}
        NOTE: Gallery is STRICT: only full-size product images from Product JSON-LD,
              data-full="…" gallery attributes, and og:image meta — no page-wide <img> sweep.
        """
        # ---------------------------
        # TITLE
        # ---------------------------
        m_title = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, flags=re.I | re.S)
        title = self._text_only(m_title.group(1)) if m_title else ""
        brand_hint = "Chala"

        # ---------------------------
        # DESCRIPTION + BULLETS
        # ---------------------------
        desc_segment = ""
        m_block = re.search(
            r'(<div[^>]+class="[^"]*(product[^"]*description|description[^"]*product)[^"]*"[^>]*>.*?</div>)',
            html_text, flags=re.I | re.S
        )
        if m_block:
            desc_segment = m_block.group(1)
        else:
            idx_start = html_text.find("MSRP:")
            idx_end = html_text.find("Share this")
            if idx_start != -1 and idx_end != -1:
                desc_segment = html_text[idx_start:idx_end]
            elif idx_start != -1:
                desc_segment = html_text[idx_start:]

        full_text = self._text_only(desc_segment)
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
        lines = [ln for ln in lines if not re.match(r'^(Default Title\b|MSRP\b|Price\b)', ln, flags=re.I)]

        benefits: List[str] = []
        details: List[str] = []
        for ln in lines:
            if re.match(r'^(Materials?:|Color:|Approx(?:\.|) Measurements?:|Strap|Designed in|Made in|Colors may|Lining patterns)',
                        ln, flags=re.I):
                details.append(ln)
            else:
                if ln not in benefits:
                    benefits.append(ln)

        description = " ".join(details).strip()

        # ---------------------------
        # GALLERY — FULL-SIZE ONLY (STRICT SOURCES)
        # ---------------------------
        gallery: List[str] = []
        seen: set[str] = set()

        def _try_add(u: Optional[str]) -> None:
            if not u:
                return
            u2 = self._normalize_img(str(u))
            if self._is_gallery_candidate(u2) and u2 not in seen:
                seen.add(u2)
                gallery.append(u2)

        # 1) Product JSON-LD (@type: Product) images only
        for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                             html_text, flags=re.I | re.S):
            block = m.group(1).strip()
            if not block:
                continue
            try:
                import json as _json
                data = _json.loads(block)
            except Exception:
                continue

            def _extract_ld(obj):
                if isinstance(obj, dict):
                    if obj.get("@type") == "Product":
                        imgs = obj.get("image")
                        if isinstance(imgs, str):
                            _try_add(imgs)
                        elif isinstance(imgs, list):
                            for u in imgs:
                                _try_add(u)
                    for v in obj.values():  # recurse
                        _extract_ld(v)
                elif isinstance(obj, list):
                    for it in obj:
                        _extract_ld(it)

            _extract_ld(data)

        # 2) Gallery markup: data-full="…" (theme sets full-size URLs here)
        for m in re.finditer(r'\bdata-full="([^"]+)"', html_text, flags=re.I):
            _try_add(m.group(1))

        # 3) Primary OpenGraph image as a final hint (often the hero image)
        #    (suggestion #3) accept property="og:image" or name="og:image"
        for m in re.finditer(
            r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            html_text, flags=re.I
        ):
            _try_add(m.group(1))

        return {
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "gallery_images": gallery
        }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Chala Handbags Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
