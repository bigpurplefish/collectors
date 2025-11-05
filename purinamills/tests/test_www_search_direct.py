#!/usr/bin/env python3
"""
Test script to directly test www site search with Playwright.
"""

import os
import sys

# Add parent path for shared imports
sys.path.insert(0, os.path.join(os.getcwd(), '..'))

from src.collector import PurinamillsCollector


def main():
    """Test www site search directly."""

    print("=" * 80)
    print("WWW SITE SEARCH DIRECT TEST (PLAYWRIGHT)")
    print("=" * 80)

    # Create collector
    collector = PurinamillsCollector()

    # Test search query
    query = "Amplify"

    print(f"\n🔍 Testing www site search directly...")
    print(f"  Query: '{query}'")
    print(f"  Search URL: https://www.purinamills.com/search?s={query}")

    # Call _search_www_site directly
    candidates = collector.searcher._search_www_site(
        query=query,
        http_get=None,  # Not used anymore
        timeout=30,
        log=print
    )

    print(f"\n✅ Search Results:")
    print(f"  Found {len(candidates)} candidate(s)")

    for i, candidate in enumerate(candidates, 1):
        print(f"\n  Candidate {i}:")
        print(f"    Name: {candidate['name']}")
        print(f"    URL: {candidate['url']}")
        print(f"    Source: {candidate['source']}")
        print(f"    Keywords: {len(candidate['kw'])} keywords")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
