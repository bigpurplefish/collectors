#!/usr/bin/env python3
"""
Generate Comprehensive Report for Cambridge Collector

Combines:
1. Failed products (from failures JSON file)
2. Successful products with missing data (from output JSON file)

Generates a complete markdown report showing both failures and data quality issues.
"""

import json
import sys
import re
from collections import defaultdict
from datetime import datetime


def load_failures(failures_file):
    """Load failures from JSON file."""
    try:
        with open(failures_file, 'r') as f:
            data = json.load(f)
        return data.get('failures', [])
    except FileNotFoundError:
        print(f"⚠️  No failures file found: {failures_file}")
        return []
    except Exception as e:
        print(f"⚠️  Error reading failures file: {e}")
        return []


def extract_urls_from_log(log_file):
    """
    Extract product and portal URLs from log file (line-by-line for efficiency).

    Returns dict mapping product_title -> {
        'public_url': str,
        'portal_urls_by_color': {color: url}
    }
    """
    urls = defaultdict(lambda: {'public_url': None, 'portal_urls_by_color': {}})

    try:
        current_product = None
        current_color = None

        with open(log_file, 'r') as f:
            for line in f:
                # Extract product title from processing line
                processing_match = re.search(r'\[(\d+)/\d+\] Processing: (.+?) \|', line)
                if processing_match:
                    current_product = processing_match.group(2).strip()

                # Extract public URL
                if 'Fetching public page:' in line and current_product:
                    public_match = re.search(r'Fetching public page: (https://www\.cambridgepavers\.com[^\s]+)', line)
                    if public_match:
                        urls[current_product]['public_url'] = public_match.group(1).strip()

                # Extract color being processed
                color_match = re.search(r'Collecting portal data for color: (.+?) \(product: (.+?)\)', line)
                if color_match:
                    current_color = color_match.group(1).strip()
                    current_product = color_match.group(2).strip()

                # Extract portal URL for current color
                if 'Fetching portal page:' in line and current_product and current_color:
                    portal_match = re.search(r'Fetching portal page: (https://shop\.cambridgepavers\.com[^\s]+)', line)
                    if portal_match:
                        urls[current_product]['portal_urls_by_color'][current_color] = portal_match.group(1).strip()
                        current_color = None  # Reset after capturing

    except FileNotFoundError:
        print(f"⚠️  Log file not found: {log_file}")
    except Exception as e:
        print(f"⚠️  Error reading log file: {e}")

    return urls


def analyze_missing_data(output_file, log_file):
    """Analyze output file for missing data."""

    with open(output_file, 'r') as f:
        data = json.load(f)

    products = data.get('products', [])

    # Extract URLs from log file
    url_data = extract_urls_from_log(log_file)

    # Track missing data by category
    missing_data = {
        'products_with_missing_images': [],
        'products_with_missing_description': [],
        'variants_with_missing_data': [],  # Consolidated variant tracking
    }

    # Track counts by field type for summary
    field_counts = {
        'weight': 0,
        'cost': 0,
        'model_number': 0,
        'color_swatch': 0
    }

    # Analyze each product
    for product in products:
        product_title = product.get('title', 'Unknown Product')
        images = product.get('images', [])
        description = product.get('descriptionHtml', '')
        variants = product.get('variants', [])

        # Get product URLs from log file data
        product_url_info = url_data.get(product_title, {})
        public_url = product_url_info.get('public_url', 'N/A')
        portal_urls_by_color = product_url_info.get('portal_urls_by_color', {})

        # Check for missing images
        if not images or len(images) == 0:
            missing_data['products_with_missing_images'].append({
                'product': product_title,
                'public_url': public_url or 'N/A',
                'issue': 'No product images'
            })

        # Check for missing description
        if not description or description.strip() == '':
            missing_data['products_with_missing_description'].append({
                'product': product_title,
                'public_url': public_url or 'N/A',
                'issue': 'No product description'
            })

        # Analyze variants
        for variant in variants:
            color = variant.get('option1', 'Unknown Color')
            unit = variant.get('option2', 'Unknown Unit')
            sku = variant.get('sku', 'N/A')
            variant_title = f"{product_title} - {color} ({unit})"

            # Get variant URLs from log file data
            portal_url = portal_urls_by_color.get(color, 'N/A')

            # Get metafield values
            color_swatch = None
            model_number = None

            variant_metafields = variant.get('metafields', [])
            for mf in variant_metafields:
                key = mf.get('key')
                if key == 'color_swatch_image':
                    color_swatch = mf.get('value', '')
                elif key == 'model_number':
                    model_number = mf.get('value', '')

            # Collect all missing data for this variant
            missing_fields = []

            # Check for missing weight
            weight = variant.get('weight')
            if weight is None or weight == 0:
                missing_fields.append('weight')

            # Check for missing cost
            cost = variant.get('cost')
            if cost is None or cost == '' or cost == '0':
                missing_fields.append('cost')

            # Check for missing model number
            if not model_number or model_number == '':
                missing_fields.append('model_number')

            # Check for missing color swatch
            if not color_swatch or color_swatch == '':
                missing_fields.append('color_swatch')

            # Add variant if it has any missing fields
            if missing_fields:
                variant_info = {
                    'product': product_title,
                    'color': color,
                    'unit': unit,
                    'sku': sku,
                    'variant': variant_title,
                    'public_url': public_url or 'N/A',
                    'portal_url': portal_url or 'N/A',
                    'missing_fields': missing_fields,
                    'weight': weight,
                    'cost': cost,
                    'model_number': model_number or 'N/A',
                    'color_swatch': color_swatch or 'N/A'
                }
                missing_data['variants_with_missing_data'].append(variant_info)

                # Update field counts for summary
                for field in missing_fields:
                    field_counts[field] += 1

    return missing_data, len(products), field_counts


