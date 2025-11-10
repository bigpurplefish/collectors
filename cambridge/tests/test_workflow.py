#!/usr/bin/env python3
"""
Test End-to-End Workflow

Tests the complete workflow with a small sample of products.
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collector import CambridgeCollector
from src.product_generator import CambridgeProductGenerator
from src.processor import load_input_file


def test_workflow():
    """Test complete workflow with sample data."""
    print("=" * 80)
    print("TEST: End-to-End Workflow")
    print("=" * 80)
    print()

    # Configuration
    config = {
        "public_origin": "https://www.cambridgepavers.com",
        "portal_origin": "https://shop.cambridgepavers.com",
        "portal_username": "",  # Not needed for this test
        "portal_password": "",
        "timeout": 30,
        "rebuild_index": False
    }

    # Check input file
    input_file = "pdf_parser/output/cambridge_products.xlsx"
    if not os.path.exists(input_file):
        print(f"✗ Input file not found: {input_file}")
        print("  Please ensure the input file exists")
        return False

    try:
        # Load input file
        print(f"Loading input file: {input_file}")
        records = load_input_file(input_file, print)

        # Take first 2 records for testing
        test_records = records[:2]
        print(f"  Using first {len(test_records)} records for testing")
        print()

        # Display records
        for i, record in enumerate(test_records, 1):
            print(f"Record {i}:")
            print(f"  Title: {record.get('title', 'N/A')}")
            print(f"  Color: {record.get('color', 'N/A')}")
            print(f"  Vendor Type: {record.get('vendor_type', 'N/A')}")
            print()

        # Initialize collector
        print("Initializing collector...")
        collector = CambridgeCollector(config)
        generator = CambridgeProductGenerator(config)

        # Ensure index is loaded
        print()
        print("Loading product index...")
        if not collector.ensure_index_loaded(force_rebuild=False, log=print):
            print("✗ Failed to load product index")
            print("  Try running: python3 scripts/build_index.py")
            return False

        # Group by title
        print()
        print("Grouping records by title...")
        product_families = generator.group_by_title(test_records, print)

        # Process first product family only
        print()
        print("Processing first product family...")
        title = list(product_families.keys())[0]
        variant_records = product_families[title]

        print(f"  Title: {title}")
        print(f"  Variants: {len(variant_records)}")

        # Find product URL
        first_color = variant_records[0].get("color", "")
        print(f"  Searching for: {title} ({first_color})")
        print()

        product_url = collector.find_product_url(title, first_color, print)

        if not product_url:
            print()
            print("✗ Product URL not found")
            print("  This may be due to:")
            print("    - Product not in index (try rebuilding)")
            print("    - Title mismatch between input and website")
            return False

        print()
        print(f"✓ Found product URL: {product_url}")

        # Collect public data
        print()
        print("Collecting public website data...")
        public_data = collector.collect_public_data(product_url, print)

        if not public_data:
            print("✗ Failed to collect public data")
            return False

        print()
        print("Public data collected:")
        print(f"  Description: {len(public_data.get('description', ''))} chars")
        print(f"  Specifications: {len(public_data.get('specifications', ''))} chars")
        print(f"  Hero Image: {public_data.get('hero_image', 'N/A')[:60]}")
        print(f"  Gallery Images: {len(public_data.get('gallery_images', []))}")

        # Generate product (without portal data for this test)
        print()
        print("Generating Shopify product...")
        portal_data_by_color = {}  # Empty for this test

        product = generator.generate_product(
            title=title,
            variant_records=variant_records,
            public_data=public_data,
            portal_data_by_color=portal_data_by_color,
            log=print
        )

        print()
        print("Product generated:")
        print(f"  Title: {product['title']}")
        print(f"  Vendor: {product['vendor']}")
        print(f"  Status: {product['status']}")
        print(f"  Options: {len(product['options'])}")
        print(f"  Variants: {len(product['variants'])}")
        print(f"  Images: {len(product['images'])}")
        print(f"  Metafields: {len(product['metafields'])}")

        # Save test output
        test_output = "tests/output/test_workflow_output.json"
        os.makedirs(os.path.dirname(test_output), exist_ok=True)

        output = {"products": [product]}
        with open(test_output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print()
        print(f"✓ Test output saved: {test_output}")

        # Validate output structure
        print()
        print("Validating output structure...")
        errors = []

        if not product.get("title"):
            errors.append("Missing title")
        if not product.get("descriptionHtml"):
            errors.append("Missing descriptionHtml")
        if product.get("status") != "ACTIVE":
            errors.append("Status should be ACTIVE")
        if not product.get("variants"):
            errors.append("Missing variants")
        if not product.get("options"):
            errors.append("Missing options")

        if errors:
            print("✗ Validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        print("✓ Output structure valid")

        print()
        print("=" * 80)
        print("✓ TEST PASSED: Workflow completed successfully")
        print("=" * 80)
        print()
        print("Note: This test did not include dealer portal data collection")
        print("      (requires credentials and is slow)")

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False

    finally:
        if 'collector' in locals():
            collector.close()


if __name__ == "__main__":
    print("\nRunning End-to-End Workflow Test\n")

    passed = test_workflow()

    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"End-to-End Workflow: {'✓ PASSED' if passed else '✗ FAILED'}")
    print("=" * 80)

    sys.exit(0 if passed else 1)
