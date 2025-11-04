"""
Search functionality for Chala Handbags collector.

Handles UPC-based product search.
"""

import re
from typing import Callable, Any
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import normalize_upc


class ChalaSearcher:
    """Handles product search for Chala Handbags."""

    def __init__(self, config: dict):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
        """
        self.origin = config.get("origin", "")
        search_config = config.get("search", {})
        self.search_path = search_config.get("html_search_path", "/search?q={QUERY}")
        self.upc_overrides = search_config.get("upc_overrides", {})

    def find_product_url(
        self,
        upc: str,
        http_get: Callable[[str, int], Any],
        timeout: int,
        log: Callable[[str], None]
    ) -> str:
        """
        Find product page URL for a given UPC.

        Searches using:
        1. UPC overrides (hardcoded mappings)
        2. Full UPC search
        3. Partial UPC search (last 5 digits)

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout in seconds
            log: Logging function

        Returns:
            Product URL or empty string if not found
        """
        upc_str = normalize_upc(upc)
        if not upc_str:
            return ""

        # Check overrides
        if upc_str in self.upc_overrides:
            return self.upc_overrides[upc_str]

        # Try full UPC search
        if self.search_path and self.origin:
            search_url = f"{self.origin}{self.search_path.format(QUERY=upc_str)}"
            log(f"Site search for UPC: {search_url}")

            try:
                response = http_get(search_url, timeout=timeout)
                if response and getattr(response, "status_code", 0) == 200:
                    match = re.search(
                        r'href="(/products/[^"<>]+)"',
                        response.text,
                        flags=re.I
                    )
                    if match:
                        return match.group(1)
            except Exception:
                pass

        # Fallback: partial search by last 5 digits
        partial_query = upc_str[-5:] if len(upc_str) >= 5 else upc_str
        if partial_query and self.search_path and self.origin:
            search_url = f"{self.origin}{self.search_path.format(QUERY=partial_query)}"
            log(f"Site search for partial UPC: {search_url}")

            try:
                response = http_get(search_url, timeout=timeout)
                if response and getattr(response, "status_code", 0) == 200:
                    match = re.search(
                        r'href="(/products/[^"<>]+)"',
                        response.text,
                        flags=re.I
                    )
                    if match:
                        return match.group(1)
            except Exception:
                pass

        return ""