def generate_comprehensive_report(failures, missing_data, total_products, field_counts, output_file):
    """Generate comprehensive markdown report including failures and missing data."""

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report = f"""# Cambridge Collector - Comprehensive Processing Report

**Generated**: {timestamp}
**Total Products Attempted**: {total_products + len(failures)}
**Successfully Processed**: {total_products}
**Failed to Process**: {len(failures)}

---

## Summary

### Processing Results

| Status | Count |
|--------|-------|
| ✅ Successfully Processed | {total_products} |
| ❌ Failed to Process | {len(failures)} |
| **Total Products** | **{total_products + len(failures)}** |

### Data Quality Issues (Successful Products Only)

| Category | Count |
|----------|-------|
| Products with Missing Images | {len(missing_data['products_with_missing_images'])} |
| Products with Missing Description | {len(missing_data['products_with_missing_description'])} |
| **Variants with Missing Data** | **{len(missing_data['variants_with_missing_data'])}** |

### Missing Data by Field Type

| Field | Variants Affected |
|-------|-------------------|
| Missing Weight | {field_counts['weight']} |
| Missing Cost | {field_counts['cost']} |
| Missing Model Number | {field_counts['model_number']} |
| Missing Color Swatch | {field_counts['color_swatch']} |

---

## SECTION 1: FAILED PRODUCTS

These products failed to process and were NOT included in the output file.

"""

    if failures:
        # Group failures by reason
        by_reason = defaultdict(list)
        for failure in failures:
            reason = failure.get('reason', 'Unknown reason')
            by_reason[reason].append(failure)

        for reason, items in sorted(by_reason.items()):
            report += f"### Failure Reason: {reason}\n\n"
            report += f"**Count**: {len(items)} products\n\n"

            for item in items:
                title = item.get('title', 'Unknown')
                colors = item.get('colors', [])
                variant_count = item.get('variant_count', 0)
                product_url = item.get('product_url', 'N/A')
                search_color = item.get('search_color', 'N/A')
                exception_type = item.get('exception_type', '')

                report += f"#### {title}\n\n"
                report += f"- **Variant Count**: {variant_count}\n"
                report += f"- **Colors**: {', '.join(colors) if colors else 'N/A'}\n"

                if search_color != 'N/A':
                    report += f"- **Search Color**: {search_color}\n"

                if product_url != 'N/A':
                    report += f"- **Public URL**: {product_url}\n"

                if exception_type:
                    report += f"- **Exception Type**: {exception_type}\n"

                report += "\n"

            report += "---\n\n"
    else:
        report += "✅ **No products failed to process**\n\n---\n\n"

    report += """
## SECTION 2: DATA QUALITY ISSUES

These products were successfully processed but have missing data fields.

---

### 2.1. Products with Missing Images

"""

    if missing_data['products_with_missing_images']:
        for item in missing_data['products_with_missing_images']:
            report += f"""#### {item['product']}
- **Issue**: {item['issue']}
- **Public URL**: {item['public_url']}

"""
    else:
        report += "✅ **No products with missing images**\n\n"

    report += "---\n\n### 2.2. Products with Missing Description\n\n"

    if missing_data['products_with_missing_description']:
        for item in missing_data['products_with_missing_description']:
            report += f"""#### {item['product']}
- **Issue**: {item['issue']}
- **Public URL**: {item['public_url']}

"""
    else:
        report += "✅ **No products with missing descriptions**\n\n"

    report += "---\n\n### 2.3. Variants with Missing Data\n\n"

    if missing_data['variants_with_missing_data']:
        # Group by product
        by_product = defaultdict(list)
        for item in missing_data['variants_with_missing_data']:
            by_product[item['product']].append(item)

        for product, items in sorted(by_product.items()):
            report += f"#### {product}\n\n"
            report += f"**Total variants with missing data**: {len(items)}\n\n"
            for idx, item in enumerate(items, 1):
                all_missing = ', '.join(item['missing_fields'])
                report += f"""##### Variant {idx}: {item['color']} - {item['unit']}

- **SKU**: `{item['sku']}`
- **Color**: {item['color']}
- **Unit of Sale**: {item['unit']}
- **Missing Fields**: `{all_missing}`
"""
                # Show current values for missing fields
                if 'weight' in item['missing_fields']:
                    report += f"- **Weight**: {item['weight']} (missing or zero)\n"
                if 'cost' in item['missing_fields']:
                    report += f"- **Cost**: {item['cost']} (missing or zero)\n"
                if 'model_number' in item['missing_fields']:
                    report += f"- **Model Number**: {item['model_number']} (missing)\n"
                if 'color_swatch' in item['missing_fields']:
                    report += f"- **Color Swatch**: {item['color_swatch']} (missing)\n"

                report += f"""- **Public URL**: {item['public_url']}
- **Portal URL**: {item['portal_url']}

"""
    else:
        report += "✅ **No variants with missing data**\n\n"

    report += """---

## Troubleshooting Recommendations

### For Failed Products:
1. **Product URL not found in public index**:
   - Product may not exist on www.cambridgepavers.com
   - Product title may not match (try searching manually)
   - Product may be discontinued or not yet published
   - Consider rebuilding the product index: `python3 scripts/build_index.py`

2. **Failed to collect public website data**:
   - Check if the URL is accessible
   - Website structure may have changed (update public_parser.py)
   - Network connectivity issues

3. **Exception during processing**:
   - Check the exception type and stack trace in logs
   - May indicate data format issues or code bugs
   - Review the full error in logs/cambridge.log

### For Data Quality Issues:
1. **Missing Images**: Check if product has gallery images on public website
2. **Missing Description**: Verify product page has description and specifications
3. **Missing Weight**: Verify portal page has "ITEM WEIGHT:" field with proper formatting
4. **Missing Cost**: Check if product has pricing on portal (may require authentication)
5. **Missing Model Number**: Verify portal page has SKU element with class "product-line-sku-value"
6. **Missing Color Swatch**: Check if portal has product image for this color variant

---

**Report generated by Cambridge Collector**
**For detailed logs, see: logs/cambridge.log**
"""

    # Save report
    with open(output_file, 'w') as f:
        f.write(report)


