#!/usr/bin/env python3
"""
Analyze missing data from Cambridge collector log file.
"""

import re
import sys
from collections import defaultdict

def analyze_log(log_file):
    """Extract products and their missing data from log file."""

    with open(log_file, 'r') as f:
        content = f.read()

    # Find all failed products (no public URL found)
    failed_products = re.findall(r'\[.*?\] Processing: (.+?) \|.*?\n.*?❌ ERROR: Product URL not found', content, re.MULTILINE)

    # Find products with missing portal data
    missing_data = defaultdict(lambda: defaultdict(list))

    # Pattern to extract current product being processed
    product_pattern = r'\[(\d+)/\d+\] Processing: (.+?) \|'
    # Pattern to extract color being processed
    color_pattern = r'Collecting portal data for color: (.+?) \(product: (.+?)\)'
    # Patterns for missing data
    gallery_pattern = r'⚠ Gallery images not found'
    weight_pattern = r'⚠ Weight not found'
    model_pattern = r'⚠ Model number not found'
    cost_pattern = r'⚠ Cost not found'

    # Split log by product sections
    product_sections = re.split(r'\[\d+/\d+\] Processing:', content)[1:]

    for section in product_sections:
        # Get product title
        product_match = re.search(r'^(.+?) \|', section)
        if not product_match:
            continue
        product_title = product_match.group(1).strip()

        # Find all color variants in this product
        color_sections = re.split(r'Collecting portal data for color:', section)[1:]

        for color_section in color_sections:
            # Extract color name
            color_match = re.search(r'^(.+?) \(product:', color_section)
            if not color_match:
                continue
            color = color_match.group(1).strip()

            # Check what data is missing
            missing_items = []
            if re.search(gallery_pattern, color_section):
                missing_items.append("Gallery images")
            if re.search(weight_pattern, color_section):
                missing_items.append("Weight")
            if re.search(model_pattern, color_section):
                missing_items.append("Model number")
            if re.search(cost_pattern, color_section):
                missing_items.append("Cost")

            if missing_items:
                missing_data[product_title][color] = missing_items

    # Find products with missing public gallery images
    public_gallery_pattern = r'\[(\d+)/\d+\] Processing: (.+?) \|.*?Playwright gallery extraction failed, no gallery detected'
    public_gallery_missing = re.findall(public_gallery_pattern, content, re.DOTALL)

    return {
        'failed_products': failed_products,
        'missing_portal_data': missing_data,
        'missing_public_gallery': [p[1] for p in public_gallery_missing]
    }

def main():
    log_file = 'logs/test_fallback_full.log'

    results = analyze_log(log_file)

    print("=" * 80)
    print("MISSING DATA ANALYSIS")
    print("=" * 80)
    print()

    # 1. Completely failed products (URL not found)
    print("1. PRODUCTS WITH NO URL MATCH (Complete Failure)")
    print("-" * 80)
    if results['failed_products']:
        for i, product in enumerate(results['failed_products'], 1):
            print(f"   {i}. {product}")
        print(f"\n   Total: {len(results['failed_products'])} products")
    else:
        print("   None!")
    print()

    # 2. Products with missing portal data
    print("2. PRODUCTS WITH MISSING PORTAL DATA")
    print("-" * 80)
    if results['missing_portal_data']:
        total_variants = 0
        for product, colors in sorted(results['missing_portal_data'].items()):
            print(f"\n   {product}:")
            for color, missing in sorted(colors.items()):
                print(f"      • {color}: Missing {', '.join(missing)}")
                total_variants += 1
        print(f"\n   Total: {len(results['missing_portal_data'])} products, {total_variants} color variants")
    else:
        print("   None!")
    print()

    # 3. Products with missing public gallery images
    print("3. PRODUCTS WITH MISSING PUBLIC GALLERY IMAGES")
    print("-" * 80)
    if results['missing_public_gallery']:
        for i, product in enumerate(results['missing_public_gallery'], 1):
            print(f"   {i}. {product}")
        print(f"\n   Total: {len(results['missing_public_gallery'])} products")
    else:
        print("   None!")
    print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"   Failed products (no URL match): {len(results['failed_products'])}")
    print(f"   Products with missing portal data: {len(results['missing_portal_data'])}")
    print(f"   Products with missing public gallery: {len(results['missing_public_gallery'])}")
    print("=" * 80)

if __name__ == "__main__":
    main()
