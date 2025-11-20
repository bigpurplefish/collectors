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

    # Create mock portal index (v1.6.0+: products include color in title)
    mock_index = {
        "last_updated": "2025-11-10T12:00:00Z",
        "total_products": 5,
        "products": [
            {
                "title": "Sherwood Ledgestone 3-Pc. Design Kit Onyx",
                "url": "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit-onyx",
                "category": "/pavers/sherwood"
            },
            {
                "title": "Sherwood Ledgestone 3-Pc. Design Kit Driftwood",
                "url": "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit-driftwood",
                "category": "/pavers/sherwood"
            },
            {
                "title": "RoundTable 3-Pc. Kit Driftwood",
                "url": "/pavers/roundtable/roundtable-3-pc-kit-driftwood",
                "category": "/pavers/roundtable"
            },
            {
                "title": "KingsCourt 4\" x 8\" Holland Onyx",
                "url": "/pavers/kingscourt/kingscourt-4x8-holland-onyx",
                "category": "/pavers/kingscourt"
            },
            {
                "title": "KingsCourt Circle Kit Coal",
                "url": "/pavers/kingscourt/kingscourt-circle-kit-coal",
                "category": "/pavers/kingscourt"
            }
        ]
    }

    # Initialize searcher
    config = {"fuzzy_match_threshold": 60.0}
    searcher = CambridgePortalSearcher(config)
    searcher.load_index(mock_index, print)
    print("")

    # Test 1: Exact title + color match (v1.6.0+)
    print("Test 1: Exact title + color match")
    print("Searching for: title='Sherwood Ledgestone 3-Pc. Design Kit', color='Onyx'")
    result = searcher.find_product_by_title_and_color("Sherwood Ledgestone 3-Pc. Design Kit", "Onyx", print)
    assert result is not None, "Should find exact match"
    assert result["url"] == "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit-onyx"
    print(f"✓ Found: {result['url']}")
    print("")

    # Test 2: Exact match with different color
    print("Test 2: Exact match with different color")
    print("Searching for: title='Sherwood Ledgestone 3-Pc. Design Kit', color='Driftwood'")
    result = searcher.find_product_by_title_and_color("Sherwood Ledgestone 3-Pc. Design Kit", "Driftwood", print)
    assert result is not None, "Should find exact match with different color"
    assert result["url"] == "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit-driftwood"
    print(f"✓ Found: {result['url']}")
    print("")

    # Test 3: Actual quote characters (v1.7.2+)
    # Note: Normalization now happens at data loading stage (processor.py)
    # Search receives already-normalized data with actual quote characters
    print("Test 3: Actual quote characters (after normalization at load time)")
    print("Searching for: title='KingsCourt 4\" x 8\" Holland', color='Onyx'")
    result = searcher.find_product_by_title_and_color('KingsCourt 4" x 8" Holland', "Onyx", print)
    assert result is not None, "Should find match with actual quote characters"
    assert result["url"] == "/pavers/kingscourt/kingscourt-4x8-holland-onyx"
    print(f"✓ Found: {result['url']}")
    print("")

    # Test 4: No match (wrong color)
    print("Test 4: No match (wrong color)")
    print("Searching for: title='Sherwood Ledgestone 3-Pc. Design Kit', color='NonExistentColor'")
    result = searcher.find_product_by_title_and_color("Sherwood Ledgestone 3-Pc. Design Kit", "NonExistentColor", print)
    assert result is None, "Should not find match for non-existent color"
    print("✓ No match (expected)")
    print("")

    # Test 5: No match (wrong title)
    print("Test 5: No match (wrong title)")
    print("Searching for: title='Completely Different Product', color='Onyx'")
    result = searcher.find_product_by_title_and_color("Completely Different Product", "Onyx", print)
    assert result is None, "Should not find match for completely different product"
    print("✓ No match (expected)")
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
