"""
Search functionality for Fromm Family Foods collector.

Handles UPC overrides for product lookup.
"""

from typing import Dict, Any, Callable
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import normalize_upc


class FrommSearcher:
    """Handles product search for Fromm Family Foods."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize searcher.

        Args:
            config: Site configuration
        """
        search_config = config.get("search", {})
        self.upc_overrides = search_config.get("upc_overrides", {})

    def find_product_url(
        self,
        upc: str,
        http_get: Callable,
        timeout: int,
        log: Callable
    ) -> str:
        """
        Find product page URL for a given UPC.

        Currently only uses hardcoded overrides (no dynamic search).

        Args:
            upc: UPC to search for
            http_get: HTTP GET function (unused)
            timeout: Request timeout (unused)
            log: Logging function (unused)

        Returns:
            Product URL or empty string if not found
        """
        clean_upc = normalize_upc(upc)
        if clean_upc in self.upc_overrides:
            return self.upc_overrides[clean_upc]
        return ""
