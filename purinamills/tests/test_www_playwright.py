#!/usr/bin/env python3
"""
Test script to verify Playwright-based www site scraping.
Tests document extraction from www.purinamills.com using Playwright.
"""

import os
import sys

# Add parent path for shared imports
sys.path.insert(0, os.path.join(os.getcwd(), '..'))

from src.collector import PurinamillsCollector


def main():
    """Test www site scraping with Playwright."""

    print("=" * 80)
    print("WWW SITE PLAYWRIGHT SCRAPING TEST")
    print("=" * 80)

    # Create collector
    collector = PurinamillsCollector()

    # Test URL: Amplify Hi-Fat Horse Supplement
    url = "https://www.purinamills.com/horse-feed/products/detail/purina-amplify-high-fat-horse-supplement"

    print(f"\n📥 Fetching page with Playwright: {url}")

    # Fetch using Playwright
    html = collector.parser.fetch_www_page_with_playwright(url)

    print(f"✓ Fetched {len(html)} bytes of HTML")

    # Parse the HTML
    print(f"\n📋 Parsing page...")
    result = collector.parse_page(html)

    print(f"\n✅ Parsed Results:")
    print(f"  - Title: {result.get('title', 'N/A')}")
    print(f"  - Site source: {result.get('site_source', 'N/A')}")
    print(f"  - Features: {len(result.get('features_benefits', ''))} chars")
    print(f"  - Documents: {len(result.get('documents', []))}")

    # Show document details
    for i, doc in enumerate(result.get('documents', []), 1):
        print(f"\n  Document {i}:")
        print(f"    - Title: {doc.get('title', 'N/A')}")
        print(f"    - URL: {doc.get('url', 'N/A')}")
        print(f"    - Type: {doc.get('type', 'N/A')}")

    # Show features preview
    features = result.get('features_benefits', '')
    if features:
        print(f"\n  Features & Benefits (first 500 chars):")
        print(f"    {features[:500]}...")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
