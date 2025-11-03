"""
Search functionality for Coastal Pet collector.

Handles UPC-based product search.
"""

import re
from typing import Optional, Callable, Any
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import normalize_upc


class CoastalSearcher:
    """Handles product search for Coastal Pet."""

    def __init__(self, config: dict):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
        """
        self.origin = config.get("origin", "")
        search_config = config.get("search", {})
        self.html_search_path = search_config.get("html_search_path", "")
        self.autocomplete_path = search_config.get("autocomplete_path", "")
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
        2. HTML search endpoint
        3. Autocomplete endpoint

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout in seconds
            log: Logging function

        Returns:
            Product URL or empty string if not found
        """
        clean_upc = normalize_upc(upc)

        # Check overrides first
        if clean_upc in self.upc_overrides:
            return self.upc_overrides[clean_upc]

        # Try HTML search
        if self.html_search_path and self.origin:
            url = f"{self.origin}{self.html_search_path.format(QUERY=clean_upc)}"
            log(f"Site search (HTML): {url}")
            try:
                response = http_get(url, timeout=timeout)
                if response.status_code == 200:
                    match = re.search(
                        r'href="(/products/detail/\?id=[^"<>]+)"',
                        response.text,
                        flags=re.I
                    )
                    if match:
                        return match.group(1)
            except Exception:
                pass

        # Try autocomplete search
        if self.autocomplete_path and self.origin:
            url = f"{self.origin}{self.autocomplete_path.format(QUERY=clean_upc)}"
            log(f"Site search (autocomplete): {url}")
            try:
                response = http_get(url, timeout=timeout)
                if response.status_code == 200:
                    match = re.search(
                        r'/products/detail/\?id=[A-Za-z0-9]+',
                        response.text
                    )
                    if match:
                        return match.group(0)
            except Exception:
                pass

        return ""
