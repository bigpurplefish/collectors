#!/usr/bin/env python3
"""
KONG Company Product Collector

Collects product data from https://www.kongcompany.com.
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
    "key": "kong",
    "display_name": "KONG Company",
    "origin": "https://www.kongcompany.com",
    "referer": "https://www.kongcompany.com/catalogue/",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
    "search": {
        "html_search_path": "/?s={QUERY}",
        "upc_overrides": {}
    }
}

from __future__ import annotations
from .base import SiteStrategy
from typing import Optional, Dict, Any, List
import re, html

class KongStrategy(SiteStrategy):
    @staticmethod
    def _text_only(s: str) -> str:
        # Convert <br> to newline, strip all HTML tags, unescape HTML entities
        s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        return html.unescape(s).strip()
    
    def find_product_page_url_for_upc(self, upc: str, http_get, timeout: int, log) -> str:
        clean = re.sub(r"\D", "", str(upc or ""))
        overrides = ((self.profile.get("search") or {}).get("upc_overrides") or {})
        if clean and clean in overrides:
            return overrides[clean]
        # If a search string override is provided in profile (e.g., product name keywords)
        query = clean
        search_term = (self.profile.get("search") or {}).get("search_term")
        if search_term:
            # Use provided search term instead of UPC if available
            query = search_term.format(UPC=clean)
        # Attempt HTML search (note: KONG site search may not index product pages without JS)
        html_path = ((self.profile.get("search") or {}).get("html_search_path") or "")
        if query and html_path and self.origin:
            url = f"{self.origin}{html_path.format(QUERY=query)}"
            log(f"Site search (HTML): {url}")
            r = http_get(url, timeout=timeout)
            if r.status_code == 200:
                # Look for any catalogue product link in search results
                m = re.search(r'href="(/catalogue/[^"<>]+)"', r.text, flags=re.I)
                if m:
                    return m.group(1)
        return ""
    
    def parse_page(self, html_text: str) -> Dict[str, Any]:
        # Title
        title = ""
        m_title = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.DOTALL | re.I)
        if m_title:
            title = self._text_only(m_title.group(1))
        
        # Description
        description = ""
        # Get first paragraph after title (product description)
        m_desc = re.search(r"</h1>\s*<p[^>]*>(.*?)</p>", html_text, re.DOTALL | re.I)
        if m_desc:
            description = self._text_only(m_desc.group(1))
        
        # Bullet point features (benefits)
        benefits: List[str] = []
        # Capture list items in the first UL after the description paragraph
        m_ul = re.search(r"</p>\s*<ul>(.*?)</ul>", html_text, re.DOTALL | re.I)
        if m_ul:
            ul_content = m_ul.group(1)
            for m in re.finditer(r"<li[^>]*>(.*?)</li>", ul_content, re.DOTALL | re.I):
                text = self._text_only(m.group(1))
                if text:
                    benefits.append(text)
        
        # Gallery Images (all variants)
        gallery: List[str] = []
        seen_ids = set()
        # Look for data-media attributes for variant image sets
        for m in re.finditer(r'data-media="([^"]+)"', html_text, re.DOTALL | re.I):
            data_str = html.unescape(m.group(1))
            # data-media string format: "key1:GUID1;key2:GUID2;..."
            parts = [p.strip() for p in data_str.split(";") if p.strip()]
            for part in parts:
                # Each part like "offpack:GUID"
                if ":" in part:
                    guid = part.split(":", 1)[1]
                else:
                    guid = part
                guid = guid.strip()
                if guid and guid not in seen_ids:
                    seen_ids.add(guid)
        # If no variants (no data-media found), fall back to parsing image URLs in HTML
        if not seen_ids:
            for m in re.finditer(r'//cdn\.amplifi\.pattern\.com/([0-9a-f\-]+)_(?:small|medium)', html_text, re.I):
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
            "gallery_images": gallery
        }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="KONG Company Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
