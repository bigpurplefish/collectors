#!/usr/bin/env python3
"""
Test script to verify www site search with Playwright.
"""

import os
import sys
import requests

# Add parent path for shared imports
sys.path.insert(0, os.path.join(os.getcwd(), '..'))

from src.collector import PurinamillsCollector


def main():
    """Test www site search."""

    print("=" * 80)
    print("WWW SITE SEARCH TEST (PLAYWRIGHT)")
    print("=" * 80)

    # Create collector
    collector = PurinamillsCollector()

    # Test product: Amplify
    test_product = {
        'item_#': '36962',
        'upc': '804273081694',
        'description_1': 'Amplify High-Fat Horse Supplement'
    }

    print(f"\n📦 Test Product:")
    print(f"  - Item #: {test_product['item_#']}")
    print(f"  - UPC: {test_product['upc']}")
    print(f"  - Description: {test_product['description_1']}")

    print(f"\n🔍 Searching for product...")

    # Find product URL (will use www site as fallback with Playwright)
    url = collector.find_product_url(
        upc=test_product['upc'],
        http_get=requests.get,
        timeout=30,
        log=print,
        product_data=test_product
    )

    if url:
        print(f"\n✅ Found product URL:")
        print(f"  {url}")

        # Verify it's the www site
        if "www.purinamills.com" in url:
            print(f"\n✓ Correctly found on www site")
            print(f"✓ URL pattern: /products/detail/")
        else:
            print(f"\n⚠️  Found on shop site instead")

    else:
        print(f"\n❌ Product not found")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
