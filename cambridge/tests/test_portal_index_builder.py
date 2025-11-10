#!/usr/bin/env python3
"""
Test Portal Index Builder

Tests the portal product index builder using the navigation API.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.portal_index_builder import CambridgePortalIndexBuilder


def test_portal_index_builder():
    """Test portal index builder with live API."""
    print("")
    print("=" * 80)
    print("TEST: Portal Index Builder (Navigation API)")
    print("=" * 80)
    print("")

    # Initialize builder
    config = {
        "portal_origin": "https://shop.cambridgepavers.com"
    }
    builder = CambridgePortalIndexBuilder(config)

    # Build index
    print("Building portal product index from navigation API...")
    index = builder.build_index(print)

    # Validate index structure
    assert "last_updated" in index, "Index missing 'last_updated' field"
    assert "total_products" in index, "Index missing 'total_products' field"
    assert "products" in index, "Index missing 'products' field"
    print(f"✓ Index structure valid")

    # Validate product count
    total = index["total_products"]
    products = index["products"]
    assert total > 0, "Index should have products"
    assert len(products) == total, f"Product count mismatch: {len(products)} vs {total}"
    print(f"✓ Found {total} products")

    # Validate products have required fields
    for i, product in enumerate(products[:5]):  # Check first 5
        assert "title" in product, f"Product {i} missing 'title'"
        assert "url" in product, f"Product {i} missing 'url'"
        assert "category" in product, f"Product {i} missing 'category'"

        # Validate URL format
        url = product["url"]
        assert url.startswith("/"), f"Product {i} URL should start with '/': {url}"
        assert url.count("/") >= 3, f"Product {i} URL should have 3+ segments: {url}"

    print(f"✓ All products have required fields")

    # Check for Sherwood products (known category)
    sherwood_products = [p for p in products if "/sherwood" in p.get("url", "")]
    assert len(sherwood_products) > 0, "Should find Sherwood products"
    print(f"✓ Found {len(sherwood_products)} Sherwood products")

    # Display sample products
    print("")
    print("Sample products:")
    for i, product in enumerate(products[:5], 1):
        print(f"  {i}. {product['title']}")
        print(f"     URL: {product['url']}")
        print(f"     Category: {product['category']}")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Portal index builder working correctly")
    print("=" * 80)
    print("")

    return True


if __name__ == "__main__":
    try:
        print("")
        print("Running Portal Index Builder Tests")
        print("")
        print("NOTE: This test fetches live data from the navigation API.")
        print("      It requires an internet connection.")
        print("")

        test_portal_index_builder()

        print("")
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("Portal Index Builder: ✓ PASSED")
        print("=" * 80)
        print("")

    except AssertionError as e:
        print("")
        print("=" * 80)
        print("✗ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print("")
        sys.exit(1)
    except Exception as e:
        print("")
        print("=" * 80)
        print("✗ TEST ERROR")
        print("=" * 80)
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("")
        sys.exit(1)
