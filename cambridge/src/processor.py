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

        # Load existing output if in skip mode
        existing_products = {}
        if processing_mode == "skip" and os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_products = {
                        p["title"]: p for p in existing_data.get("products", [])
                    }
                log_and_status(
                    status_fn,
                    msg=f"Loaded {len(existing_products)} existing products from {output_file} (skip mode enabled)",
                    ui_msg=f"Loaded {len(existing_products)} existing products (skip mode)"
                )
            except Exception as e:
                log_warning(
                    status_fn,
                    msg="Failed to load existing output",
                    details=f"File: {output_file}, Error: {str(e)}"
                )

        # Process each product family
        products = []
        failures = []  # Track failed products with details
        warnings = []  # Track products with warnings (missing portal data)
        success_count = 0
        skip_count = 0
        fail_count = 0

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

            # Skip if already processed
            if processing_mode == "skip" and portal_title in existing_products:
                log_and_status(
                    status_fn,
                    msg=f"[{i}/{len(product_families)}] Skipping: {portal_title} (already processed, skip mode enabled)",
                    ui_msg="  ⏭ Skipping (already processed)"
                )
                products.append(existing_products[portal_title])
                skip_count += 1
                continue

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

                # Collect portal data for each color variant
                portal_data_by_color = {}
                portal_warnings = []  # Track portal data issues

                for variant_record in variant_records:
                    color = variant_record.get("color", "").strip()
                    if not color:
                        continue

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
                        warning_msg = f"No portal data found for color '{color}'"
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
                        details=f"Portal Title: {portal_title}, searched {len(variant_records)} colors in portal"
                    )
                    failures.append({
                        "title": portal_title,
                        "reason": "Product not found in public index or portal",
                        "colors": [v.get("color", "") for v in variant_records],
                        "search_color": first_color,
                        "variant_count": len(variant_records)
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

                # Generate Shopify product
                product = generator.generate_product(
                    title=portal_title,
                    variant_records=variant_records,
                    public_data=public_data,
                    portal_data_by_color=portal_data_by_color,
                    log=status_fn
                )

                products.append(product)
                success_count += 1

                # Track warnings
                if portal_warnings or using_portal_fallback:
                    warning_entry = {
                        "title": portal_title,
                        "colors": [v.get("color", "") for v in variant_records],
                        "variant_count": len(variant_records),
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

        # Save output
        log_and_status(status_fn, "", ui_msg="")
        log_section_header(status_fn, "SAVING OUTPUT")

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
                        "with_warnings": len(warnings)
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
                "✅ Successful": success_count,
                "⚠️  With Warnings": len(warnings),
                "⏭ Skipped": skip_count,
                "❌ Failed": fail_count,
                "Total": len(product_families)
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
