#!/usr/bin/env python3
"""
Analyze Cambridge output file for missing data.

Generates a comprehensive report of products and variants with missing data,
including URLs for troubleshooting (extracted from log files).
"""

import json
import sys
import re
from collections import defaultdict
from datetime import datetime


def extract_urls_from_log(log_file):
    """
    Extract product and portal URLs from log file.

    Returns dict mapping product_title -> {
        'public_url': str,
        'portal_urls_by_color': {color: url}
    }
    """
    urls = defaultdict(lambda: {'public_url': None, 'portal_urls_by_color': {}})

    try:
        with open(log_file, 'r') as f:
            content = f.read()

        # Extract public URLs: "Fetching public page: https://..."
        public_url_pattern = r'\[(\d+)/\d+\] Processing: (.+?) \|.*?Fetching public page: (https://www\.cambridgepavers\.com[^\s]+)'
        for match in re.finditer(public_url_pattern, content, re.DOTALL):
            product_title = match.group(2).strip()
            public_url = match.group(3).strip()
            urls[product_title]['public_url'] = public_url

        # Extract portal URLs: "Collecting portal data for color: ... Fetching portal page: https://..."
        portal_url_pattern = r'Collecting portal data for color: (.+?) \(product: (.+?)\).*?Fetching portal page: (https://shop\.cambridgepavers\.com[^\s]+)'
        for match in re.finditer(portal_url_pattern, content, re.DOTALL):
            color = match.group(1).strip()
            product_title = match.group(2).strip()
            portal_url = match.group(3).strip()
            urls[product_title]['portal_urls_by_color'][color] = portal_url

    except FileNotFoundError:
        print(f"Warning: Log file not found: {log_file}")
    except Exception as e:
        print(f"Warning: Error reading log file: {e}")

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
        'variants_with_missing_weight': [],
        'variants_with_missing_cost': [],
        'variants_with_missing_model_number': [],
        'variants_with_missing_color_swatch': [],
    }

    # Analyze each product
    for product in products:
        product_title = product.get('title', 'Unknown Product')
        images = product.get('images', [])
        description = product.get('descriptionHtml', '')
        metafields = product.get('metafields', [])
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

            # Check for missing weight
            weight = variant.get('weight')
            if weight is None or weight == 0:
                missing_data['variants_with_missing_weight'].append({
                    'product': product_title,
                    'color': color,
                    'unit': unit,
                    'variant': variant_title,
                    'public_url': public_url or 'N/A',
                    'portal_url': portal_url or 'N/A',
                })

            # Check for missing cost
            cost = variant.get('cost')
            if cost is None or cost == '' or cost == '0':
                missing_data['variants_with_missing_cost'].append({
                    'product': product_title,
                    'color': color,
                    'unit': unit,
                    'variant': variant_title,
                    'public_url': public_url or 'N/A',
                    'portal_url': portal_url or 'N/A',
                })

            # Check for missing model number
            if not model_number or model_number == '':
                missing_data['variants_with_missing_model_number'].append({
                    'product': product_title,
                    'color': color,
                    'unit': unit,
                    'variant': variant_title,
                    'public_url': public_url or 'N/A',
                    'portal_url': portal_url or 'N/A',
                })

            # Check for missing color swatch
            if not color_swatch or color_swatch == '':
                missing_data['variants_with_missing_color_swatch'].append({
                    'product': product_title,
                    'color': color,
                    'unit': unit,
                    'variant': variant_title,
                    'public_url': public_url or 'N/A',
                    'portal_url': portal_url or 'N/A',
                })

    return missing_data, len(products)


