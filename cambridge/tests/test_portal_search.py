#!/usr/bin/env python3
"""
Test Portal Search Functionality

Tests the portal product searcher using mock data.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.portal_search import CambridgePortalSearcher


def test_portal_search():
    """Test portal search with mock index."""
    print("")
    print("=" * 80)
    print("TEST: Portal Product Search")
    print("=" * 80)
    print("")

    # Create mock portal index
    mock_index = {
        "last_updated": "2025-11-10T12:00:00Z",
        "total_products": 3,
        "products": [
            {
                "title": "Sherwood Ledgestone 3-Pc. Design Kit",
                "url": "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit",
                "category": "/pavers/sherwood"
            },
            {
                "title": "RoundTable 3-Pc. Kit",
                "url": "/pavers/roundtable/roundtable-3-pc-kit",
                "category": "/pavers/roundtable"
            },
            {
                "title": "KingsCourt Circle Kit",
                "url": "/pavers/kingscourt/kingscourt-circle-kit",
                "category": "/pavers/kingscourt"
            }
        ]
    }

    # Initialize searcher
    config = {"fuzzy_match_threshold": 60.0}
    searcher = CambridgePortalSearcher(config)
    searcher.load_index(mock_index, print)
    print("")

    # Test 1: Exact match
    print("Test 1: Exact title match")
    print("Searching for: 'Sherwood Ledgestone 3-Pc. Design Kit'")
    result = searcher.find_product_by_title("Sherwood Ledgestone 3-Pc. Design Kit", print)
    assert result is not None, "Should find exact match"
    assert result["url"] == "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit"
    print(f"✓ Found: {result['url']}")
    print("")

    # Test 2: Fuzzy match (slight variation)
    print("Test 2: Fuzzy match (variation)")
    print("Searching for: 'Sherwood Ledgestone 3-Pc Kit'")
    result = searcher.find_product_by_title("Sherwood Ledgestone 3-Pc Kit", print)
    assert result is not None, "Should find fuzzy match"
    assert result["url"] == "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit"
    print(f"✓ Found: {result['url']}")
    print("")

    # Test 3: Longer partial match (should work)
    print("Test 3: Longer partial match")
    print("Searching for: 'Sherwood Ledgestone'")
    result = searcher.find_product_by_title("Sherwood Ledgestone", print)
    assert result is not None, "Should find longer partial match"
    assert result["url"] == "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit"
    print(f"✓ Found: {result['url']}")
    print("")

    # Test 4: Short partial match (below threshold)
    print("Test 4: Short partial match (below threshold)")
    print("Searching for: 'Ledgestone'")
    result = searcher.find_product_by_title("Ledgestone", print)
    print(f"Result: {result['url'] if result else 'No match (expected for short partial)'}")
    print("")

    # Test 5: No match (completely different)
    print("Test 5: No match (completely different)")
    print("Searching for: 'Completely Different Product'")
    result = searcher.find_product_by_title("Completely Different Product", print)
    assert result is None, "Should not find match for completely different product"
    print("✓ No match (expected)")
    print("")

    # Test 6: Title and color (portal doesn't use color in URL)
    print("Test 6: Title and color search (color ignored)")
    print("Searching for: title='RoundTable 3-Pc. Kit', color='Driftwood'")
    result = searcher.find_product_by_title_and_color("RoundTable 3-Pc. Kit", "Driftwood", print)
    assert result is not None, "Should find match (color ignored)"
    assert result["url"] == "/pavers/roundtable/roundtable-3-pc-kit"
    print(f"✓ Found: {result['url']}")
    print("")

    print("=" * 80)
    print("✓ TEST PASSED: Portal search functionality working correctly")
    print("=" * 80)
    print("")

    return True


if __name__ == "__main__":
    try:
        print("")
        print("Running Portal Search Tests")
        print("")

        test_portal_search()

        print("")
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("Portal Search: ✓ PASSED")
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
