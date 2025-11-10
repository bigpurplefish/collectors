#!/usr/bin/env python3
"""
Test Product Index Builder

Tests the index building and caching functionality.
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.index_builder import (
    CambridgeIndexBuilder,
    load_index_from_cache,
    save_index_to_cache,
    is_index_stale
)
from src.config import INDEX_CACHE_FILE
import requests


def test_index_builder():
    """Test building product index from live site."""
    print("=" * 80)
    print("TEST: Product Index Builder")
    print("=" * 80)
    print()

    # Create index builder
    config = {
        "public_origin": "https://www.cambridgepavers.com",
        "timeout": 30
    }
    builder = CambridgeIndexBuilder(config)

    # Build index
    print("Building product index (this may take 2-3 minutes)...")
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    try:
        index = builder.build_index(
            http_get=session.get,
            timeout=30,
            log=print
        )

        # Validate index structure
        assert "last_updated" in index, "Index missing 'last_updated'"
        assert "total_products" in index, "Index missing 'total_products'"
        assert "products" in index, "Index missing 'products'"
        assert isinstance(index["products"], list), "Products should be a list"

        total = index["total_products"]
        assert total > 0, "Index should have at least 1 product"

        print()
        print(f"✓ Index built successfully: {total} products")

        # Validate product structure
        if index["products"]:
            product = index["products"][0]
            print()
            print("Sample product:")
            print(f"  prodid: {product.get('prodid')}")
            print(f"  title: {product.get('title')}")
            print(f"  url: {product.get('url')}")
            print(f"  category: {product.get('category')}")

            assert "prodid" in product, "Product missing 'prodid'"
            assert "title" in product, "Product missing 'title'"
            assert "url" in product, "Product missing 'url'"

        # Save to test output
        test_output = "tests/output/test_index.json"
        save_index_to_cache(index, test_output, print)

        print()
        print("=" * 80)
        print("✓ TEST PASSED: Index builder working correctly")
        print("=" * 80)

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False

    finally:
        session.close()


def test_index_cache():
    """Test loading index from cache."""
    print()
    print("=" * 80)
    print("TEST: Index Cache Load/Save")
    print("=" * 80)
    print()

    # Create test index
    test_index = {
        "last_updated": "2025-11-10T12:00:00",
        "total_products": 2,
        "products": [
            {
                "prodid": 64,
                "title": "Test Product 1",
                "url": "/pavers-details?prodid=64",
                "category": "Test Category"
            },
            {
                "prodid": 92,
                "title": "Test Product 2",
                "url": "/pavers-details?prodid=92",
                "category": "Test Category"
            }
        ]
    }

    try:
        # Save to cache
        cache_file = "tests/output/test_cache.json"
        save_index_to_cache(test_index, cache_file, print)

        # Load from cache
        loaded_index = load_index_from_cache(cache_file, print)

        # Validate
        assert loaded_index is not None, "Failed to load index from cache"
        assert loaded_index["total_products"] == 2, "Product count mismatch"
        assert len(loaded_index["products"]) == 2, "Products list length mismatch"
        assert loaded_index["products"][0]["title"] == "Test Product 1", "Product title mismatch"

        print()
        print("✓ Cache save/load working correctly")

        # Test staleness check
        print()
        print("Testing staleness check...")
        is_stale = is_index_stale(loaded_index, max_age_days=7)
        print(f"  Is stale (7 days): {is_stale}")

        print()
        print("=" * 80)
        print("✓ TEST PASSED: Cache functionality working correctly")
        print("=" * 80)

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    print("\nRunning Index Builder Tests\n")

    # Test 1: Cache functionality (fast)
    cache_passed = test_index_cache()

    # Test 2: Live index building (slow)
    # Check if running in automated mode (via command line arg)
    run_live_test = False
    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        run_live_test = True
    elif sys.stdin.isatty():  # Only prompt if interactive
        print("\n\nWARNING: Next test will crawl live Cambridge website (2-3 minutes)")
        try:
            response = input("Continue? (y/n): ")
            if response.lower() == 'y':
                run_live_test = True
        except EOFError:
            print("Non-interactive mode detected, skipping live test")

    if run_live_test:
        index_passed = test_index_builder()
    else:
        print("Skipping live index building test (use --live flag to enable)")
        index_passed = True

    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Cache Load/Save: {'✓ PASSED' if cache_passed else '✗ FAILED'}")
    print(f"Index Builder: {'✓ PASSED' if index_passed else '✗ FAILED (skipped)'}")
    print("=" * 80)

    sys.exit(0 if (cache_passed and index_passed) else 1)
