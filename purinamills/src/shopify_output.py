"""
Shopify Output Generator for Purinamills

Converts parsed product data into Shopify-compatible JSON format.
"""

import re
from typing import Dict, Any, List, Optional


def _clean_html(html: str) -> str:
    """Clean HTML for Shopify compatibility."""
    if not html:
        return ""
    # Remove data-start, data-end attributes
    html = re.sub(r'\s*data-(start|end)="[^"]*"', '', html)
    return html


def _generate_alt_tags(product_name: str, variant_options: Dict[str, str]) -> str:
    """
    Generate alt text with filter tags for images.

    Format: "Product Name #OPTION1#OPTION2#OPTION3"
    """
    tags = []

    # Add option tags (uppercase, replace spaces/hyphens with underscores)
    for key in ['size', 'material', 'option1', 'option2', 'option3']:
        value = variant_options.get(key, '')
        if value:
            tag = value.upper().replace(' ', '_').replace('-', '_').replace('&', '_')
            tags.append(f"#{tag}")

    tag_string = ''.join(tags)
    return f"{product_name} {tag_string}".strip()


def generate_shopify_product(
    parsed_data: Dict[str, Any],
    input_data: Dict[str, Any],
    log: callable = print
) -> Dict[str, Any]:
    """
    Generate Shopify product structure from parsed data.

    Args:
        parsed_data: Data extracted from website parser
        input_data: Original input product data
        log: Logging function

    Returns:
        Dictionary with Shopify product structure
    """

    # Extract basic info
    title = parsed_data.get('title', input_data.get('description_1', 'Unknown Product'))
    brand = parsed_data.get('brand_hint', 'Purina')
    description = _clean_html(parsed_data.get('description', ''))

    log(f"    - Title: {title}")
    log(f"    - Brand: {brand}")

    # Extract variants (sizes)
    source_variants = parsed_data.get('variants', [])

    # If no variants from parser, create one from input data
    if not source_variants:
        size = input_data.get('size', '')
        if size:
            source_variants = [{
                'size': size,
                'price': input_data.get('sold_ext_price_adj', input_data.get('avg_price_/_unit', '0'))
            }]
        else:
            source_variants = [{'size': 'Standard', 'price': '0'}]

    # Build Shopify variants
    shopify_variants = []
    variant_position = 1

    for var in source_variants:
        size = var.get('size', var.get('option_text', 'Standard'))
        material = var.get('material', 'BG')
        price = str(var.get('price', '0'))

        # Clean price (remove $ and commas)
        price = price.replace('$', '').replace(',', '')

        # Generate SKU from input data
        sku = input_data.get('upc', input_data.get('upc_updated', f"PUR-{variant_position:04d}"))

        variant = {
            "sku": sku,
            "price": price,
            "position": variant_position,
            "inventory_policy": "deny",
            "compare_at_price": None,
            "fulfillment_service": "manual",
            "inventory_management": "shopify",
            "option1": size,
            "option2": material,
            "taxable": True,
            "barcode": sku,
            "grams": 0,
            "weight": 0,
            "weight_unit": "lb",
            "inventory_quantity": int(input_data.get('inventory_qty', 0)),
            "requires_shipping": True,
            "metafields": [],
            "image_id": variant_position
        }

        # Add variant metafields

        # Model Number
        model_number = input_data.get('item_#', sku)
        if model_number:
            variant["metafields"].append({
                "namespace": "custom",
                "key": "model_number",
                "value": str(model_number),
                "type": "single_line_text_field"
            })

        # Size Info (if we have size data)
        if size and size != 'Standard':
            import json as json_lib
            size_info = {
                "label": size,
                "weight": size  # e.g., "50 LB"
            }
            variant["metafields"].append({
                "namespace": "custom",
                "key": "size_info",
                "value": json_lib.dumps(size_info),
                "type": "json"
            })

        shopify_variants.append(variant)
        variant_position += 1

    log(f"    - Created {len(shopify_variants)} variant(s)")

    # Build product options
    options = []

    # Option 1: Size
    sizes = list(set([v['option1'] for v in shopify_variants]))
    if sizes:
        options.append({
            "name": "Size",
            "position": 1,
            "values": sizes
        })

    # Option 2: Material/Package
    materials = list(set([v['option2'] for v in shopify_variants]))
    if materials and materials != ['BG']:
        options.append({
            "name": "Package",
            "position": 2,
            "values": materials
        })

    # Build images array
    images = []
    gallery_images = parsed_data.get('gallery_images', [])

    if gallery_images:
        log(f"    - Adding {len(gallery_images)} image(s)")
        for idx, img_url in enumerate(gallery_images, 1):
            # Generate alt text with filter tags
            alt_text = _generate_alt_tags(title, shopify_variants[0] if shopify_variants else {})

            images.append({
                "position": idx,
                "src": img_url,
                "alt": alt_text
            })

    # Build metafields (product-level)
    metafields = []

    # Features (from Features & Benefits section)
    features = parsed_data.get('features_benefits', '')
    if features:
        metafields.append({
            "namespace": "custom",
            "key": "features",
            "value": _clean_html(features),
            "type": "rich_text_field"
        })
        log(f"    - Added Features metafield")

    # Nutritional Information (from Nutrients/Guaranteed Analysis section)
    nutrients = parsed_data.get('nutrients', '')
    if nutrients:
        metafields.append({
            "namespace": "custom",
            "key": "nutritional_information",
            "value": _clean_html(nutrients),
            "type": "rich_text_field"
        })
        log(f"    - Added Nutritional Information metafield")

    # Directions (from Feeding Directions section)
    directions = parsed_data.get('feeding_directions', '')
    if directions:
        metafields.append({
            "namespace": "custom",
            "key": "directions",
            "value": _clean_html(directions),
            "type": "rich_text_field"
        })
        log(f"    - Added Directions metafield")

    # Documentation (from www site PDFs)
    documents = parsed_data.get('documents', [])
    if documents:
        import json
        metafields.append({
            "namespace": "custom",
            "key": "documentation",
            "value": json.dumps(documents),
            "type": "json"
        })
        log(f"    - Added Documentation metafield with {len(documents)} document(s)")

    # Build final Shopify product structure
    shopify_product = {
        "product": {
            "title": title,
            "body_html": description,
            "vendor": brand,
            "product_type": input_data.get('department', 'Feed'),
            "published": True,
            "options": options,
            "variants": shopify_variants,
            "images": images,
            "metafields": metafields
        }
    }

    # Add source site info for reference
    shopify_product["_metadata"] = {
        "source_site": parsed_data.get('site_source', 'unknown'),
        "source_upc": input_data.get('upc', input_data.get('upc_updated', '')),
        "source_item_number": input_data.get('item_#', ''),
        "parsed_at": "2025-11-04"  # Could use datetime.now()
    }

    return shopify_product


