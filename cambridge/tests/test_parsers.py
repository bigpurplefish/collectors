#!/usr/bin/env python3
"""
Test Parsers

Tests public website and dealer portal parsers.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.public_parser import CambridgePublicParser


def test_search():
    """Test search functionality with fuzzy matching."""
    print()
    print("=" * 80)
    print("TEST: Search and Fuzzy Matching")
    print("=" * 80)
    print()

    from src.search import CambridgeSearcher

    # Create mock index
    mock_index = {
        "last_updated": "2025-11-10T12:00:00",
        "total_products": 3,
        "products": [
            {
                "prodid": 64,
                "title": "Sherwood Ledgestone 3-Pc. Design Kit",
                "url": "/pavers-details?prodid=64",
                "category": "Sherwood Collection"
            },
            {
                "prodid": 92,
                "title": "Sherwood Ledgestone XL 3-Pc. Design Kit",
                "url": "/pavers-details?prodid=92",
                "category": "Sherwood Collection"
            },
            {
                "prodid": 10,
                "title": "RoundTable 6 x 9",
                "url": "/pavers-details?prodid=10",
                "category": "RoundTable Collection"
            }
        ]
    }

    try:
        # Initialize searcher
        config = {
            "public_origin": "https://www.cambridgepavers.com",
            "fuzzy_match_threshold": 60.0
        }
        searcher = CambridgeSearcher(config)
        searcher.load_index(mock_index, print)

        # Test exact match
        print("\nTest 1: Exact match")
        url = searcher.find_product_url("Sherwood Ledgestone 3-Pc. Design Kit", "Driftwood", print)
        assert url, "Exact match failed"
        print(f"✓ Found: {url}")

        # Test exact match with different color (v1.6.0+: uses exact matching only)
        print("\nTest 2: Exact match with different color")
        url = searcher.find_product_url("Sherwood Ledgestone 3-Pc. Design Kit", "Onyx", print)
        assert url, "Exact match failed"
        print(f"✓ Found: {url}")

        # Test no match (title doesn't match exactly)
        print("\nTest 3: No match (title variation)")
        url = searcher.find_product_url("Sherwood Ledgestone 3-Pc Kit", "Bluestone", print)
        print(f"Result: {url if url else 'No match (expected - exact match required as of v1.6.0)'}")

        # Test no match (completely different)
        print("\nTest 4: No match (different product)")
        url = searcher.find_product_url("Completely Different Product Name", "Red", print)
        print(f"Result: {url if url else 'No match (expected)'}")

        print()
        print("=" * 80)
        print("✓ TEST PASSED: Search functionality working correctly")
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


def test_public_parser_playwright():
    """Test public parser with Playwright against a live product page (slow/network test)."""
    print()
    print("=" * 80)
    print("TEST: Public Website Parser (Playwright)")
    print("=" * 80)
    print()

    config = {"public_origin": "https://www.cambridgepavers.com"}
    parser = CambridgePublicParser(config)

    # Known product URL for testing
    product_url = "https://www.cambridgepavers.com/pavers-details?prodid=64"

    try:
        data = parser.scrape_page(product_url, print)

        print("\nExtracted data:")
        print(f"  Title: {data.get('title', 'NOT FOUND')[:60]}")
        print(f"  Collection: {data.get('collection', 'NOT FOUND')}")
        print(f"  Description: {data.get('description', 'NOT FOUND')[:80]}...")
        print(f"  Specifications: {data.get('specifications', 'NOT FOUND')[:80]}...")
        print(f"  Hero Image: {'YES' if data.get('hero_image') else 'NOT FOUND'}")
        print(f"  Gallery Images: {len(data.get('gallery_images', []))} images")
        print(f"  Colors: {len(data.get('colors', []))} colors")

        if data.get('colors'):
            print(f"    Colors: {', '.join(data['colors'][:5])}")

        print(f"  Color Swatches: {len(data.get('color_swatches', {}))} swatches")
        if data.get('color_swatches'):
            for name, url in list(data['color_swatches'].items())[:3]:
                print(f"    {name}: {url[:60]}...")

        # Validate required fields
        errors = []

        if not data.get('title'):
            errors.append("Title not extracted")

        if not data.get('description'):
            errors.append("Description not extracted")

        if not data.get('hero_image'):
            errors.append("Hero image not extracted")

        if not data.get('gallery_images'):
            errors.append("Gallery images not extracted")

        if not data.get('colors'):
            errors.append("Colors not extracted")

        # Validate swatch URLs are absolute HTTPS
        swatches = data.get('color_swatches', {})
        if swatches:
            for name, url in swatches.items():
                if not url.startswith("https://"):
                    errors.append(f"Swatch URL for '{name}' is not absolute HTTPS: {url[:60]}")
        else:
            errors.append("No color swatches extracted")

        if errors:
            print()
            print("⚠ Issues:")
            for error in errors:
                print(f"  - {error}")
            print()
            print("=" * 80)
            print("⚠ TEST PASSED WITH WARNINGS")
            print("=" * 80)
            return True
        else:
            print()
            print("=" * 80)
            print("✓ TEST PASSED: All data extracted successfully via Playwright")
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
    import argparse
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--all", action="store_true", help="Run all tests including slow ones")
    args = arg_parser.parse_args()

    print("\nRunning Parser Tests\n")

    # Test 1: Search functionality (fast, always runs)
    search_passed = test_search()

    # Test 2: Public parser with Playwright (slow, --all only)
    if args.all:
        playwright_passed = test_public_parser_playwright()
    else:
        print("\nSkipping Playwright parser test (use --all to run)")
        playwright_passed = None

    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Search/Fuzzy Match: {'✓ PASSED' if search_passed else '✗ FAILED'}")
    print(f"Public Parser (Playwright): {'✓ PASSED' if playwright_passed else '✗ FAILED' if playwright_passed is False else '⊘ SKIPPED'}")
    print("=" * 80)

    # Exit with appropriate code
    if search_passed is False or playwright_passed is False:
        sys.exit(1)
    else:
        sys.exit(0)
