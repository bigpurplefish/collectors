#!/usr/bin/env python3
"""
Script to rebuild the Cambridge dealer portal product index.

This script uses the authenticated two-stage approach to:
1. Fetch category URLs from the navigation API
2. Fetch product details from the search API (authenticated)
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import load_config, save_config
from portal_index_builder import CambridgePortalIndexBuilder
import json


def save_portal_index(index, output_file, log=print):
    """Save portal index to file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    log(f"\n✓ Saved portal index to: {output_path}")
    log(f"  Total products: {index.get('total_products', 0)}")


def main():
    """Build portal product index."""
    # Load configuration
    config = load_config()

    # Create index builder
    builder = CambridgePortalIndexBuilder(config)

    # Build index
    index = builder.build_index(log=print)

    # Save to cache
    cache_dir = Path(__file__).parent.parent / "cache"
    output_file = cache_dir / "portal_product_index.json"

    save_portal_index(index, output_file, log=print)


if __name__ == "__main__":
    main()
