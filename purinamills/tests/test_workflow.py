#!/usr/bin/env python3
"""
Test script to verify end-to-end Purinamills collection workflow.
"""

import os
import sys
import json
import requests

# Add parent path for shared imports
parent_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_path)

from shared.src.excel_utils import load_products
from src.collector import PurinamillsCollector
from utils.shopify_output import generate_shopify_product, merge_www_data


def test_first_product():
    """Test collection workflow with first product from input file."""

    print("=" * 80)
    print("PURINAMILLS COLLECTION WORKFLOW TEST")
    print("=" * 80)

    # Load input file
    input_file = "input/purina-mills.xlsx"
    print(f"\n📂 Loading input file: {input_file}")

    products = load_products(input_file)
    print(f"✓ Loaded {len(products)} products")

    if not products:
        print("❌ No products found in input file")
        return

    # Test with first product
    product = products[0]
    print(f"\n🔬 Testing with first product:")
    print(f"  - UPC: {product.get('upc', 'N/A')}")
    print(f"  - Item #: {product.get('item_#', 'N/A')}")
    print(f"  - Description: {product.get('description_1', 'N/A')}")

    # Initialize collector
    collector = PurinamillsCollector()

    # Step 1: Search for product URL
    print(f"\n🔍 Step 1: Searching for product...")

    upc = product.get('upc', product.get('upc_updated', ''))

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
            return

        print(f"✓ Found product URL: {product_url}")

    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 2: Fetch product page
    print(f"\n📥 Step 2: Fetching product page...")

    try:
        response = requests.get(product_url, timeout=30)
        response.raise_for_status()
        print(f"✓ Fetched {len(response.text)} bytes")

    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        return

    # Step 3: Parse product data
    print(f"\n📋 Step 3: Parsing product data...")

    try:
        parsed_data = collector.parse_page(response.text)

        print(f"✓ Parsed product:")
        print(f"  - Title: {parsed_data.get('title', 'N/A')}")
        print(f"  - Variants: {len(parsed_data.get('variants', []))}")
        print(f"  - Images: {len(parsed_data.get('gallery_images', []))}")
        print(f"  - Site source: {parsed_data.get('site_source', 'N/A')}")

    except Exception as e:
        print(f"❌ Parse failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Fetch www site for documents (if from shop)
    if parsed_data.get('site_source') == 'shop':
        print(f"\n🌐 Step 4: Fetching additional materials from www site...")

        try:
            # Convert shop URL to www URL
            www_url = product_url.replace(
                'shop.purinamills.com/products/',
                'www.purinamills.com/horse-feed/products/detail/'
            )

            print(f"  - WWW URL: {www_url}")

            www_response = requests.get(www_url, timeout=30)
            www_response.raise_for_status()

            www_data = collector.parse_page(www_response.text)

            print(f"✓ Fetched www data:")
            print(f"  - Documents: {len(www_data.get('documents', []))}")

            # Merge www data
            if www_data.get('documents'):
                parsed_data.setdefault('documents', []).extend(www_data['documents'])

        except Exception as e:
            print(f"⚠️  WWW site fetch failed (non-critical): {e}")
    else:
        print(f"\n⏭️  Step 4: Skipping www site (already from www)")

    # Step 5: Generate Shopify output
    print(f"\n🏗️  Step 5: Generating Shopify product structure...")

    try:
        shopify_product = generate_shopify_product(
            parsed_data=parsed_data,
            input_data=product,
            log=print
        )

        print(f"✓ Generated Shopify product:")
        print(f"  - Title: {shopify_product['product']['title']}")
        print(f"  - Variants: {len(shopify_product['product']['variants'])}")
        print(f"  - Images: {len(shopify_product['product']['images'])}")
        print(f"  - Metafields: {len(shopify_product['product']['metafields'])}")

        # List metafield keys
        metafield_keys = [mf['key'] for mf in shopify_product['product']['metafields']]
        print(f"  - Metafield keys: {', '.join(metafield_keys)}")

    except Exception as e:
        print(f"❌ Shopify generation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Save output
    output_file = "output/test_output.json"
    print(f"\n💾 Saving output to: {output_file}")

    os.makedirs("output", exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([shopify_product], f, indent=2, ensure_ascii=False)

    print(f"✓ Saved successfully")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_first_product()
