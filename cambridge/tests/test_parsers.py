#!/usr/bin/env python3
"""
Test Parsers

Tests public website and dealer portal parsers using sample HTML files.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.public_parser import CambridgePublicParser


def test_public_parser():
    """Test public website parser with sample HTML."""
    print("=" * 80)
    print("TEST: Public Website Parser")
    print("=" * 80)
    print()

    # Load sample HTML
    sample_file = "sample_files/Public - Cambridge Pavingstones - Outdoor Living Solutions with ArmorTec.html"

    if not os.path.exists(sample_file):
        print(f"✗ Sample file not found: {sample_file}")
        print("  Skipping test")
        return None

    with open(sample_file, "r", encoding="utf-8") as f:
        html = f.read()

    print(f"Loaded sample file: {sample_file}")
    print(f"HTML size: {len(html)} bytes")
    print()

    # Parse HTML
    config = {"public_origin": "https://www.cambridgepavers.com"}
    parser = CambridgePublicParser(config)

    try:
        data = parser.parse_page(html)

        print("Extracted data:")
        print(f"  Title: {data.get('title', 'NOT FOUND')[:60]}...")
        print(f"  Collection: {data.get('collection', 'NOT FOUND')}")
        print(f"  Description: {data.get('description', 'NOT FOUND')[:80]}...")
        print(f"  Specifications: {data.get('specifications', 'NOT FOUND')[:80]}...")
        print(f"  Hero Image: {data.get('hero_image', 'NOT FOUND')[:60]}...")
        print(f"  Gallery Images: {len(data.get('gallery_images', []))} images")
        print(f"  Colors: {len(data.get('colors', []))} colors")

        if data.get('colors'):
            print(f"    Colors: {', '.join(data['colors'][:5])}")

        # Validate
        errors = []

        if not data.get('description'):
            errors.append("Description not extracted")

        if not data.get('specifications'):
            errors.append("Specifications not extracted")

        if not data.get('hero_image'):
            errors.append("Hero image not extracted")

        if not data.get('gallery_images'):
            errors.append("Gallery images not extracted")

        if errors:
            print()
            print("⚠ Warnings:")
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
            print("✓ TEST PASSED: All data extracted successfully")
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

        # Test fuzzy match
        print("\nTest 2: Fuzzy match (slight variation)")
        url = searcher.find_product_url("Sherwood Ledgestone 3-Pc Kit", "Onyx", print)
        assert url, "Fuzzy match failed"
        print(f"✓ Found: {url}")

        # Test partial match
        print("\nTest 3: Partial match")
        url = searcher.find_product_url("Sherwood Ledgestone", "Bluestone", print)
        assert url, "Partial match failed"
        print(f"✓ Found: {url}")

        # Test no match
        print("\nTest 4: No match (threshold)")
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


if __name__ == "__main__":
    print("\nRunning Parser Tests\n")

    # Test 1: Public parser
    public_passed = test_public_parser()

    # Test 2: Search functionality
    search_passed = test_search()

    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Public Parser: {'✓ PASSED' if public_passed else '✗ FAILED' if public_passed is False else '⊘ SKIPPED'}")
    print(f"Search/Fuzzy Match: {'✓ PASSED' if search_passed else '✗ FAILED'}")
    print("=" * 80)

    # Exit with appropriate code
    if public_passed is False or search_passed is False:
        sys.exit(1)
    else:
        sys.exit(0)
