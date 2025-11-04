#!/usr/bin/env python3
"""
Purinamills Product Collector

Collects product data from https://shop.purinamills.com.
"""

import os
import sys
from typing import Dict, Any

# Add parent directories to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.search import PurinamillsSearcher
from src.parser import PurinamillsParser


# Site Configuration (embedded from profile)
SITE_CONFIG = {
    "site_key": "purinamills",

    # Primary e-commerce site (Shopify)
    "shop_origin": "https://shop.purinamills.com",
    "shop_search_path": "/search",
    "shop_search_param": "q",

    # Secondary information site (fallback)
    "www_origin": "https://www.purinamills.com",
    "www_search_path": "/search",
    "www_search_param": "q",

    # Legacy compatibility
    "origin": "https://shop.purinamills.com",
    "referer": "https://shop.purinamills.com/",

    # HTTP settings
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "fetch_jitter_min_ms": 200,
    "fetch_jitter_max_ms": 700,
    "timeout": 30,

    # Search settings
    "max_search_candidates": 10,
    "fuzzy_match_threshold": 0.3,
}


class PurinamillsCollector:
    """Purinamills product data collector."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize collector.

        Args:
            config: Optional site configuration (defaults to SITE_CONFIG)
        """
        self.config = config or SITE_CONFIG
        self.searcher = PurinamillsSearcher(self.config)
        self.parser = PurinamillsParser(self.config)

    def find_product_url(
        self,
        upc: str,
        http_get,
        timeout: float = 30,
        log=print,
        product_data: Dict[str, Any] = None
    ) -> str:
        """
        Find product page URL for a given UPC.

        Uses fuzzy name matching against product index.

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout in seconds
            log: Logging function
            product_data: Optional product data for name matching

        Returns:
            Product URL or empty string if not found
        """
        return self.searcher.find_product_url(upc, http_get, timeout, log, product_data)

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Parse product page HTML.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        return self.parser.parse_page(html_text)
