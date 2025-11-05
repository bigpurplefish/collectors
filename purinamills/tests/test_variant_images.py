#!/usr/bin/env python3
"""
Test script to verify variant-image mapping extraction.
"""

import os
import sys
import json

# Add parent path for shared imports
sys.path.insert(0, os.path.join(os.getcwd(), '..'))

from src.collector import PurinamillsCollector


def main():
    """Test variant-image mapping."""

    print("=" * 80)
    print("VARIANT-IMAGE MAPPING TEST")
    print("=" * 80)

    # Create collector
    collector = PurinamillsCollector()

    # Test URL (Omega Match product with 2 variants)
    test_url = "https://shop.purinamills.com/products/purina-omega-match-ahiflower-oil-supplement"

    print(f"\n🔍 Testing variant-image mapping extraction...")
    print(f"  URL: {test_url}")

    # Fetch and parse the page
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(test_url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract variant-image mapping
    variant_image_data = collector.parser._extract_shop_variant_image_map(soup)

    print(f"\n✅ Variant-Image Mapping Results:")
    print(f"  Total Images: {len(variant_image_data.get('images', []))}")
    print(f"  Total Variant Mappings: {len(variant_image_data.get('variant_image_map', {}))}")

    print("\n📸 Images:")
    for img in variant_image_data.get('images', []):
        print(f"\n  Position {img['position']}:")
        print(f"    URL: {img['src'][:80]}...")
        print(f"    Alt: {img['alt']}")
        print(f"    Variant Keys: {img['variant_keys']}")

    print("\n🔗 Variant-to-Image Mappings:")
    for variant_key, img_info in variant_image_data.get('variant_image_map', {}).items():
        print(f"\n  Variant: {variant_key}")
        print(f"    Image Position: {img_info['position']}")
        print(f"    Options: {img_info['options']}")
        print(f"    Image URL: {img_info['src'][:80]}...")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
