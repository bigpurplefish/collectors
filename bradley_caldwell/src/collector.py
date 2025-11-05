#!/usr/bin/env python3
"""
Bradley Caldwell Product Collector

This collector uses a pre-built JSON catalog to enrich product data.
No web scraping is performed - all data comes from the catalog file.
"""

import os
import sys
from typing import Dict, Any, Optional

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import load_json_file, save_json_file
from src.catalog import CatalogManager
from src.enricher import ProductEnricher


# Bradley Caldwell Site Configuration (embedded from profile)
SITE_CONFIG = {
    "key": "bradley_caldwell",
    "display_name": "Bradley Caldwell",
    "origin": "https://www.bradleycaldwell.com",
    "referer": "https://www.bradleycaldwell.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
    "search": {
        "upc_overrides": {}
    }
}


class BradleyCaldwellCollector:
    """
    Zero-scrape collector that requires a product-catalog JSON file.
    Reads product URLs, titles, brands, UPCs, descriptions, and images from the catalog.
    """

    def __init__(self, catalog_path: Optional[str] = None):
        """
        Initialize collector.

        Args:
            catalog_path: Path to product catalog JSON file
        """
        self.catalog = CatalogManager(catalog_path)
        self.enricher = ProductEnricher()

    def set_catalog_path(self, path: str) -> None:
        """
        Set or update the catalog path.

        Args:
            path: Path to catalog JSON file
        """
        self.catalog.set_catalog_path(path)

    def find_product_by_upc(self, upc: str) -> str:
        """
        Locate product page URL for the given UPC from catalog.

        Args:
            upc: UPC to search for

        Returns:
            Product URL or empty string if not found
        """
        return self.catalog.find_product_url(upc)

    def enrich_product(self, input_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a product record with data from the catalog.

        Args:
            input_row: Input product record (must contain UPC field)

        Returns:
            Enriched product record with manufacturer data
        """
        from shared.src import normalize_upc

        # Ensure catalog is loaded
        self.catalog.ensure_loaded()

        # Extract UPC from input
        upc_digits = normalize_upc(
            input_row.get("upc")
            or input_row.get("upc_updated")
            or input_row.get("upc_staged")
            or ""
        )

        # Look up catalog record
        catalog_record = self.catalog.get_by_upc(upc_digits) or {}

        # Enrich product
        return self.enricher.enrich(input_row, catalog_record)

    def process_file(self, input_path: str, output_path: str) -> None:
        """
        Process an input JSON file and write enriched output.

        Args:
            input_path: Path to input JSON file (array of products)
            output_path: Path to output JSON file
        """
        # Load input products
        products = load_json_file(input_path)

        if not isinstance(products, list):
            raise ValueError("Input JSON must be an array of products")

        # Enrich each product
        enriched = []
        for product in products:
            try:
                enriched_product = self.enrich_product(product)
                enriched.append(enriched_product)
            except Exception as e:
                print(f"Error processing product {product.get('upc', 'unknown')}: {e}")
                # Keep original product on error
                enriched.append(product)

        # Save output
        save_json_file(enriched, output_path)

        print(f"Processed {len(enriched)} products")
        print(f"Output written to: {output_path}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Bradley Caldwell Product Collector")
    parser.add_argument("--catalog", required=True, help="Path to product catalog JSON file")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    collector = BradleyCaldwellCollector(catalog_path=args.catalog)
    collector.process_file(args.input, args.output)


if __name__ == "__main__":
    main()
