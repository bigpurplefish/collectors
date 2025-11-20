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

Implements dual logging pattern from GUI_DESIGN_REQUIREMENTS.md:
- User-friendly messages to status callback (GUI)
- Detailed technical logs to console and file
"""

import json
import os
import sys
import logging
import math
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

# Add shared utils to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from utils.logging_utils import (
    log_and_status,
    log_section_header,
    log_progress,
    log_success,
    log_warning,
    log_error,
    log_summary
)

from src.collector import CambridgeCollector
from src.product_generator import CambridgeProductGenerator
from src.data_validator import DataValidator


def load_input_file(input_file: str, status_fn: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """
    Load input Excel file.

    Args:
        input_file: Path to Excel file
        status_fn: Status callback function

    Returns:
        List of product records
    """
    try:
        log_and_status(
            status_fn,
            msg=f"Loading input file: {input_file} (Excel format)",
            ui_msg=f"Loading input file..."
        )

        # Read Excel file
        df = pd.read_excel(input_file)

        # Convert to list of dictionaries
        records = df.to_dict(orient="records")

        # Normalize escaped characters and symbols in string fields
        # Excel data may contain literal escaped quotes (e.g., \"  ) that should be actual quotes (")
        # Excel data may contain copyright symbol (©) that should be (C) for portal matching
        for record in records:
            for key, value in record.items():
                if isinstance(value, str):
                    # Normalize escaped quotes to actual quotes
                    value = value.replace('\\"', '"')
                    # Normalize copyright symbol to (C)
                    value = value.replace('©', '(C)')
                    record[key] = value

        log_success(
            status_fn,
            msg=f"Loaded {len(records)} records from input file",
            details=f"File: {input_file}, Format: Excel (.xlsx), Records: {len(records)}"
        )

        return records

    except Exception as e:
        log_error(
            status_fn,
            msg="Failed to load input file",
            details=f"File: {input_file}",
            exc=e
        )
        raise


def save_output_file(products: List[Dict[str, Any]], output_file: str, status_fn: Optional[Callable] = None):
    """
    Save products to output JSON file.

    Args:
        products: List of Shopify product dictionaries
        output_file: Path to output file
        status_fn: Status callback function
    """
    try:
        log_and_status(
            status_fn,
            msg=f"Saving output to: {output_file} (JSON format, {len(products)} products)",
            ui_msg="Saving output..."
        )

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Save products
        output = {"products": products}

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        # Calculate file size
        file_size_bytes = os.path.getsize(output_file)
        file_size_kb = file_size_bytes / 1024

        log_success(
            status_fn,
            msg=f"Saved {len(products)} products to output file",
            details=f"File: {output_file}, Products: {len(products)}, Size: {file_size_kb:.2f} KB"
        )

    except Exception as e:
        log_error(
            status_fn,
            msg="Failed to save output file",
            details=f"File: {output_file}",
            exc=e
        )
        raise


def extract_existing_variants_by_color_unit(product: Dict[str, Any]) -> Dict[tuple, Dict[str, Any]]:
    """
    Extract existing variants from a product, keyed by (color, unit) combination.

    Args:
        product: Product dictionary from output file

    Returns:
        Dictionary mapping (color, unit) tuple to variant data
    """
    variants_by_color_unit = {}
    for variant in product.get("variants", []):
        color = variant.get("option1", "").strip()
        unit = variant.get("option2", "").strip()
        if color and unit:
            key = (color, unit)
            variants_by_color_unit[key] = variant
    return variants_by_color_unit


def variant_has_portal_data(variant: Dict[str, Any]) -> bool:
    """
    Check if a variant has complete portal data (SKU, price, cost).

    Args:
        variant: Single variant dictionary

    Returns:
        True if variant has SKU, price, and cost
    """
    has_sku = bool(variant.get("sku"))
    has_price = bool(variant.get("price"))
    has_cost = bool(variant.get("cost"))
    return has_sku and has_price and has_cost


def determine_variant_unit(variant_record: Dict[str, Any]) -> Optional[str]:
    """
    Determine the unit of sale for a variant record based on pricing data.

    This matches the logic in product_generator.py:
    - Priority: "Piece" if has cost_per_piece and price_per_piece
    - Fallback: "Sq Ft" if has sq_ft_cost and sq_ft_price

    Args:
        variant_record: Input record from Excel file

    Returns:
        "Piece", "Sq Ft", or None if no pricing data
    """
    import math

    # Check for piece pricing
    cost_per_piece = variant_record.get("cost_per_piece")
    price_per_piece = variant_record.get("price_per_piece")

    has_piece_cost = cost_per_piece is not None and not (isinstance(cost_per_piece, float) and math.isnan(cost_per_piece))
    has_piece_price = price_per_piece is not None and not (isinstance(price_per_piece, float) and math.isnan(price_per_piece))

    if has_piece_cost and has_piece_price:
        return "Piece"

    # Check for sq ft pricing
    sq_ft_cost = variant_record.get("sq_ft_cost")
    sq_ft_price = variant_record.get("sq_ft_price")

    has_sqft_cost = sq_ft_cost is not None and not (isinstance(sq_ft_cost, float) and math.isnan(sq_ft_cost))
    has_sqft_price = sq_ft_price is not None and not (isinstance(sq_ft_price, float) and math.isnan(sq_ft_price))

    if has_sqft_cost and has_sqft_price:
        return "Sq Ft"

    return None


def process_products(config: Dict[str, Any], status_fn: Optional[Callable] = None):
    """
    Main processing workflow.

    Args:
        config: Configuration dictionary
        status_fn: Status callback function
    """
    log_section_header(status_fn, "CAMBRIDGE PRODUCT COLLECTOR")
    log_and_status(status_fn, "", ui_msg="")

    # Extract configuration
    input_file = config.get("input_file", "")
    output_file = config.get("output_file", "")
    processing_mode = config.get("processing_mode", "skip")
    start_record = config.get("start_record", "")
    end_record = config.get("end_record", "")
    force_rebuild_index = config.get("rebuild_index", False)

    # Validate inputs
    if not input_file or not os.path.exists(input_file):
        log_error(
            status_fn,
            msg="Input file not found or not specified",
            details=f"Input file path: {input_file}"
        )
        return

    if not output_file:
        log_error(
            status_fn,
            msg="Output file not specified",
            details="Output file path is empty in configuration"
        )
        return

    # Initialize collector
    log_and_status(
        status_fn,
        msg=f"Initializing Cambridge collector (processing_mode={processing_mode}, start={start_record or 'beginning'}, end={end_record or 'end'})",
        ui_msg="Initializing collector..."
    )
    collector = CambridgeCollector(config)
    generator = CambridgeProductGenerator(config)

    try:
        # Ensure product index is loaded (public site)
        log_and_status(status_fn, "", ui_msg="")
        if not collector.ensure_index_loaded(force_rebuild=force_rebuild_index, log=status_fn):
            log_error(
                status_fn,
                msg="Failed to load public product index",
                details=f"Force rebuild: {force_rebuild_index}"
            )
            return

        # Ensure portal product index is loaded
        log_and_status(status_fn, "", ui_msg="")
        if not collector.ensure_portal_index_loaded(force_rebuild=force_rebuild_index, log=status_fn):
            log_error(
                status_fn,
                msg="Failed to load portal product index",
                details=f"Force rebuild: {force_rebuild_index}"
            )
            return

        # Load input file
        log_and_status(status_fn, "", ui_msg="")
        records = load_input_file(input_file, status_fn)

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

        log_and_status(
            status_fn,
            msg=f"Processing {len(records)} records (from record #{start_idx + 1}, mode={processing_mode})",
            ui_msg=f"Processing {len(records)} records (from record #{start_idx + 1})"
        )

        # Group records by title
        log_and_status(status_fn, "", ui_msg="")
        log_and_status(
            status_fn,
            msg=f"Grouping {len(records)} records by title to create variant families",
            ui_msg="Grouping records by title (variant families)..."
        )
        product_families = generator.group_by_title(records, status_fn)

        # Load existing output (for both skip and overwrite modes)
        # This allows incremental saving in both modes
        existing_products = {}
        if os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_products = {
                        p["title"]: p for p in existing_data.get("products", [])
                    }
                mode_msg = "skip mode enabled" if processing_mode == "skip" else "overwrite mode enabled"
                log_and_status(
                    status_fn,
                    msg=f"Loaded {len(existing_products)} existing products from {output_file} ({mode_msg})",
                    ui_msg=f"Loaded {len(existing_products)} existing products ({mode_msg})"
                )
            except Exception as e:
                log_warning(
                    status_fn,
                    msg="Failed to load existing output",
                    details=f"File: {output_file}, Error: {str(e)}"
                )

        # Process each product family
        # Use dictionary for easy updates and incremental saving
        products_dict = existing_products.copy()
        failures = []  # Track failed products with details
        warnings = []  # Track products with warnings (missing portal data)
        success_count = 0
        skip_count = 0
        fail_count = 0
        variant_success_count = 0  # Track successful variants
        variant_skip_count = 0  # Track skipped variants (existing data)
        variant_fail_count = 0  # Track failed variants (missing portal data)

        log_and_status(status_fn, "", ui_msg="")
        log_section_header(status_fn, "PROCESSING PRODUCTS")

        for i, (portal_title, variant_records) in enumerate(product_families.items(), 1):
            log_and_status(status_fn, "", ui_msg="")

            colors_str = ", ".join([v.get("color", "") for v in variant_records[:3]])
            if len(variant_records) > 3:
                colors_str += f" +{len(variant_records) - 3} more"

            log_progress(
                status_fn,
                current=i,
                total=len(product_families),
                item_name=portal_title,
                details=f"Variants={len(variant_records)}, Colors=[{colors_str}]"
            )

            # Variant-level skip logic (skip mode only)
            # Check each input record (variant) by color+unit combination
            existing_variants_by_color_unit = {}
            variants_to_skip = set()  # Set of (color, unit) tuples
            variants_to_process = []  # List of variant_records to process

            if processing_mode == "skip" and portal_title in products_dict:
                # Extract existing variants keyed by (color, unit)
                existing_product = products_dict[portal_title]
                existing_variants_by_color_unit = extract_existing_variants_by_color_unit(existing_product)

                # Check each input record individually
                for variant_record in variant_records:
                    color = variant_record.get("color", "").strip()
                    if not color:
                        continue

                    # Determine the unit for this record
                    unit = determine_variant_unit(variant_record)
                    if not unit:
                        # No pricing data, can't determine unit - process anyway
                        variants_to_process.append(variant_record)
                        continue

                    variant_key = (color, unit)

                    # Check if this specific color+unit combination already exists with portal data
                    if variant_key in existing_variants_by_color_unit:
                        existing_variant = existing_variants_by_color_unit[variant_key]
                        if variant_has_portal_data(existing_variant):
                            variants_to_skip.add(variant_key)
                            variant_skip_count += 1
                        else:
                            variants_to_process.append(variant_record)
                    else:
                        variants_to_process.append(variant_record)

                # If all variants should be skipped, skip entire product
                if not variants_to_process and variants_to_skip:
                    log_and_status(
                        status_fn,
                        msg=f"[{i}/{len(product_families)}] Skipping: {portal_title} - all {len(variants_to_skip)} variants have portal data",
                        ui_msg="  ⏭ Skipping (all variants processed)"
                    )
                    skip_count += 1
                    continue

                # Log which variants we're skipping vs processing
                if variants_to_skip:
                    skip_labels = [f"{c}/{u}" for c, u in sorted(list(variants_to_skip)[:3])]
                    if len(variants_to_skip) > 3:
                        skip_labels.append(f"+{len(variants_to_skip) - 3} more")
                    log_and_status(
                        status_fn,
                        msg=f"  Skipping {len(variants_to_skip)} variants with existing portal data: {', '.join(skip_labels)}",
                        ui_msg=f"  Skipping {len(variants_to_skip)} variants"
                    )
                if variants_to_process:
                    log_and_status(
                        status_fn,
                        msg=f"  Processing {len(variants_to_process)} variants",
                        ui_msg=f"  Processing {len(variants_to_process)} new/missing variants"
                    )
            else:
                # Not skip mode or product doesn't exist - process all records
                variants_to_process = [v for v in variant_records if v.get("color", "").strip()]

            try:
                # Get public_title from first variant (used for public site search)
                first_variant = variant_records[0]
                first_color = first_variant.get("color", "")

                # Handle public_title (may be NaN from Excel)
                public_title_raw = first_variant.get("public_title", "")
                if isinstance(public_title_raw, float) and math.isnan(public_title_raw):
                    public_title = ""
                elif isinstance(public_title_raw, str):
                    public_title = public_title_raw.strip()
                else:
                    public_title = str(public_title_raw).strip() if public_title_raw is not None else ""

                # Find product URL using public_title (skip if empty)
                product_url = ""
                if public_title:
                    product_url = collector.find_product_url(public_title, first_color, status_fn)
                else:
                    log_and_status(
                        status_fn,
                        msg="  No public_title in input file, skipping public site scraping",
                        ui_msg="  Skipping public site (no public_title)"
                    )

                # Initialize public data
                public_data = {}
                using_portal_fallback = False

                if not product_url and public_title:
                    log_warning(
                        status_fn,
                        msg="Product URL not found in public index, trying portal as fallback",
                        details=f"Public Title: {public_title}, Color: {first_color}"
                    )
                    using_portal_fallback = True
                    # Will try to collect portal data below and create product if found
                elif product_url:
                    # Collect public website data
                    public_data = collector.collect_public_data(product_url, status_fn)
                else:
                    # No public_title provided, skip public scraping
                    using_portal_fallback = True

                # Validate public data (skip validation if using portal fallback)
                is_valid, missing_critical, missing_important = DataValidator.validate_public_data(public_data)
                public_summary = DataValidator.get_public_data_summary(public_data)

                if not using_portal_fallback:
                    # Only validate if we expected to have public data
                    if not is_valid:
                        log_error(
                            status_fn,
                            msg="Public data validation failed - missing critical fields",
                            details=f"Public Title: {public_title}, Missing critical: {', '.join(missing_critical)}, Missing important: {', '.join(missing_important)}"
                        )
                        failures.append({
                            "title": portal_title,
                            "reason": "Public data validation failed",
                            "colors": [v.get("color", "") for v in variant_records],
                            "search_color": first_color,
                            "variant_count": len(variant_records),
                            "product_url": product_url,
                            "missing_critical_fields": missing_critical,
                            "missing_important_fields": missing_important,
                            "public_data_summary": public_summary
                        })
                        fail_count += 1
                        continue

                    # Warn if important fields are missing but continue processing
                    if missing_important:
                        log_warning(
                            status_fn,
                            msg="Public data is missing some important fields",
                            details=f"Public Title: {public_title}, Missing: {', '.join(missing_important)}"
                        )

                # Collect portal data for each variant to process
                portal_data_by_color = {}
                portal_warnings = []  # Track portal data issues

                # Get unique colors from variants_to_process in original order
                # Use list to preserve spreadsheet order instead of set
                colors_to_collect = []
                seen_colors = set()
                for v in variants_to_process:
                    color = v.get("color", "").strip()
                    if color and color not in seen_colors:
                        colors_to_collect.append(color)
                        seen_colors.add(color)

                for color in colors_to_collect:
                    log_and_status(
                        status_fn,
                        msg=f"  Collecting portal data for color: {color} (product: {portal_title})",
                        ui_msg=f"  Collecting portal data for color: {color}"
                    )

                    # Search portal using "[portal_title] [color]" (exact match)
                    # The portal index has title field that contains "[portal_title] [color]"
                    portal_data = collector.collect_portal_data(portal_title, color, status_fn)

                    # Validate portal data
                    has_data, missing_portal_fields = DataValidator.validate_portal_data(portal_data)
                    portal_summary = DataValidator.get_portal_data_summary(portal_data)

                    if has_data:
                        portal_data_by_color[color] = portal_data
                        variant_success_count += 1

                        # Warn if missing important fields
                        if missing_portal_fields:
                            warning_msg = f"Portal data for color '{color}' is missing: {', '.join(missing_portal_fields)}"
                            log_warning(
                                status_fn,
                                msg=warning_msg,
                                details=f"Portal Title: {portal_title}, Color: {color}"
                            )
                            portal_warnings.append({
                                "color": color,
                                "missing_fields": missing_portal_fields,
                                "summary": portal_summary
                            })
                    else:
                        variant_fail_count += 1
                        warning_msg = f"❌ Variant failed: No portal data found for color '{color}'"
                        log_warning(
                            status_fn,
                            msg=warning_msg,
                            details=f"Portal Title: {portal_title}, Color: {color}"
                        )
                        portal_warnings.append({
                            "color": color,
                            "missing_fields": DataValidator.PORTAL_IMPORTANT_FIELDS[:],
                            "summary": portal_summary
                        })

                # If using portal fallback and no portal data found, fail
                if using_portal_fallback and not portal_data_by_color:
                    log_error(
                        status_fn,
                        msg="Product not found in public index or portal",
                        details=f"Portal Title: {portal_title}, searched {len(variants_to_process)} variants in portal"
                    )
                    failures.append({
                        "title": portal_title,
                        "reason": "Product not found in public index or portal",
                        "colors": [v.get("color", "") for v in variants_to_process],
                        "search_color": first_color,
                        "variant_count": len(variants_to_process)
                    })
                    fail_count += 1
                    continue

                # If using portal fallback, track that public description is missing
                if using_portal_fallback:
                    log_warning(
                        status_fn,
                        msg="Product generated from portal data only (public site data unavailable)",
                        details=f"Portal Title: {portal_title}, missing public description, hero image, and gallery"
                    )

                # Generate Shopify product (only for variants_to_process)
                product = generator.generate_product(
                    title=portal_title,
                    variant_records=variants_to_process,
                    public_data=public_data,
                    portal_data_by_color=portal_data_by_color,
                    log=status_fn
                )

                # ALWAYS rebuild variants list in original spreadsheet order
                # This ensures variant order matches the input file regardless of mode

                # Create mapping from (color, unit) to generated variants
                generated_variants_map = {}
                for variant in product["variants"]:
                    color = variant.get("option1", "").strip()
                    unit = variant.get("option2", "").strip()
                    if color and unit:
                        generated_variants_map[(color, unit)] = variant

                # Create mapping from (color, unit) to existing variants (if any)
                existing_variants_map = {}
                existing_images = []
                if variants_to_skip and portal_title in existing_products:
                    existing_product = existing_products[portal_title]
                    existing_images = existing_product.get("images", [])
                    existing_variants_map = extract_existing_variants_by_color_unit(existing_product)

                # Rebuild variants list in original spreadsheet order
                ordered_variants = []
                skipped_colors = set()

                for variant_record in variant_records:
                    color = variant_record.get("color", "").strip()
                    if not color:
                        continue

                    unit = determine_variant_unit(variant_record)
                    if not unit:
                        # Record without unit determination - check if it was generated
                        # Find by color in generated variants
                        found = False
                        for gen_variant in product["variants"]:
                            if gen_variant.get("option1", "").strip() == color:
                                if gen_variant not in ordered_variants:
                                    ordered_variants.append(gen_variant)
                                    found = True
                                    break
                        if not found:
                            # Try existing variants
                            for (ex_color, ex_unit), ex_variant in existing_variants_map.items():
                                if ex_color == color and ex_variant not in ordered_variants:
                                    ordered_variants.append(ex_variant)
                                    skipped_colors.add(color)
                                    break
                        continue

                    variant_key = (color, unit)

                    # Use existing variant if this was skipped, otherwise use generated
                    if variant_key in variants_to_skip and variant_key in existing_variants_map:
                        ordered_variants.append(existing_variants_map[variant_key])
                        skipped_colors.add(color)
                    elif variant_key in generated_variants_map:
                        ordered_variants.append(generated_variants_map[variant_key])

                # Replace product variants with ordered list
                product["variants"] = ordered_variants

                # Merge images that are tagged for skipped colors (skip mode only)
                if variants_to_skip and existing_images:
                    for existing_image in existing_images:
                        image_alt = existing_image.get("alt", "")
                        # Check if image is tagged for a skipped color
                        for skipped_color in skipped_colors:
                            if f"Color [{skipped_color}]" in image_alt:
                                # Check if this image is not already in the product
                                image_src = existing_image.get("src", "")
                                if not any(img.get("src") == image_src for img in product["images"]):
                                    product["images"].append(existing_image)
                                break

                    log_and_status(
                        status_fn,
                        msg=f"  Merged {len(variants_to_skip)} existing variants in original order",
                        ui_msg=f"  Merged {len(variants_to_skip)} skipped variants"
                    )

                # Update dictionary and save incrementally
                products_dict[portal_title] = product
                success_count += 1

                # Save progress incrementally (preserves work if interrupted)
                try:
                    products_list = list(products_dict.values())
                    save_output_file(products_list, output_file, None)  # Don't log every save
                except Exception as e:
                    log_warning(
                        status_fn,
                        msg="Failed to save incremental progress",
                        details=f"Error: {str(e)}"
                    )

                # Track warnings
                if portal_warnings or using_portal_fallback:
                    # Include all colors (both processed and skipped)
                    all_colors = set()
                    all_colors.update([v.get("color", "") for v in variants_to_process])
                    all_colors.update([color for color, unit in variants_to_skip])

                    warning_entry = {
                        "title": portal_title,
                        "colors": sorted(list(all_colors)),
                        "variant_count": len(variants_to_process) + len(variants_to_skip),
                        "product_url": product_url if product_url else "N/A (portal only)",
                        "public_data_summary": public_summary
                    }

                    if using_portal_fallback:
                        warning_entry["reason"] = "Product generated from portal only (missing public description and images)"
                        warning_entry["missing_public_fields"] = ["description", "hero_image", "gallery_images", "specifications"]
                    elif portal_warnings:
                        warning_entry["reason"] = "Product generated with incomplete portal data"
                        warning_entry["portal_warnings"] = portal_warnings

                    warnings.append(warning_entry)

                # Build success message with warnings if present
                success_details = f"Portal Title: {portal_title}, Variants: {len(product['variants'])}, Images: {len(product['images'])}"

                warning_suffix = ""
                if using_portal_fallback:
                    warning_suffix = " (portal only - missing public data)"
                elif portal_warnings:
                    colors_with_issues = [w["color"] for w in portal_warnings]
                    success_details += f", Portal warnings for colors: {', '.join(colors_with_issues)}"
                    warning_suffix = " (with warnings)"

                log_success(
                    status_fn,
                    msg="Product generated successfully" + warning_suffix,
                    details=success_details
                )

            except Exception as e:
                log_error(
                    status_fn,
                    msg="Error processing product",
                    details=f"Portal Title: {portal_title}",
                    exc=e
                )
                failures.append({
                    "title": portal_title,
                    "reason": f"Exception during processing: {str(e)}",
                    "colors": [v.get("color", "") for v in variant_records],
                    "variant_count": len(variant_records),
                    "exception_type": type(e).__name__
                })
                fail_count += 1
                continue

        # Save output (final save with logging)
        log_and_status(status_fn, "", ui_msg="")
        log_section_header(status_fn, "SAVING OUTPUT")

        # Convert dictionary to list for final save
        products = list(products_dict.values())
        save_output_file(products, output_file, status_fn)

        # Save comprehensive report with failures and warnings
        if failures or warnings:
            report_file = output_file.replace(".json", "_report.json")
            try:
                report = {
                    "summary": {
                        "total_products": len(product_families),
                        "successful": success_count,
                        "skipped": skip_count,
                        "failed": fail_count,
                        "with_warnings": len(warnings),
                        "variant_stats": {
                            "successful_variants": variant_success_count,
                            "skipped_variants": variant_skip_count,
                            "failed_variants": variant_fail_count,
                            "total_variants": variant_success_count + variant_skip_count + variant_fail_count
                        }
                    },
                    "failures": failures,
                    "warnings": warnings
                }
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                log_and_status(
                    status_fn,
                    msg=f"Saved processing report: {len(failures)} failures, {len(warnings)} warnings",
                    ui_msg=f"Saved processing report ({len(failures)} failures, {len(warnings)} warnings)"
                )
            except Exception as e:
                log_warning(
                    status_fn,
                    msg="Failed to save report file",
                    details=f"File: {report_file}, Error: {str(e)}"
                )

        # Summary
        log_summary(
            status_fn,
            title="PROCESSING COMPLETE",
            stats={
                "✅ Successful Products": success_count,
                "⚠️  Products with Warnings": len(warnings),
                "⏭ Skipped Products": skip_count,
                "❌ Failed Products": fail_count,
                "Total Products": len(product_families),
                "": "",  # Separator
                "✅ Successful Variants": variant_success_count,
                "⏭ Skipped Variants": variant_skip_count,
                "❌ Failed Variants": variant_fail_count,
                "Total Variants": variant_success_count + variant_skip_count + variant_fail_count
            }
        )

    except Exception as e:
        log_error(
            status_fn,
            msg="Fatal error during processing",
            details="Main processing workflow encountered unrecoverable error",
            exc=e
        )
        raise

    finally:
        # Cleanup
        collector.close()
