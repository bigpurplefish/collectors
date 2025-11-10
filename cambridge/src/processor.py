"""
Processing Workflow for Cambridge Collector

Main workflow that:
1. Reads input Excel file
2. Groups records by title (variant families)
3. For each product family:
   - Searches for product URL
   - Collects public website data
   - Collects dealer portal data for each color
4. Generates Shopify products
5. Saves to output file
"""

import json
import os
import pandas as pd
from typing import Dict, List, Any, Callable

from src.collector import CambridgeCollector
from src.product_generator import CambridgeProductGenerator


def load_input_file(input_file: str, log: Callable = print) -> List[Dict[str, Any]]:
    """
    Load input Excel file.

    Args:
        input_file: Path to Excel file
        log: Logging function

    Returns:
        List of product records
    """
    try:
        log(f"Loading input file: {input_file}")

        # Read Excel file
        df = pd.read_excel(input_file)

        # Convert to list of dictionaries
        records = df.to_dict(orient="records")

        log(f"  ✓ Loaded {len(records)} records")
        return records

    except Exception as e:
        log(f"  ❌ Failed to load input file: {e}")
        raise


def save_output_file(products: List[Dict[str, Any]], output_file: str, log: Callable = print):
    """
    Save products to output JSON file.

    Args:
        products: List of Shopify product dictionaries
        output_file: Path to output file
        log: Logging function
    """
    try:
        log(f"\nSaving output to: {output_file}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save products
        output = {"products": products}

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        log(f"  ✓ Saved {len(products)} products")

    except Exception as e:
        log(f"  ❌ Failed to save output file: {e}")
        raise


def process_products(config: Dict[str, Any], status: Callable = print):
    """
    Main processing workflow.

    Args:
        config: Configuration dictionary
        status: Status logging function
    """
    status("")
    status("=" * 80)
    status("CAMBRIDGE PRODUCT COLLECTOR")
    status("=" * 80)
    status("")

    # Extract configuration
    input_file = config.get("input_file", "")
    output_file = config.get("output_file", "")
    processing_mode = config.get("processing_mode", "skip")
    start_record = config.get("start_record", "")
    end_record = config.get("end_record", "")
    force_rebuild_index = config.get("rebuild_index", False)

    # Validate inputs
    if not input_file or not os.path.exists(input_file):
        status("❌ Input file not found or not specified")
        return

    if not output_file:
        status("❌ Output file not specified")
        return

    # Initialize collector
    status("Initializing collector...")
    collector = CambridgeCollector(config)
    generator = CambridgeProductGenerator(config)

    try:
        # Ensure product index is loaded
        status("")
        if not collector.ensure_index_loaded(force_rebuild=force_rebuild_index, log=status):
            status("❌ Failed to load product index")
            return

        # Load input file
        status("")
        records = load_input_file(input_file, status)

        # Apply record range filtering
        start_idx = 0
        end_idx = None

        if start_record:
            try:
                start_idx = int(start_record) - 1
                if start_idx < 0:
                    start_idx = 0
            except (ValueError, TypeError):
                start_idx = 0

        if end_record:
            try:
                end_idx = int(end_record)
            except (ValueError, TypeError):
                end_idx = None

        records = records[start_idx:end_idx]
        status(f"\nProcessing {len(records)} records (from record #{start_idx + 1})")

        # Group records by title
        status("")
        status("Grouping records by title (variant families)...")
        product_families = generator.group_by_title(records, status)

        # Load existing output if in skip mode
        existing_products = {}
        if processing_mode == "skip" and os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_products = {
                        p["title"]: p for p in existing_data.get("products", [])
                    }
                status(f"Loaded {len(existing_products)} existing products (skip mode)")
            except Exception as e:
                status(f"⚠ Failed to load existing output: {e}")

        # Process each product family
        products = []
        success_count = 0
        skip_count = 0
        fail_count = 0

        status("")
        status("=" * 80)
        status("PROCESSING PRODUCTS")
        status("=" * 80)

        for i, (title, variant_records) in enumerate(product_families.items(), 1):
            status("")
            status(f"[{i}/{len(product_families)}] Processing: {title}")
            status(f"  Variants: {len(variant_records)} colors")

            # Skip if already processed
            if processing_mode == "skip" and title in existing_products:
                status(f"  ⏭ Skipping (already processed)")
                products.append(existing_products[title])
                skip_count += 1
                continue

            try:
                # Find product URL using first variant
                first_variant = variant_records[0]
                first_color = first_variant.get("color", "")

                product_url = collector.find_product_url(title, first_color, status)

                if not product_url:
                    status(f"  ❌ Product URL not found")
                    fail_count += 1
                    continue

                # Collect public website data
                public_data = collector.collect_public_data(product_url, status)

                if not public_data:
                    status(f"  ❌ Failed to collect public data")
                    fail_count += 1
                    continue

                # Collect portal data for each color variant
                portal_data_by_color = {}

                for variant_record in variant_records:
                    color = variant_record.get("color", "").strip()
                    if not color:
                        continue

                    status(f"  Collecting portal data for color: {color}")

                    # TODO: Map color to portal product URL
                    # For now, use the same URL (portal may have different structure)
                    portal_data = collector.collect_portal_data(product_url, status)

                    if portal_data:
                        portal_data_by_color[color] = portal_data

                # Generate Shopify product
                product = generator.generate_product(
                    title=title,
                    variant_records=variant_records,
                    public_data=public_data,
                    portal_data_by_color=portal_data_by_color,
                    log=status
                )

                products.append(product)
                success_count += 1

                status(f"  ✓ Product generated successfully")
                status(f"    - Variants: {len(product['variants'])}")
                status(f"    - Images: {len(product['images'])}")

            except Exception as e:
                status(f"  ❌ Error processing product: {e}")
                fail_count += 1
                continue

        # Save output
        status("")
        status("=" * 80)
        status("SAVING OUTPUT")
        status("=" * 80)

        save_output_file(products, output_file, status)

        # Summary
        status("")
        status("=" * 80)
        status("PROCESSING COMPLETE")
        status("=" * 80)
        status(f"✅ Successful: {success_count}")
        status(f"⏭ Skipped: {skip_count}")
        status(f"❌ Failed: {fail_count}")
        status(f"Total: {len(product_families)} product families")
        status("=" * 80)

    except Exception as e:
        status(f"\n❌ Fatal error: {e}")
        raise

    finally:
        # Cleanup
        collector.close()
