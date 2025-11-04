"""
Catalog management for Bradley Caldwell Product Collector.

Handles loading and indexing the product catalog JSON file.
"""

import os
from typing import Dict, Any, Optional
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import load_json_file, build_catalog_index


class CatalogManager:
    """Manages the Bradley Caldwell product catalog."""

    def __init__(self, catalog_path: Optional[str] = None):
        """
        Initialize catalog manager.

        Args:
            catalog_path: Path to catalog JSON file (optional, can be set later)
        """
        self.catalog_path = (catalog_path or "").strip()
        self.catalog_loaded = False
        self.by_upc: Dict[str, Dict[str, Any]] = {}
        self.by_url: Dict[str, Dict[str, Any]] = {}

    def set_catalog_path(self, path: str) -> None:
        """
        Set or update the catalog path.

        Args:
            path: Path to catalog JSON file
        """
        self.catalog_path = (path or "").strip()
        self.catalog_loaded = False

    def ensure_loaded(self) -> None:
        """
        Load the product catalog from JSON file if not already loaded.

        Raises:
            RuntimeError: If catalog path not set or file not found/invalid
        """
        if self.catalog_loaded:
            return

        if not self.catalog_path:
            raise RuntimeError(
                "No Bradley Caldwell product catalog specified. "
                "Please provide a catalog JSON file path."
            )

        if not os.path.isfile(self.catalog_path):
            raise RuntimeError(
                f"Product catalog not found: {self.catalog_path}. "
                "Please select a valid JSON file."
            )

        # Load catalog data
        items = load_json_file(self.catalog_path)
        if not isinstance(items, list):
            items = []

        # Build indexes
        self.by_upc, self.by_url = build_catalog_index(items)
        self.catalog_loaded = True

    def get_by_upc(self, upc: str) -> Optional[Dict[str, Any]]:
        """
        Get product record by UPC.

        Args:
            upc: UPC to look up (will be normalized)

        Returns:
            Product record or None if not found
        """
        from shared.src import normalize_upc

        self.ensure_loaded()
        clean = normalize_upc(upc)
        return self.by_upc.get(clean)

    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get product record by URL.

        Args:
            url: Product URL to look up

        Returns:
            Product record or None if not found
        """
        self.ensure_loaded()
        url_clean = url.strip()
        return self.by_url.get(url_clean)

    def find_product_url(self, upc: str) -> str:
        """
        Locate product page URL for the given UPC from catalog.

        Args:
            upc: UPC to search for

        Returns:
            Product URL or empty string if not found
        """
        rec = self.get_by_upc(upc)
        return (rec or {}).get("product_url", "") or ""
