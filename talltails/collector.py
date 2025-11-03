#!/usr/bin/env python3
"""Tall Tails Dog Product Collector"""

import os
import sys
import re
from typing import Dict, Any, Set, Optional

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .variant_handler import VariantHandler
from .search import TalltailsSearcher
from .parser import TalltailsParser


# Site Configuration (embedded from profile)
SITE_CONFIG = {
    "site_key": "talltailsdog",
    "origin": "https://www.talltailsdog.com",
    "referer": "https://www.talltailsdog.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "search": {
        "type": "onsite",
        "endpoint": "/catalogsearch/result/?q={query}",
        "method": "GET",
        "qparam": "q",
        "expects_html_grid": True,
    },
    "catalog_required": False,
    "selectors": {
        "title": "h1",
        "feature_bullets": ".product-info-main ul li",
        "description_root": ".product.attribute.description .value",
        "materials_root": "[id*='materials'] .value, .product.attribute .value",
        "gallery_hint": "mage/gallery/gallery",
    },
    "learning": {
        "upc_disable_after": 5,
    },
    "debug": True,
}


class TalltailsCollector:
    """Tall Tails Dog product data collector."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize collector.

        Args:
            config: Optional site configuration (defaults to SITE_CONFIG)
        """
        self.config = config or SITE_CONFIG
        self.variant_handler = VariantHandler()
        self.searcher = TalltailsSearcher(self.config)
        self.parser = TalltailsParser(self.config.get("origin", ""))

        # Variant tracking for parser
        self._variant_tokens: Set[str] = set()
        self._variant_query_text: str = ""

    @staticmethod
    def _derive_variant_tokens(product_data: Optional[dict]) -> Set[str]:
        """Extract variant tokens from product data."""
        fields = []
        if isinstance(product_data, dict):
            for k in ("upcitemdb_title", "description_1", "description_2", "title", "name"):
                v = product_data.get(k)
                if isinstance(v, str):
                    fields.append(v)
        text = " ".join(fields)
        toks = set(re.findall(r"[a-z0-9]+", text.lower()))

        # helpful fused labels
        def add_if(words: list, label: str):
            if all(w in toks for w in words):
                toks.update(set(re.findall(r"[a-z0-9]+", label.lower())))
                toks.add(label.replace(" ", "_"))
                toks.add(label.replace(" ", ""))

        add_if(["cow"], "highland cow")
        add_if(["black", "bear"], "black bear")
        add_if(["cow", "print"], "cow print")
        return toks

    def find_product_url(
        self,
        upc: str,
        http_get,
        timeout: int = 30,
        log=print,
        product_data: Optional[dict] = None
    ) -> Optional[str]:
        """
        Find product page URL for a given UPC.

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout in seconds
            log: Logging function
            product_data: Optional product data for name fallback

        Returns:
            Product URL or None if not found
        """
        # Store variant info for parser
        self._variant_tokens = self._derive_variant_tokens(product_data)
        self._variant_query_text = (
            (product_data or {}).get("description_1")
            or (product_data or {}).get("upcitemdb_title")
            or ""
        )

        return self.searcher.find_product_url(upc, http_get, timeout, log, product_data)

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Parse product page HTML.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        return self.parser.parse_page(
            html_text,
            variant_handler=self.variant_handler,
            variant_query_text=self._variant_query_text,
            variant_tokens=self._variant_tokens,
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Tall Tails Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    args = parser.parse_args()
    print(f"Processing {args.input} -> {args.output}")


if __name__ == "__main__":
    main()
