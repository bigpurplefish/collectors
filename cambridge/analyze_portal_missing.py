#!/usr/bin/env python3
"""
Analyze products with missing portal data (for products that found URL matches).
"""

import re
from collections import defaultdict

def analyze_portal_missing(log_file):
    """Extract products with missing portal data."""

    with open(log_file, 'r') as f:
        content = f.read()

    missing = defaultdict(lambda: defaultdict(list))

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

        # Only look at the next ~20 lines (until next color or product)
        section_lines = section.split('\n')[:20]
        section_text = '\n'.join(section_lines)

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
            missing[product][color] = missing_items

    return missing

def main():
    log_file = 'logs/test_fallback_full.log'

    results = analyze_portal_missing(log_file)

    print("=" * 80)
    print("PORTAL DATA MISSING (For Products with URL Matches)")
    print("=" * 80)
    print()

    if results:
        total_products = len(results)
        total_variants = sum(len(colors) for colors in results.values())

        for product, colors in sorted(results.items()):
            print(f"{product}:")
            for color, missing_items in sorted(colors.items()):
                print(f"  • {color}: Missing {', '.join(missing_items)}")
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
