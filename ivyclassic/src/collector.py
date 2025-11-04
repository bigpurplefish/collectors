#!/usr/bin/env python3
"""
Ivyclassic Product Collector

Collects product data from https://ivyclassic.com.
"""

import os
import sys
from typing import Dict, Any, Optional, Callable

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

catalog import CatalogManager
parser import IvyclassicParser


# Site Configuration (embedded from profile)
SITE_CONFIG = {
    "site_key": "ivyclassic",
    "origin": "https://ivyclassic.com",
    "referer": "https://ivyclassic.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "fetch_jitter_min_ms": 200,
    "fetch_jitter_max_ms": 700,
    "candidate_cap": 8,
    "hl": "en",
    "gl": "us",
    "bv_auth_required": False,
    "bv_base_url": "",
    "bv_common_params": {},
    "requires_catalog": True
}


class IvyclassicCollector:
    """Ivyclassic product data collector."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize collector.

        Args:
            config: Optional site configuration (defaults to SITE_CONFIG)
        """
        self.config = config or SITE_CONFIG
        self.origin = self.config.get("origin", "https://ivyclassic.com").rstrip("/")

        # Initialize catalog manager
        catalog_path = (
            self.config.get("catalog_json_file")
            or self.config.get("product_catalog")
            or ""
        ).strip()
        self.catalog = CatalogManager(catalog_path)

        # Initialize parser
        self.parser = IvyclassicParser(self.origin)

    def set_catalog_path(self, path: Optional[str]) -> None:
        """
        Set or update the catalog path.

        Args:
            path: Path to catalog JSON file
        """
        self.catalog.set_catalog_path(path)

    def find_product_url(
        self,
        upc: str,
        http_get: Callable[..., Any],
        timeout: float,
        log: Callable[[str], None],
    ) -> Optional[str]:
        """
        Find product page URL for a given UPC.

        Discovery order:
          1) If profile requires a catalog, enforce presence of a catalog path.
          2) Try local UPC→PDP catalog (exact/normalized matches).
          3) If not found, return None (no search fallback).

        Args:
            upc: UPC to search for
            http_get: HTTP GET function (kept for interface compatibility)
            timeout: Request timeout (kept for interface compatibility)
            log: Logging function

        Returns:
            Product URL or None if not found
        """
        if not upc:
            log("[Ivy] No UPC provided.")
            return None

        # Honor profile flag 'requires_catalog'
        requires_catalog = bool(self.config.get("requires_catalog", False))
        if requires_catalog and not self.catalog.catalog_path:
            log(
                "[Ivy] Catalog required by profile ('requires_catalog': true), "
                "but no path was provided."
            )
            return None

        catalog_url = self.catalog.lookup(upc, log)
        if catalog_url:
            log(f"[Ivy] Catalog hit for UPC {upc}: {catalog_url}")
            return catalog_url

        log(f"[Ivy] Catalog miss for UPC {upc}; no search fallback enabled.")
        return None

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Parse product page HTML.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        return self.parser.parse_page(html_text)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Ivyclassic Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")


if __name__ == "__main__":
    main()
