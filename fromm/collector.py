#!/usr/bin/env python3
"""
Fromm Family Foods Product Collector

Collects product data from https://frommfamily.com.
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
    "key": "fromm",
    "display_name": "Fromm Family Foods",
    "origin": "https://frommfamily.com",
    "referer": "https://frommfamily.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "search": {
        "html_search_path": "",
        "autocomplete_path": "",
        "upc_overrides": {
            "072705115372": "https://frommfamily.com/products/dog/gold/dry/large-breed-adult-gold/",
            "072705115204": "https://frommfamily.com/products/dog/gold/dry/adult-gold/"
        }
    }
}

# strategies/fromm.py

import re, html
from urllib.parse import urlsplit, urlunsplit
from .base import SiteStrategy

class FrommFamilyStrategy(SiteStrategy):
    @staticmethod
    def _text_only(s: str) -> str:
        if s is None:
            return ""
        s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        return html.unescape(s).strip()

    @staticmethod
    def _clean_url(u: str) -> str:
        if not u:
            return ""
        parts = urlsplit(u)
        return urlunsplit(("https", parts.netloc, parts.path, "", ""))

    @classmethod
    def _images_from_gallery(cls, html_text: str) -> list[str]:
        """
        Capture only FULL-SIZE product gallery images from #mainCarousel.
        """
        media = []
        # Prefer data-src
        for m in re.finditer(
            r'id="mainCarousel"[\s\S]*?<div[^>]*class="carousel__slide"[^>]*\sdata-src="([^"]+)"',
            html_text, flags=re.I
        ):
            media.append(m.group(1))
        # Fallback: <img src>
        for m in re.finditer(
            r'id="mainCarousel"[\s\S]*?<div[^>]*class="carousel__slide"[\s\S]*?<img[^>]*\ssrc="([^"]+)"',
            html_text, flags=re.I
        ):
            media.append(m.group(1))
        # Filter + normalize
        out, seen = [], set()
        for u in media:
            if "cdn.frommfamily.com/media/" not in u:
                continue
            cu = cls._clean_url(u)
            if cu and cu not in seen:
                seen.add(cu)
                out.append(cu)
        return out

    def find_product_page_url_for_upc(self, upc: str, http_get, timeout: int, log) -> str:
        clean_upc = re.sub(r"\D", "", str(upc or ""))
        overrides = (self.profile.get("search") or {}).get("upc_overrides") or {}
        if clean_upc and clean_upc in overrides:
            return overrides[clean_upc]
        return ""

    def parse_page(self, html_text: str) -> dict:
        data = {}

        # Product name
        m_name = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.I|re.DOTALL)
        data["name"] = self._text_only(m_name.group(1)) if m_name else ""

        # Description (primary lead block, with fallback just after H1)  [Robustness tweak #4]
        desc_html = ""
        m_desc = re.search(r'<div class="lead">\s*<p>(.*?)</p>', html_text, flags=re.I|re.DOTALL)
        if m_desc:
            desc_html = m_desc.group(1)
        else:
            m_desc2 = re.search(r"</h1>\s*<p[^>]*>(.*?)</p>", html_text, flags=re.I|re.DOTALL)
            desc_html = m_desc2.group(1) if m_desc2 else ""
        data["description"] = self._text_only(desc_html)

        # Ingredients
        m_ing = re.search(r"<h3>Ingredients</h3>(.*?)</div>", html_text, flags=re.I|re.DOTALL)
        ingredients = self._text_only(m_ing.group(1)) if m_ing else ""
        ingredients = re.sub(r",(?=\S)", ", ", ingredients)
        data["ingredients"] = ingredients

        # Nutrition (Guaranteed Analysis + Caloric Content)
        nutrition_parts = []
        m_ga = re.search(r"<h3>Guaranteed Analysis</h3>(.*?)</ul>", html_text, flags=re.I|re.DOTALL)
        if m_ga:
            nutrition_parts.append(self._text_only(m_ga.group(1)))
        m_cal = re.search(r"<h3>Caloric Content</h3>(.*?)</section>", html_text, flags=re.I|re.DOTALL)
        if m_cal:
            nutrition_parts.append("Caloric Content: " + self._text_only(m_cal.group(1)))
        data["nutrition"] = "\n".join(p for p in nutrition_parts if p)

        # Sizes (trim trailing period + collapse whitespace)  [Robustness tweak #1]
        m_sizes = re.search(r"<h3>Available Sizes</h3>\s*<p>(.*?)</p>", html_text, flags=re.I)
        if m_sizes:
            sizes = m_sizes.group(1).strip()
            if sizes.endswith("."):
                sizes = sizes[:-1]
            data["size_info"] = re.sub(r"\s+", " ", sizes)
        else:
            data["size_info"] = ""

        # Breadcrumbs (normalize whitespace per crumb)  [Robustness tweak #2]
        crumbs = re.findall(r'<p class="breadcrumbs.*?">\s*(.*?)</p>', html_text, flags=re.I|re.DOTALL)
        bc = []
        if crumbs:
            bc = re.findall(r'>([^<]+)</a>', crumbs[0])
        data["breadcrumbs"] = [re.sub(r"\s+", " ", c).strip() for c in bc]

        # Manufacturer info
        data["manufacturer_key"] = "FROMM-FAMILY-FOODS"
        data["mpn"] = ""

        # Images (gallery only)
        data["media"] = self._images_from_gallery(html_text)

        # UPCs (derived from image filenames where present)
        upcs_found = set()
        for url in data["media"]:
            digits = re.findall(r"(\d{12,13})", url)
            for d in digits:
                if len(d) == 13 and d.startswith("0"):
                    d = d[1:]
                if len(d) == 12:
                    upcs_found.add(d)
        upc_list = sorted(upcs_found)
        if len(upc_list) == 1:
            data["upc"] = upc_list[0]
            data["key"] = f"FROMM-FAMILY-FOODS-{upc_list[0]}"
        else:
            data["upc"] = None
            base_key = (
                f"FROMM-FAMILY-FOODS-{data['name'].upper().replace(' ', '-')}"
                if data.get("name") else
                "FROMM-FAMILY-FOODS-PRODUCT"
            )
            data["key"] = base_key
            data["variants"] = [{"upc": u} for u in upc_list]

        return data


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fromm Family Foods Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
