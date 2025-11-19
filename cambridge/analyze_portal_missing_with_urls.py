#!/usr/bin/env python3
"""
Analyze products with missing portal data and include URLs.
"""

import re
from collections import defaultdict

def analyze_portal_missing_with_urls(log_file):
    """Extract products with missing portal data and their URLs."""

    with open(log_file, 'r') as f:
        content = f.read()

    missing = defaultdict(lambda: defaultdict(dict))

    # Find all color sections with missing data
    # Pattern: look for color being processed, then check what's missing
    color_sections = re.split(r'Collecting portal data for color: (.+?) \(product: (.+?)\)', content)[1:]

    # Process in groups of 3 (color, product, section content)
    for i in range(0, len(color_sections), 3):
        if i + 2 >= len(color_sections):
            break

        color = color_sections[i].strip()
        product = color_sections[i + 1].strip()
        section = color_sections[i + 2]

        # Only look at the next ~30 lines (until next color or product)
        section_lines = section.split('\n')[:30]
        section_text = '\n'.join(section_lines)

        # Extract URL
        url_match = re.search(r'Fetching portal page: (https://[^\s]+)', section_text)
        url = url_match.group(1) if url_match else "URL not found"

        # Check for missing data
        missing_items = []
        if '⚠ Gallery images not found' in section_text:
            missing_items.append('Gallery images')
        if '⚠ Weight not found' in section_text:
            missing_items.append('Weight')
        if '⚠ Model number not found' in section_text:
            missing_items.append('Model number')
        if '⚠ Cost not found' in section_text:
            missing_items.append('Cost')

        if missing_items:
            missing[product][color] = {
                'missing': missing_items,
                'url': url
            }

    return missing

def main():
    log_file = 'logs/test_fallback_full.log'

    results = analyze_portal_missing_with_urls(log_file)

    print("=" * 80)
    print("PORTAL DATA MISSING (For Products with URL Matches)")
    print("=" * 80)
    print()

    if results:
        total_products = len(results)
        total_variants = sum(len(colors) for colors in results.values())

        for product, colors in sorted(results.items()):
            print(f"{product}:")
            for color, data in sorted(colors.items()):
                print(f"  • {color}")
                print(f"    Missing: {', '.join(data['missing'])}")
                print(f"    URL: {data['url']}")
            print()

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Products with missing portal data: {total_products}")
        print(f"Total color variants affected: {total_variants}")
        print("=" * 80)
    else:
        print("✅ NO MISSING PORTAL DATA!")
        print("All products with URL matches have complete portal data.")
        print("=" * 80)

if __name__ == "__main__":
    main()
