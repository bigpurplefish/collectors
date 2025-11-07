"""
Shopify Output Generator for Purinamills

Converts parsed product data into Shopify-compatible JSON format.
"""

import re
from typing import Dict, Any, List, Optional


def _clean_html(html: str) -> str:
    """
    Clean HTML for Shopify compatibility.

    Removes problematic attributes and ensures HTML is safe for Shopify.
    Shopify supports standard HTML tags like <strong>, <i>, <ul>, <li>, <table>, etc.
    """
    if not html:
        return ""

    # Remove non-content tags (scripts, noscripts, images, svgs, buttons, divs used for layout)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<svg[^>]*>.*?</svg>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<button[^>]*>.*?</button>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<img[^>]*>', '', html, flags=re.IGNORECASE)

    # Remove video embeds (deferred-media, iframes, templates)
    # These are handled separately in the media array for GraphQL compatibility
    html = re.sub(r'<deferred-media[^>]*>.*?</deferred-media>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<template[^>]*>.*?</template>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove divs and spans but keep their content
    html = re.sub(r'</?div[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</?span[^>]*>', '', html, flags=re.IGNORECASE)

    # Remove role, aria-*, and other accessibility attributes
    html = re.sub(r'\s*role="[^"]*"', '', html)
    html = re.sub(r'\s*aria-[a-z-]+="[^"]*"', '', html)

    # Remove all data-* attributes (data-start, data-end, etc.)
    html = re.sub(r'\s*data-[a-z-]+="[^"]*"', '', html)

    # Remove other problematic attributes
    # Remove style attributes (Shopify themes handle styling)
    html = re.sub(r'\s*style="[^"]*"', '', html)

    # Remove class attributes that might conflict with theme
    html = re.sub(r'\s*class="[^"]*"', '', html)

    # Remove id attributes
    html = re.sub(r'\s*id="[^"]*"', '', html)

    # Remove sizes, srcset, loading attributes (from images we didn't catch)
    html = re.sub(r'\s*(sizes|srcset|loading|width|height|alt)="[^"]*"', '', html)

    # Remove onclick and other event handlers
    html = re.sub(r'\s*on[a-z]+="[^"]*"', '', html, flags=re.IGNORECASE)

    # Clean up any double spaces that might have been created
    html = re.sub(r'\s+', ' ', html)

    # Clean up space before closing tags
    html = re.sub(r'\s+>', '>', html)

    # Clean up empty tags that might be left over
    html = re.sub(r'<([a-z]+)>\s*</\1>', '', html, flags=re.IGNORECASE)

    return html.strip()


def _normalize_size(size_value: str) -> str:
    """
    Normalize size values to use proper capitalization.

    Rules:
    - Common units stay uppercase: LB, OZ, KG, G, ML, L, GAL
    - Other words use initial caps: Gallon, Pound, Each, Pack
    - Numbers stay as-is

    Examples:
        "50 LB" -> "50 LB"
        "2 GALLON" -> "2 Gallon"
        "16 OZ" -> "16 OZ"
        "EACH" -> "Each"
    """
    if not size_value:
        return ""

    # List of units that should remain uppercase
    uppercase_units = {
        'LB', 'LBS', 'OZ', 'KG', 'G', 'MG',
        'ML', 'L', 'GAL', 'QT', 'PT', 'FL',
        'CT', 'EA', 'PK', 'BX', 'CS'
    }

    # Split into words
    words = size_value.strip().split()
    normalized_words = []

    for word in words:
        # Check if it's a number (with or without decimals)
        if re.match(r'^\d+(\.\d+)?$', word):
            normalized_words.append(word)
        # Check if it's an uppercase unit that should stay uppercase
        elif word.upper() in uppercase_units:
            normalized_words.append(word.upper())
        # Check for mixed formats like "50LB" (number + unit together)
        elif re.match(r'^\d+[A-Z]+$', word, re.IGNORECASE):
            # Extract number and unit
            match = re.match(r'^(\d+)([A-Z]+)$', word, re.IGNORECASE)
            if match:
                number, unit = match.groups()
                if unit.upper() in uppercase_units:
                    normalized_words.append(f"{number} {unit.upper()}")
                else:
                    normalized_words.append(f"{number} {unit.capitalize()}")
        # Otherwise, use initial caps (title case)
        else:
            normalized_words.append(word.capitalize())

    return ' '.join(normalized_words)


def _format_body_html(html: str) -> str:
    """
    Format body_html with proper paragraph tags.

    Converts <br> tags into separate paragraphs and ensures all text is wrapped in <p> tags.
    """
    if not html:
        return ""

    # First clean the HTML
    html = _clean_html(html)

    if not html:
        return ""

    # Check if content already has paragraph tags
    has_p_tags = bool(re.search(r'<p[^>]*>', html, re.IGNORECASE))

    if has_p_tags:
        # Already has paragraphs, just convert any remaining <br> to paragraph breaks
        # Split on <br> tags and wrap each segment in <p> if not already wrapped
        parts = re.split(r'<br\s*/?>', html, flags=re.IGNORECASE)
        formatted_parts = []

        for part in parts:
            part = part.strip()
            if part:
                # If this part doesn't start with a tag, wrap it
                if not part.startswith('<'):
                    formatted_parts.append(f'<p>{part}</p>')
                else:
                    formatted_parts.append(part)

        return ''.join(formatted_parts)
    else:
        # No paragraph tags, split on <br> and wrap each in <p>
        parts = re.split(r'<br\s*/?>', html, flags=re.IGNORECASE)
        formatted_parts = []

        for part in parts:
            part = part.strip()
            if part:
                formatted_parts.append(f'<p>{part}</p>')

        return ''.join(formatted_parts) if formatted_parts else f'<p>{html}</p>'


def _generate_alt_tags(product_name: str, variant_options: Dict[str, str]) -> str:
    """
    Generate alt text with filter tags for images.

    Format: "Product Name #OPTION1#OPTION2#OPTION3"
    Skips common unit values like "EA", "Each", None, etc.
    """
    tags = []

    # Common values to skip (not meaningful differentiators)
    skip_values = {'ea', 'each', 'none', '', 'null'}

    # Add option tags (uppercase, replace spaces/hyphens with underscores)
    for key in ['size', 'material', 'option1', 'option2', 'option3']:
        value = variant_options.get(key, '')
        if value and str(value).lower() not in skip_values:
            tag = str(value).upper().replace(' ', '_').replace('-', '_').replace('&', '_')
            tags.append(f"#{tag}")

    tag_string = ''.join(tags)
    return f"{product_name} {tag_string}".strip()


def generate_shopify_product(
    parsed_data: Dict[str, Any],
    input_data: Dict[str, Any],
    variant_data: List[Dict[str, Any]] = None,
    log: callable = print
) -> Dict[str, Any]:
    """
    Generate Shopify product structure from parsed data.

    Args:
        parsed_data: Data extracted from website parser
        input_data: Parent product data from input file
        variant_data: List of variant products from input file (empty for single products)
        log: Logging function

    Returns:
        Dictionary with Shopify product structure
    """
    import json as json_lib

    # Extract basic info
    title = parsed_data.get('title', input_data.get('description_1', 'Unknown Product'))
    brand = parsed_data.get('brand_hint', 'Purina')
    description = _format_body_html(parsed_data.get('description', ''))

    log(f"    - Title: {title}")
    log(f"    - Brand: {brand}")

    # Build variants from input file structure
    # Combine parent + variant_data into all_variant_records
    if variant_data is None:
        variant_data = []

    all_variant_records = [input_data] + variant_data  # Parent is first variant

    # Determine option fields from parent
    option_1_field = input_data.get('option_1', '').strip()
    option_2_field = input_data.get('option_2', '').strip()
    option_3_field = input_data.get('option_3', '').strip()
    option_4_field = input_data.get('option_4', '').strip()

    # If no options are defined but product has size, use size as option_1
    # This ensures size information is prominently displayed even for single-variant products
    if not option_1_field and not option_2_field and not option_3_field and not option_4_field:
        if input_data.get('size'):
            option_1_field = 'size'
            log(f"    - No explicit options found, using 'size' as option_1")

    log(f"    - Generating {len(all_variant_records)} variant(s)")
    if option_1_field:
        log(f"    - Option 1: {option_1_field}")
    if option_2_field:
        log(f"    - Option 2: {option_2_field}")
    if option_3_field:
        log(f"    - Option 3: {option_3_field}")
    if option_4_field:
        log(f"    - Option 4: {option_4_field}")

    # Build Shopify variants
    shopify_variants = []

    # Get variant-image mapping data if available
    images_data = parsed_data.get('images_data', {})
    variant_image_map = images_data.get('variant_image_map', {})

    for variant_position, variant_record in enumerate(all_variant_records, 1):
        # Get option values from the fields specified in option_1-4
        option1_value = variant_record.get(option_1_field, '') if option_1_field else ''
        option2_value = variant_record.get(option_2_field, '') if option_2_field else ''
        option3_value = variant_record.get(option_3_field, '') if option_3_field else ''
        option4_value = variant_record.get(option_4_field, '') if option_4_field else ''

        # Normalize size values for consistent capitalization
        if option_1_field == 'size' and option1_value:
            option1_value = _normalize_size(str(option1_value))
        if option_2_field == 'size' and option2_value:
            option2_value = _normalize_size(str(option2_value))
        if option_3_field == 'size' and option3_value:
            option3_value = _normalize_size(str(option3_value))
        if option_4_field == 'size' and option4_value:
            option4_value = _normalize_size(str(option4_value))

        # Get price
        price = str(variant_record.get('sold_ext_price_adj', variant_record.get('avg_price_/_unit', '0')))
        price = price.replace('$', '').replace(',', '')

        # Get cost (maps to inventoryItem.cost in Shopify)
        cost = str(variant_record.get('sold_ext_cost_adj', ''))
        cost = cost.replace('$', '').replace(',', '') if cost else None

        # Get SKU and barcode
        # item_# → sku
        # sku field from input → barcode
        sku = variant_record.get('item_#', f"PUR-{variant_position:04d}")
        barcode = variant_record.get('sku', variant_record.get('upc', variant_record.get('upc_updated', '')))

        # Determine correct image_id for this variant
        image_id = variant_position  # Default: use variant position

        if variant_image_map:
            # Build variant key from options (matching parser format)
            # Try multiple key patterns since shop site may have different option structure
            # than our input file (e.g., shop has "EA" as option2, input file might not)

            possible_keys = [
                f"{option1_value}|{option2_value}|{option3_value}".strip('|'),
                f"{option1_value}||".strip('|'),  # Just option1
                f"{option1_value}",  # Just option1 without pipes
            ]

            # Also try with "EA" as option2 (common in shop site)
            if option1_value and not option2_value:
                possible_keys.append(f"{option1_value}|EA|None")
                possible_keys.append(f"{option1_value}|EA|")
                possible_keys.append(f"{option1_value}|EA")

            # Look up image position for this variant (case-insensitive matching)
            variant_img_info = None

            # Create lowercase map for case-insensitive lookup
            variant_image_map_lower = {k.lower(): v for k, v in variant_image_map.items()}

            for key in possible_keys:
                key_lower = key.lower()
                if key_lower in variant_image_map_lower:
                    variant_img_info = variant_image_map_lower[key_lower]
                    break

            if variant_img_info:
                image_id = variant_img_info.get('position', variant_position)

        # Build variant (only include option fields that are actually used)
        variant = {
            "sku": str(sku),
            "price": price,
            "position": variant_position,
            "inventory_policy": "deny",
            "compare_at_price": None,
            "fulfillment_service": "manual",
            "inventory_management": "shopify",
            "taxable": True,
            "barcode": barcode,
            "grams": 0,
            "weight": 0,
            "weight_unit": "lb",
            "inventory_quantity": int(variant_record.get('inventory_qty', 0)),
            "requires_shipping": True,
            "metafields": [],
            "image_id": image_id
        }

        # Only add option fields if they have values
        if option1_value:
            variant["option1"] = option1_value
        if option2_value:
            variant["option2"] = option2_value
        if option3_value:
            variant["option3"] = option3_value
        if option4_value:
            variant["option4"] = option4_value

        # Add cost if available (for Shopify's inventoryItem.cost field)
        if cost:
            variant["cost"] = cost

        # Add variant metafields

        # Model Number (only from scraped content, not from input file)
        # Check if parsed_data has model_number for this variant
        model_number = parsed_data.get('model_number')  # Will be None if not scraped
        if model_number:
            variant["metafields"].append({
                "namespace": "custom",
                "key": "model_number",
                "value": str(model_number),
                "type": "single_line_text_field"
            })

        # Size Info (if we have size data from option_1)
        if option1_value and option_1_field == 'size':
            size_info = {
                "label": option1_value,
                "weight": option1_value  # e.g., "50 LB"
            }
            variant["metafields"].append({
                "namespace": "custom",
                "key": "size_info",
                "value": json_lib.dumps(size_info),
                "type": "json"
            })

        shopify_variants.append(variant)

    log(f"    - Created {len(shopify_variants)} variant(s)")

    # Build product options based on option_1-4 fields
    options = []

    # Option 1
    if option_1_field:
        values = list(set([v['option1'] for v in shopify_variants if v.get('option1')]))
        if values:
            # Capitalize field name for display
            option_name = option_1_field.replace('_', ' ').title()
            options.append({
                "name": option_name,
                "position": 1,
                "values": values
            })

    # Option 2
    if option_2_field:
        values = list(set([v['option2'] for v in shopify_variants if v.get('option2')]))
        if values:
            option_name = option_2_field.replace('_', ' ').title()
            options.append({
                "name": option_name,
                "position": 2,
                "values": values
            })

    # Option 3
    if option_3_field:
        values = list(set([v['option3'] for v in shopify_variants if v.get('option3')]))
        if values:
            option_name = option_3_field.replace('_', ' ').title()
            options.append({
                "name": option_name,
                "position": 3,
                "values": values
            })

    # Option 4
    if option_4_field:
        values = list(set([v['option4'] for v in shopify_variants if v.get('option4')]))
        if values:
            option_name = option_4_field.replace('_', ' ').title()
            options.append({
                "name": option_name,
                "position": 4,
                "values": values
            })

    # Build images array with variant-specific alt tags
    images = []
    images_data = parsed_data.get('images_data', {})

    if images_data and images_data.get('images'):
        # Use variant-image mapping data from parser
        variant_image_map = images_data.get('variant_image_map', {})

        log(f"    - Adding {len(images_data['images'])} image(s) with variant mapping")

        for img_data in images_data['images']:
            media_type = img_data.get('media_type', 'image')

            # Skip videos - they go in the media array, not images array
            if media_type in ['external_video', 'video']:
                continue

            position = img_data.get('position', 0)
            src = img_data.get('src', '')
            variant_keys = img_data.get('variant_keys', [])

            # Determine which variants use this image
            if variant_keys:
                # Variant-specific image - create one entry with variant filter tags
                first_variant_key = variant_keys[0]
                variant_info = variant_image_map.get(first_variant_key, {})
                variant_options = variant_info.get('options', {})

                # Generate alt text with filter tags
                alt_text = _generate_alt_tags(title, variant_options)

                images.append({
                    "position": position,
                    "src": src,
                    "alt": alt_text
                })
            else:
                # Shared image - create one entry for EACH variant with that variant's tags
                for variant in shopify_variants:
                    variant_options = {
                        'option1': variant.get('option1', ''),
                        'option2': variant.get('option2', ''),
                        'option3': variant.get('option3', ''),
                    }

                    # Generate alt text with this variant's filter tags
                    alt_text = _generate_alt_tags(title, variant_options)

                    images.append({
                        "position": position,
                        "src": src,
                        "alt": alt_text
                    })
    else:
        # Fallback: use legacy gallery_images field
        gallery_images = parsed_data.get('gallery_images', [])

        if gallery_images:
            log(f"    - Adding {len(gallery_images)} image(s) (legacy mode)")
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

    # Separate videos from images (videos require GraphQL, can't be imported via JSON)
    video_media = []
    if images_data and images_data.get('images'):
        for img_data in images_data['images']:
            media_type = img_data.get('media_type', 'image')
            if media_type in ['external_video', 'video']:
                # Extract video data for GraphQL upload
                position = img_data.get('position', 0)
                variant_keys = img_data.get('variant_keys', [])

                video_entry = {
                    'position': position,
                    'media_type': media_type,
                    'alt': img_data.get('alt', ''),
                }

                if media_type == 'external_video':
                    video_entry['host'] = img_data.get('host', '')
                    video_entry['external_id'] = img_data.get('external_id', '')
                    video_entry['src'] = img_data.get('src', '')
                elif media_type == 'video':
                    video_entry['sources'] = img_data.get('sources', [])

                # Add variant associations (for shared videos, duplicate per variant)
                if variant_keys:
                    # Video is variant-specific
                    video_entry['variant_options'] = []
                    for variant_key in variant_keys:
                        variant_info = variant_image_map.get(variant_key, {})
                        if variant_info:
                            video_entry['variant_options'].append(variant_info.get('options', {}))
                else:
                    # Shared video - associate with all variants
                    video_entry['variant_options'] = [
                        {
                            'option1': v.get('option1', ''),
                            'option2': v.get('option2', ''),
                            'option3': v.get('option3', ''),
                        }
                        for v in shopify_variants
                    ]

                video_media.append(video_entry)

    # Build media array for GraphQL (videos go here, not in images array)
    # Videos must be uploaded using productCreateMedia mutation after product creation
    media = []
    if video_media:
        for video in video_media:
            media_type = video.get('media_type')

            if media_type == 'external_video':
                # External video (YouTube, Vimeo, etc.)
                media_entry = {
                    "alt": video.get('alt', ''),
                    "media_content_type": "EXTERNAL_VIDEO",
                    "original_source": video.get('src', ''),
                    "host": video.get('host', '').upper(),  # YOUTUBE, VIMEO
                    "external_id": video.get('external_id', '')
                }
            elif media_type == 'video':
                # Hosted video
                sources = video.get('sources', [])
                if sources:
                    media_entry = {
                        "alt": video.get('alt', ''),
                        "media_content_type": "VIDEO",
                        "original_source": sources[0].get('url', '')
                    }

            # Add variant associations if present
            if 'variant_options' in video:
                media_entry['variant_options'] = video['variant_options']

            media.append(media_entry)

        log(f"    - Added {len(media)} video(s) to media array for GraphQL upload")

    # Build final Shopify product structure (GraphQL API 2025-10 compatible format)
    shopify_product = {
        "product": {
            "title": title,
            "descriptionHtml": description,  # GraphQL uses descriptionHtml instead of body_html
            "vendor": brand,
            "status": "ACTIVE",  # GraphQL uses status (ACTIVE/DRAFT/ARCHIVED) instead of published boolean
            "options": options,
            "variants": shopify_variants,
            "images": images,
            "metafields": metafields
        }
    }

    # Add media array if we have videos
    # NOTE: Videos require GraphQL API and must be uploaded using productCreateMedia mutation
    # after product creation, then associated with variants using productVariantAppendMedia
    if media:
        shopify_product['product']['media'] = media

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