def main():
    output_file = 'output/cambridge.json'
    failures_file = 'output/cambridge_failures.json'
    log_file = 'logs/cambridge.log'
    report_file = 'output/comprehensive_report.md'

    print("=" * 80)
    print("CAMBRIDGE COLLECTOR - COMPREHENSIVE REPORT GENERATOR")
    print("=" * 80)
    print()
    print(f"Analyzing successful products: {output_file}")
    print(f"Analyzing failed products: {failures_file}")
    print(f"Extracting URLs from: {log_file}")
    print()

    # Load failures
    failures = load_failures(failures_file)

    # Analyze successful products
    missing_data, total_products, field_counts = analyze_missing_data(output_file, log_file)

    # Print summary
    print("SUMMARY")
    print("-" * 80)
    print(f"Total Products Attempted: {total_products + len(failures)}")
    print(f"Successfully Processed: {total_products}")
    print(f"Failed to Process: {len(failures)}")
    print()
    print("Data Quality Issues:")
    print(f"  - Products with Missing Images: {len(missing_data['products_with_missing_images'])}")
    print(f"  - Products with Missing Description: {len(missing_data['products_with_missing_description'])}")
    print(f"  - Variants with Missing Data: {len(missing_data['variants_with_missing_data'])}")
    print()
    print("Missing Data by Field:")
    print(f"  - Missing Weight: {field_counts['weight']} variants")
    print(f"  - Missing Cost: {field_counts['cost']} variants")
    print(f"  - Missing Model Number: {field_counts['model_number']} variants")
    print(f"  - Missing Color Swatch: {field_counts['color_swatch']} variants")
    print()

    # Generate comprehensive report
    generate_comprehensive_report(failures, missing_data, total_products, field_counts, report_file)

    print("=" * 80)
    print(f"✅ Comprehensive report saved to: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
