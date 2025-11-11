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
from src.index_builder import save_index_to_cache, load_index_from_cache
from src.config import PORTAL_INDEX_CACHE_FILE, load_config


def test_portal_index_builder():
    """Test portal index builder with authenticated two-stage API."""
    print("")
    print("=" * 80)
    print("TEST: Portal Index Builder (Two-Stage Authenticated API)")
    print("=" * 80)
    print("")

    # Load config to get credentials
    cfg = load_config()

    # Check if credentials are configured
    if not cfg.get("portal_username") or not cfg.get("portal_password"):
        print("⚠ SKIPPED: Portal credentials not configured in config.json")
        print("   Please configure portal_username and portal_password to run this test")
        return True

    # Initialize builder with credentials
    config = {
        "portal_origin": "https://shop.cambridgepavers.com",
        "portal_username": cfg.get("portal_username"),
        "portal_password": cfg.get("portal_password")
    }
    builder = CambridgePortalIndexBuilder(config)

    # Build index
    print("Building portal product index using two-stage authenticated API...")
    print("(This will take several minutes as it queries search API for each category)")
    print("")
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

    # Validate products have required fields (including search API fields)
    for i, product in enumerate(products[:5]):  # Check first 5
        assert "title" in product, f"Product {i} missing 'title'"
        assert "url" in product, f"Product {i} missing 'url'"
        assert "category" in product, f"Product {i} missing 'category'"
        assert "sku" in product, f"Product {i} missing 'sku'"
        assert "price" in product, f"Product {i} missing 'price'"
        assert "stock" in product, f"Product {i} missing 'stock'"
        assert "images" in product, f"Product {i} missing 'images'"

        # Validate URL format (includes urlcomponent)
        url = product["url"]
        assert url.startswith("/"), f"Product {i} URL should start with '/': {url}"
        assert url.count("/") >= 3, f"Product {i} URL should have 3+ segments: {url}"

        # Validate images is a list
        assert isinstance(product["images"], list), f"Product {i} images should be a list"

    print(f"✓ All products have required fields (including SKU, price, stock, images)")

    # Check for Sherwood products (known category)
    sherwood_products = [p for p in products if "/sherwood" in p.get("url", "")]
    assert len(sherwood_products) > 0, "Should find Sherwood products"
    print(f"✓ Found {len(sherwood_products)} Sherwood products")

    # Display sample products with new fields
    print("")
    print("Sample products:")
    for i, product in enumerate(products[:3], 1):
        print(f"  {i}. {product['title']}")
        print(f"     URL: {product['url']}")
        print(f"     Category: {product['category']}")
        print(f"     SKU: {product['sku']}")
        print(f"     Price: ${product['price']}")
        print(f"     Stock: {product['stock']}")
        print(f"     Images: {len(product['images'])} image(s)")
        if product['images']:
            print(f"     First Image: {product['images'][0][:80]}...")
    print("")

    # Test cache save/load functionality
    print("Testing cache save/load...")
    save_index_to_cache(index, PORTAL_INDEX_CACHE_FILE, print)
    print("✓ Cache saved")

    # Load from cache and verify
    loaded_index = load_index_from_cache(PORTAL_INDEX_CACHE_FILE, print)
    assert loaded_index is not None, "Failed to load index from cache"
    assert loaded_index["total_products"] == total, "Loaded index has different product count"
    assert len(loaded_index["products"]) == len(products), "Loaded index has different number of products"
    print("✓ Cache loaded and verified")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Portal index builder and cache working correctly")
    print("=" * 80)
    print("")

    return True


if __name__ == "__main__":
    try:
        print("")
        print("Running Portal Index Builder Tests")
        print("")
        print("NOTE: This test uses authenticated APIs to fetch product data.")
        print("      It requires:")
        print("      - Internet connection")
        print("      - Portal credentials configured in config.json")
        print("      - Several minutes to complete (queries 362 categories)")
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
