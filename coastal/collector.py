#!/usr/bin/env python3
"""
Coastal Pet Product Collector

Collects product data from https://www.coastalpet.com.
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
    "key": "coastal",
    "display_name": "Coastal Pet",
    "origin": "https://www.coastalpet.com",
    "referer": "https://www.coastalpet.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
    "bv": {
        "client": "Coastal",
        "bfd_token": "25877,main_site,en_US",
        "api_base_template": "https://apps.bazaarvoice.com/bfd/v1/clients/{client}/api-products/cv2/resources/data/products.json",
        "common_params": {
            "apiVersion": "5.4",
            "locale": "en_US",
            "allowMissing": "true"
        }
    },
    "search": {
        "html_search_path": "/products/search/?q={QUERY}",
        "autocomplete_path": "/product/searchconnection/autocompleteandsuggest?fuzzy=true&term={QUERY}",
        "upc_overrides": {
            "076484093722": "https://www.coastalpet.com/products/detail?id=TPC03",
            "076484362064": "https://www.coastalpet.com/products/detail?id=K9L02",
            "076484362088": "https://www.coastalpet.com/products/detail?id=K9L02"
        }
    }
}

# strategies/coastal.py
from __future__ import annotations
from .base import SiteStrategy
from typing import Optional, Dict, Any, List
import re, json, html

class CoastalPetStrategy(SiteStrategy):
    @staticmethod
    def _text_only(s: str) -> str:
        s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        return html.unescape(s).strip()

    @staticmethod
    def _deproxy_image_url(src: Optional[str]) -> str:
        if not src or not isinstance(src, str):
            return ""
        s = src.strip()
        if s.startswith("/remote.axd/"):
            s = s[len("/remote.axd/"):]
        if s.startswith("images.salsify.com/"):
            s = "https://" + s
        if s.startswith("http://"):
            s = "https://" + s[7:]
        return s.split("?", 1)[0]

    @staticmethod
    def _json_from_model_product(html_text: str) -> Optional[Dict[str, Any]]:
        m = re.search(r"var\s+modelProduct\s*=\s*(\{.*?\});", html_text, re.DOTALL)
        if not m:
            return None
        blob = html.unescape(m.group(1)).rstrip(";").replace("http://", "https://")
        try:
            return json.loads(blob)
        except Exception:
            return None

    def find_product_page_url_for_upc(self, upc: str, http_get, timeout: int, log) -> str:
        clean = re.sub(r"\D", "", str(upc or ""))
        overrides = ((self.profile.get("search") or {}).get("upc_overrides") or {})
        if clean and clean in overrides:
            return overrides[clean]

        html_path = ((self.profile.get("search") or {}).get("html_search_path") or "")
        if html_path and self.origin:
            url = f"{self.origin}{html_path.format(QUERY=clean)}"
            log(f"Site search (HTML): {url}")
            r = http_get(url, timeout=timeout)
            if r.status_code == 200:
                m = re.search(r'href="(/products/detail/\?id=[^"<>]+)"', r.text, flags=re.I)
                if m:
                    return m.group(1)

        auto_path = ((self.profile.get("search") or {}).get("autocomplete_path") or "")
        if auto_path and self.origin:
            url2 = f"{self.origin}{auto_path.format(QUERY=clean)}"
            log(f"Site search (autocomplete): {url2}")
            r2 = http_get(url2, timeout=timeout)
            if r2.status_code == 200:
                m2 = re.search(r'/products/detail/\?id=[A-Za-z0-9]+', r2.text)
                if m2:
                    return m2.group(0)
        return ""

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        mp = self._json_from_model_product(html_text)

        # Title
        m_title = re.search(
            r'<h4[^>]*class="[^"]*product-details__product-name[^"]*"[^>]*>(.*?)</h4>',
            html_text, re.DOTALL | re.I
        )
        title = self._text_only(m_title.group(1)) if m_title else ""

        # Brand
        brand_hint = ""
        if mp and isinstance(mp.get("Brand"), str):
            brand_hint = self._text_only(mp["Brand"])
        else:
            m_brand = re.search(
                r'/products/search/\?[^"]*brand=([^"&]+)"[^>]*>(.*?)</a>',
                html_text, re.DOTALL | re.I
            )
            if m_brand:
                brand_hint = self._text_only(m_brand.group(2))

        # Benefits
        benefits: List[str] = []
        for m in re.finditer(
            r'<li[^>]*class="[^"]*key-benefits[^"]*"[^>]*>(.*?)</li>',
            html_text, re.DOTALL | re.I
        ):
            v = self._text_only(m.group(1))
            if v and v not in benefits:
                benefits.append(v)

        # Description
        m_desc = re.search(r'<h3[^>]*>\s*Description\s*</h3>\s*<p[^>]*>(.*?)</p>',
                           html_text, re.DOTALL | re.I)
        if not m_desc:
            m_desc = re.search(r'<div[^>]+id="description"[^>]*>.*?<p[^>]*>(.*?)</p>',
                               html_text, re.DOTALL | re.I)
        description = self._text_only(m_desc.group(1)) if m_desc else ""

        # Gallery from modelProduct (parent-level; UPC pin-down is done in main app)
        gallery: List[str] = []
        if mp:
            swatch_urls = set()

            def add_swatch(u: Optional[str]):
                if not u: return
                u2 = self._deproxy_image_url(u)
                if u2: swatch_urls.add(u2)

            if isinstance(mp.get("SwatchAsset"), dict):
                add_swatch(mp["SwatchAsset"].get("salsify_url"))
            for ch in (mp.get("ChildProducts") or []):
                sw = ch.get("SwatchAsset")
                if isinstance(sw, dict):
                    add_swatch(sw.get("salsify_url"))

            def add(u: Optional[str]):
                if not u: return
                u2 = self._deproxy_image_url(u)
                if u2 and u2 not in swatch_urls:
                    gallery.append(u2)

            def add_list(nodes):
                if isinstance(nodes, list):
                    for it in nodes:
                        if isinstance(it, dict):
                            add(it.get("salsify_url"))
                        elif isinstance(it, str):
                            add(it)

            def harvest_gallery(node: Optional[Dict[str, Any]]):
                if not isinstance(node, dict): return
                add((node.get("ProductImage") or {}).get("salsify_url"))
                add_list(node.get("LifestyleImages"))
                add_list(node.get("MultiAngleImages"))

            harvest_gallery(mp)
            gallery = list(dict.fromkeys([g for g in gallery if g]))

        # Retailer fallback if thin
        if len(gallery) < 2:
            dom_urls = self.dom_gallery_fallback(html_text)
            if dom_urls:
                seen = set(gallery)
                for u in dom_urls:
                    if u and u not in seen:
                        gallery.append(u); seen.add(u)

        return {
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "model_product": mp,
            "gallery_images": gallery
        }

    def dom_gallery_fallback(self, html_text: str) -> List[str]:
        urls: List[str] = []

        def add_url(u: Optional[str]):
            if not u: return
            u2 = self._deproxy_image_url(u)
            if u2: urls.append(u2)

        blocks: List[str] = []

        for m in re.finditer(
            r'<div[^>]+class="[^"]*product-details__preview-images[^"]*"[^>]*>(.*?)</div>',
            html_text, re.I | re.DOTALL
        ):
            blocks.append(m.group(1))
        for m in re.finditer(
            r'<div[^>]+class="[^"]*product-details__product-image[^"]*"[^>]*>(.*?)</div>',
            html_text, re.I | re.DOTALL
        ):
            blocks.append(m.group(1))

        for block in blocks:
            for tag in re.finditer(r'<img[^>]*>', block, re.I):
                t = tag.group(0)
                m_src = re.search(r'\bsrc="([^"]+)"', t, re.I)
                if m_src: add_url(m_src.group(1))
                m_dsrc = re.search(r'\bdata-src="([^"]+)"', t, re.I)
                if m_dsrc: add_url(m_dsrc.group(1))
                m_ss = re.search(r'\bsrcset="([^"]+)"', t, re.I)
                if m_ss:
                    parts = [p.strip() for p in m_ss.group(1).split(",") if p.strip()]
                    if parts:
                        add_url(parts[-1].split()[0])  # largest

        return list(dict.fromkeys([u for u in urls if u]))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Coastal Pet Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
