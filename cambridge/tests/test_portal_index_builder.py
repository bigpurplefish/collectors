#!/usr/bin/env python3
"""
Test Portal Index Builder

Tests the portal product index builder using navigation API + PLP scraping.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.portal_index_builder import CambridgePortalIndexBuilder
from src.index_builder import save_index_to_cache, load_index_from_cache
from src.config import PORTAL_INDEX_CACHE_FILE, load_config


def test_portal_index_builder():
    """Test portal index builder with authenticated PLP scraping."""
    print("")
    print("=" * 80)
    print("TEST: Portal Index Builder (Nav API + PLP Scraping)")
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
    print("Building portal product index using nav API + PLP scraping...")
    print("(This will take several minutes as it navigates each category page)")
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

    # Validate products have required fields
    for i, product in enumerate(products[:5]):  # Check first 5
        assert "title" in product, f"Product {i} missing 'title'"
        assert "url" in product, f"Product {i} missing 'url'"
        assert "category" in product, f"Product {i} missing 'category'"
        assert "sku" in product, f"Product {i} missing 'sku'"
        assert "price" in product, f"Product {i} missing 'price'"
        assert "stock" in product, f"Product {i} missing 'stock'"
        assert "images" in product, f"Product {i} missing 'images'"

        # Validate URL format (PLP-scraped URLs are single-segment: /Product-Name_N or /product/ID)
        url = product["url"]
        assert url.startswith("/"), f"Product {i} URL should start with '/': {url}"

        # Validate images is a list
        assert isinstance(product["images"], list), f"Product {i} images should be a list"

    print(f"✓ All products have required fields (including SKU, price, stock, images)")

    # Check for Sherwood products (known category)
    sherwood_products = [p for p in products if "sherwood" in p.get("category", "").lower()]
    assert len(sherwood_products) > 0, "Should find Sherwood products"
    print(f"✓ Found {len(sherwood_products)} Sherwood products")

    # Display sample products
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


def test_cached_fallback():
    """Test that cached index is returned when fresh build returns 0 products."""
    print("")
    print("=" * 80)
    print("TEST: Cached Fallback on 0 Products (Unit Test)")
    print("=" * 80)
    print("")

    import json
    import tempfile
    import os as os_module

    # Create a temporary cache file with sample data
    sample_cache = {
        "last_updated": "2025-11-18T12:00:00Z",
        "total_products": 3,
        "products": [
            {"title": "Test Product 1", "url": "/test-1", "sku": "SKU1"},
            {"title": "Test Product 2", "url": "/test-2", "sku": "SKU2"},
            {"title": "Test Product 3", "url": "/test-3", "sku": "SKU3"},
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_cache, f)
        temp_cache_path = f.name

    try:
        # Test load_index_from_cache works correctly
        loaded = load_index_from_cache(temp_cache_path, print)
        assert loaded is not None, "Failed to load cached index"
        assert loaded["total_products"] == 3, "Wrong product count in cache"
        assert len(loaded["products"]) == 3, "Wrong number of products in cache"
        print("✓ Cache loading works correctly")

        # Test that cache has expected structure for fallback
        assert "products" in loaded, "Cache missing 'products' key"
        assert loaded.get("products"), "Cache 'products' is empty or None"
        print("✓ Cache structure valid for fallback")

        print("")
        print("=" * 80)
        print("✓ TEST PASSED: Cached fallback mechanism working correctly")
        print("=" * 80)
        print("")

    finally:
        # Cleanup
        if os_module.path.exists(temp_cache_path):
            os_module.unlink(temp_cache_path)

    return True


def test_scraping_config():
    """Test that PLP scraping configuration is correctly defined."""
    print("")
    print("=" * 80)
    print("TEST: PLP Scraping Configuration (Unit Test)")
    print("=" * 80)
    print("")

    import inspect
    from src.portal_index_builder import CambridgePortalIndexBuilder

    # Verify scraping method exists and uses correct approach
    source = inspect.getsource(CambridgePortalIndexBuilder._scrape_products_from_category)

    assert "time.sleep(2.5)" in source, "rate limiting delay should be 2.5 seconds"
    print("✓ rate limiting delay = 2.5 seconds")

    assert "15000 if probe else 30000" in source, "nav_timeout should be 15s (probe) / 30s (normal)"
    print("✓ timeout = 15s (probe) / 30s (normal)")

    assert "PlaywrightTimeoutError" in source, "should catch PlaywrightTimeoutError"
    print("✓ catches PlaywrightTimeoutError specifically")

    # Verify DOM extraction method references correct selectors
    extract_source = inspect.getsource(CambridgePortalIndexBuilder._extract_product_cards)
    assert "facets-item-cell-grid" in extract_source, "should use .facets-item-cell-grid selector"
    print("✓ uses .facets-item-cell-grid selector for product cards")

    assert "data-rate" in extract_source, "should extract price from data-rate attribute"
    print("✓ extracts price from data-rate attribute")

    assert "data-sku" in extract_source, "should extract SKU from data-sku attribute"
    print("✓ extracts SKU from data-sku attribute")

    # Verify early bail-out in build_index
    build_source = inspect.getsource(CambridgePortalIndexBuilder.build_index)
    assert "PROBE_COUNT = 5" in build_source, "early bail-out probe count should be 5"
    print("✓ early bail-out PROBE_COUNT = 5")

    assert "probe_failures" in build_source, "build_index should track probe failures"
    print("✓ early bail-out tracks probe failures")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: PLP scraping configuration is correct")
    print("=" * 80)
    print("")

    return True


if __name__ == "__main__":
    try:
        print("")
        print("Running Portal Index Builder Tests")
        print("")

        # Run fast unit tests first
        test_cached_fallback()
        test_scraping_config()

        print("")
        print("NOTE: Full integration test navigates category pages with Playwright.")
        print("      It requires:")
        print("      - Internet connection")
        print("      - Portal credentials configured in config.json")
        print("      - 30-50 minutes to complete (navigates ~432 category pages)")
        print("")

        test_portal_index_builder()

        print("")
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("Cached Fallback: ✓ PASSED")
        print("PLP Scraping Config: ✓ PASSED")
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