def generate_report(missing_data, total_products, output_file):
    """Generate markdown report."""

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report = f"""# Cambridge Collector - Missing Data Report

**Generated**: {timestamp}
**Total Products Analyzed**: {total_products}

---

## Summary

| Category | Count |
|----------|-------|
| Products with Missing Images | {len(missing_data['products_with_missing_images'])} |
| Products with Missing Description | {len(missing_data['products_with_missing_description'])} |
| Variants with Missing Weight | {len(missing_data['variants_with_missing_weight'])} |
| Variants with Missing Cost | {len(missing_data['variants_with_missing_cost'])} |
| Variants with Missing Model Number | {len(missing_data['variants_with_missing_model_number'])} |
| Variants with Missing Color Swatch | {len(missing_data['variants_with_missing_color_swatch'])} |

---

## 1. Products with Missing Images

"""

    if missing_data['products_with_missing_images']:
        for item in missing_data['products_with_missing_images']:
            report += f"""### {item['product']}
- **Issue**: {item['issue']}
- **Public URL**: {item['public_url']}

"""
    else:
        report += "✅ **No products with missing images**\n\n"

    report += "---\n\n## 2. Products with Missing Description\n\n"

    if missing_data['products_with_missing_description']:
        for item in missing_data['products_with_missing_description']:
            report += f"""### {item['product']}
- **Issue**: {item['issue']}
- **Public URL**: {item['public_url']}

"""
    else:
        report += "✅ **No products with missing descriptions**\n\n"

    report += "---\n\n## 3. Variants with Missing Weight\n\n"

    if missing_data['variants_with_missing_weight']:
        # Group by product
        by_product = defaultdict(list)
        for item in missing_data['variants_with_missing_weight']:
            by_product[item['product']].append(item)

        for product, items in sorted(by_product.items()):
            report += f"### {product}\n\n"
            for item in items:
                report += f"""- **Color**: {item['color']} | **Unit**: {item['unit']}
  - Public URL: {item['public_url']}
  - Portal URL: {item['portal_url']}

"""
    else:
        report += "✅ **No variants with missing weight**\n\n"

    report += "---\n\n## 4. Variants with Missing Cost\n\n"

    if missing_data['variants_with_missing_cost']:
        # Group by product
        by_product = defaultdict(list)
        for item in missing_data['variants_with_missing_cost']:
            by_product[item['product']].append(item)

        for product, items in sorted(by_product.items()):
            report += f"### {product}\n\n"
            for item in items:
                report += f"""- **Color**: {item['color']} | **Unit**: {item['unit']}
  - Public URL: {item['public_url']}
  - Portal URL: {item['portal_url']}

"""
    else:
        report += "✅ **No variants with missing cost**\n\n"

    report += "---\n\n## 5. Variants with Missing Model Number\n\n"

    if missing_data['variants_with_missing_model_number']:
        # Group by product
        by_product = defaultdict(list)
        for item in missing_data['variants_with_missing_model_number']:
            by_product[item['product']].append(item)

        for product, items in sorted(by_product.items()):
            report += f"### {product}\n\n"
            for item in items:
                report += f"""- **Color**: {item['color']} | **Unit**: {item['unit']}
  - Public URL: {item['public_url']}
  - Portal URL: {item['portal_url']}

"""
    else:
        report += "✅ **No variants with missing model number**\n\n"

    report += "---\n\n## 6. Variants with Missing Color Swatch\n\n"

    if missing_data['variants_with_missing_color_swatch']:
        # Group by product
        by_product = defaultdict(list)
        for item in missing_data['variants_with_missing_color_swatch']:
            by_product[item['product']].append(item)

        for product, items in sorted(by_product.items()):
            report += f"### {product}\n\n"
            for item in items:
                report += f"""- **Color**: {item['color']} | **Unit**: {item['unit']}
  - Public URL: {item['public_url']}
  - Portal URL: {item['portal_url']}

"""
    else:
        report += "✅ **No variants with missing color swatch**\n\n"

    report += "---\n\n## Recommendations\n\n"
    report += """1. **Missing Images**: Check if product has gallery images on public website
2. **Missing Description**: Verify product page has description and specifications
3. **Missing Weight**: Verify portal page has "ITEM WEIGHT:" field with proper formatting
4. **Missing Cost**: Check if product has pricing on portal (may require authentication)
5. **Missing Model Number**: Verify portal page has SKU element with class "product-line-sku-value"
6. **Missing Color Swatch**: Check if portal has product image for this color variant

---

**Report generated by Cambridge Collector**
"""

    # Save report
    with open(output_file, 'w') as f:
        f.write(report)


def main():
    input_file = 'output/cambridge.json'
    log_file = 'logs/cambridge.log'  # Default log file
    output_file = 'output/missing_data_report.md'

    print("=" * 80)
    print("CAMBRIDGE COLLECTOR - MISSING DATA ANALYSIS")
    print("=" * 80)
    print()
    print(f"Analyzing: {input_file}")
    print(f"Extracting URLs from: {log_file}")
    print()

    missing_data, total_products = analyze_missing_data(input_file, log_file)

    # Print summary
    print("SUMMARY")
    print("-" * 80)
    print(f"Total Products Analyzed: {total_products}")
    print()
    print(f"Products with Missing Images: {len(missing_data['products_with_missing_images'])}")
    print(f"Products with Missing Description: {len(missing_data['products_with_missing_description'])}")
    print(f"Variants with Missing Weight: {len(missing_data['variants_with_missing_weight'])}")
    print(f"Variants with Missing Cost: {len(missing_data['variants_with_missing_cost'])}")
    print(f"Variants with Missing Model Number: {len(missing_data['variants_with_missing_model_number'])}")
    print(f"Variants with Missing Color Swatch: {len(missing_data['variants_with_missing_color_swatch'])}")
    print()

    # Generate detailed report
    generate_report(missing_data, total_products, output_file)

    print("=" * 80)
    print(f"✅ Report saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