def merge_www_data(shop_product: Dict[str, Any], www_data: Dict[str, Any], log: callable = print) -> Dict[str, Any]:
    """
    Merge additional data from www site into shop product.

    Args:
        shop_product: Shopify product generated from shop site
        www_data: Parsed data from www site
        log: Logging function

    Returns:
        Updated Shopify product with merged data
    """
    product = shop_product.get('product', {})

    # Add documents if available
    documents = www_data.get('documents', [])
    if documents:
        import json

        # Check if documents metafield already exists
        existing_docs = None
        for mf in product.get('metafields', []):
            if mf.get('key') == 'documents':
                existing_docs = mf
                break

        if existing_docs:
            # Merge with existing
            try:
                existing_list = json.loads(existing_docs['value'])
                merged = existing_list + documents
                existing_docs['value'] = json.dumps(merged)
                log(f"    - Merged {len(documents)} additional document(s)")
            except:
                pass
        else:
            # Add new metafield
            product.setdefault('metafields', []).append({
                "namespace": "custom",
                "key": "documents",
                "value": json.dumps(documents),
                "type": "json"
            })
            log(f"    - Added {len(documents)} document(s) from www site")

    # If shop site was missing images, use www images
    if not product.get('images') and www_data.get('gallery_images'):
        log(f"    - Using {len(www_data['gallery_images'])} image(s) from www site")
        images = []
        for idx, img_url in enumerate(www_data['gallery_images'], 1):
            images.append({
                "position": idx,
                "src": img_url,
                "alt": product.get('title', 'Product')
            })
        product['images'] = images

    return shop_product
