#!/usr/bin/env python3
"""
Test script to verify parent/variant structure works correctly.
Tests both single-item products and parent-variant groups.
"""

import os
import sys
import json
import requests

# Add parent path for shared imports
parent_path = os.path.join(os.getcwd(), '..')
sys.path.insert(0, parent_path)

from shared.src.excel_utils import load_products
from src.collector import PurinamillsCollector
from utils.shopify_output import generate_shopify_product


def test_product_group(parent_product, variants, test_name, collector):
    """Test collection workflow for a product group."""

    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)

    product = parent_product
    upc = product.get('upc', product.get('upc_updated', ''))

    print(f"\n📦 Product Group:")
    print(f"  - Parent Item #: {product.get('item_#')}")
    print(f"  - Parent: {product.get('parent', '(blank)')}")
    print(f"  - Variants: {len(variants)}")
    print(f"  - Description: {product.get('description_1', 'N/A')[:60]}")
    print(f"  - Option 1: {product.get('option_1', '(blank)')}")
    print(f"  - Option 2: {product.get('option_2', '(blank)')}")

    if variants:
        print(f"\n  Variant Items:")
        for v in variants:
            print(f"    - Item #: {v.get('item_#')}, Size: {v.get('size', 'N/A')}, UPC: {v.get('upc', 'N/A')}")

    # Step 1: Search for product URL
    print(f"\n🔍 Step 1: Searching for product...")

    try:
        product_url = collector.find_product_url(
            upc=upc,
            http_get=requests.get,
            timeout=30,
            log=print,
            product_data=product
        )

        if not product_url:
            print("❌ Product not found")
            return None

        print(f"✓ Found product URL: {product_url}")

    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Step 2: Fetch product page
    print(f"\n📥 Step 2: Fetching product page...")

    try:
        response = requests.get(product_url, timeout=30)
        response.raise_for_status()
        print(f"✓ Fetched {len(response.text)} bytes")

    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        return None

    # Step 3: Parse product data
    print(f"\n📋 Step 3: Parsing product data...")

    try:
        parsed_data = collector.parse_page(response.text)

        print(f"✓ Parsed product:")
        print(f"  - Title: {parsed_data.get('title', 'N/A')}")
        print(f"  - Images: {len(parsed_data.get('gallery_images', []))}")
        print(f"  - Site source: {parsed_data.get('site_source', 'N/A')}")

    except Exception as e:
        print(f"❌ Parse failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Step 4: Generate Shopify output structure
    print(f"\n🏗️  Step 4: Generating Shopify product structure...")

    try:
        shopify_product = generate_shopify_product(
            parsed_data=parsed_data,
            input_data=product,
            variant_data=variants,
            log=print
        )

        print(f"✓ Generated Shopify product:")
        print(f"  - Title: {shopify_product['product']['title']}")
        print(f"  - Variants: {len(shopify_product['product']['variants'])}")
        print(f"  - Options: {len(shopify_product['product']['options'])}")

        # Show option details
        for opt in shopify_product['product']['options']:
            print(f"    - {opt['name']}: {opt['values']}")

        # Show variant details
        print(f"\n  Variant Details:")
        for v in shopify_product['product']['variants']:
            opt_str = f"option1={v.get('option1')}, option2={v.get('option2')}"
            print(f"    - SKU: {v['sku']}, Price: ${v['price']}, {opt_str}")

    except Exception as e:
        print(f"❌ Shopify generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    print(f"\n✅ TEST PASSED: {test_name}")
    return shopify_product


def main():
    """Run tests."""

    print("=" * 80)
    print("PURINAMILLS PARENT/VARIANT STRUCTURE TEST")
    print("=" * 80)

    # Load input file
    input_file = "input/purina-mills.xlsx"
    print(f"\n📂 Loading input file: {input_file}")

    products = load_products(input_file)
    print(f"✓ Loaded {len(products)} products")

    # Initialize collector
    collector = PurinamillsCollector()

    # Test 1: Single-item product (no parent field)
    # Find first product with blank parent
    single_product = None
    for p in products:
        if not str(p.get('parent', '')).strip():
            single_product = p
            break

    if single_product:
        result1 = test_product_group(
            single_product,
            [],
            "Single-Item Product (No Variants)",
            collector
        )
    else:
        print("\n⚠️  No single-item products found")

    # Test 2: Parent-variant group
    # Find parent 36962
    parent_36962 = None
    variants_36962 = []

    for p in products:
        item_num = str(p.get('item_#', ''))
        parent = str(p.get('parent', '')).strip()

        if item_num == '36962' and parent == '36962':
            parent_36962 = p
        elif parent == '36962' and item_num != '36962':
            variants_36962.append(p)

    if parent_36962:
        result2 = test_product_group(
            parent_36962,
            variants_36962,
            "Parent-Variant Group (36962 + variants)",
            collector
        )

        # Save output
        if result2:
            output_file = "output/test_variants.json"
            print(f"\n💾 Saving output to: {output_file}")

            os.makedirs("output", exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump([result2], f, indent=2, ensure_ascii=False)

            print(f"✓ Saved successfully")
    else:
        print("\n⚠️  Parent product 36962 not found")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
