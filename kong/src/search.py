"""
Search functionality for KONG collector.

Handles UPC-based product search.
"""

import re
import os
import sys
from typing import Optional, Callable, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import normalize_upc


class KongSearcher:
    """Handles product search for KONG Company."""

    def __init__(self, config: dict):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
        """
        self.origin = config.get("origin", "")
        search_config = config.get("search", {})
        self.html_search_path = search_config.get("html_search_path", "")
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

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout in seconds
            log: Logging function

        Returns:
            Product URL or empty string if not found
        """
        clean = normalize_upc(upc)

        # Check overrides first
        if clean and clean in self.upc_overrides:
            return self.upc_overrides[clean]

        # Determine query (UPC or custom search term)
        query = clean
        search_term = self.html_search_path
        if search_term:
            query = search_term.format(UPC=clean) if "{UPC}" in search_term else clean

        # Try HTML search
        if query and self.html_search_path and self.origin:
            url = f"{self.origin}{self.html_search_path.format(QUERY=query)}"
            log(f"Site search (HTML): {url}")
            try:
                r = http_get(url, timeout=timeout)
                if r.status_code == 200:
                    # Look for any catalogue product link
                    m = re.search(r'href="(/catalogue/[^"<>]+)"', r.text, flags=re.I)
                    if m:
                        return m.group(1)
            except Exception:
                pass

        return ""
