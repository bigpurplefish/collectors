"""
Product Generator for Cambridge Collector

Handles:
- Grouping input records by title (variant families)
- Generating Shopify GraphQL-compatible products
- Image ordering with proper alt tags for Shopify variant filtering
- Metafields creation
- SKU generation for products without SKUs
- Weight/unit_of_sale as standard fields and variant options

Implements dual logging pattern from LOGGING_REQUIREMENTS.md.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict

# Add parent collectors directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from utils.sku_generator import SKUGenerator
from utils.image_utils import (
    strip_querystring,
    deduplicate_images,
    generate_variant_alt_tag,
    generate_lifestyle_alt_tag,
    clean_and_verify_image_url
)
from utils.logging_utils import log_and_status


class CambridgeProductGenerator:
    """Generates Shopify products from collected Cambridge data."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize product generator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.sku_generator = SKUGenerator()

    def group_by_title(
        self,
        records: List[Dict[str, Any]],
        status_fn: Optional[Callable] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group input records by title.

        Records with the same title are color variants of one product.

        Args:
            records: List of input records
            status_fn: Status callback function

        Returns:
            Dictionary mapping title -> list of variant records
        """
        grouped = defaultdict(list)

        for record in records:
            title = record.get("title", "").strip()
            if title:
                grouped[title].append(record)

        log_and_status(
            status_fn,
            msg=f"Grouped {len(records)} records into {len(grouped)} product families (variant grouping by title)",
            ui_msg=f"Grouped {len(records)} records into {len(grouped)} product families"
        )

        return dict(grouped)

    def generate_product(
        self,
        title: str,
        variant_records: List[Dict[str, Any]],
        public_data: Dict[str, Any],
        portal_data_by_color: Dict[str, Dict[str, Any]],
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Generate Shopify product from collected data.

        Args:
            title: Product title
            variant_records: List of variant records (one per color)
            public_data: Data from public website (shared across variants)
            portal_data_by_color: Portal data indexed by color
            log: Logging function

        Returns:
            Shopify product dictionary (GraphQL 2025-10 format)
        """
        # Generate product structure
        product = {
            "title": title,
            "descriptionHtml": self._generate_description_html(public_data),
            "vendor": "Cambridge Pavers",
            "status": "ACTIVE",
            "options": self._generate_options(variant_records, portal_data_by_color),
            "metafields": self._generate_metafields(public_data),
            "variants": self._generate_variants(variant_records, portal_data_by_color, title),
            "images": self._generate_images(public_data, portal_data_by_color, title, variant_records),
        }

        return product

    def _generate_description_html(self, public_data: Dict[str, Any]) -> str:
        """
        Generate HTML description from public data.

        Appends specifications as a bulleted list if available.

        Args:
            public_data: Public website data

        Returns:
            HTML description string
        """
        html_parts = []

        # Main description
        description = public_data.get("description", "")
        if description:
            html_parts.append(f"<p>{description}</p>")

        # Specifications section
        specifications = public_data.get("specifications", "")
        if specifications:
            # Split specifications into lines
            spec_lines = [line.strip() for line in specifications.split('\n') if line.strip()]

            if spec_lines:
                # Add heading and bulleted list
                html_parts.append("<h3>Specifications</h3>")
                html_parts.append("<ul>")
                for line in spec_lines:
                    html_parts.append(f"<li>{line}</li>")
                html_parts.append("</ul>")

        return "".join(html_parts)

    def _generate_options(
        self,
        variant_records: List[Dict[str, Any]],
        portal_data_by_color: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate product options from variant records.

        Creates options for Color and Unit of Sale.

        Args:
            variant_records: List of variant records
            portal_data_by_color: Portal data indexed by color (not used for unit_of_sale anymore)

        Returns:
            List of option dictionaries
        """
        options = []

        # Option 1: Color
        colors = []
        for record in variant_records:
            color = record.get("color", "").strip()
            if color and color not in colors:
                colors.append(color)

        if colors:
            options.append({
                "name": "Color",
                "position": 1,
                "values": colors
            })

        # Option 2: Unit of Sale - Now simplified to single unit per color
        # Each color gets exactly one unit: Piece (priority) or Sq Ft (fallback)
        # Collect units used across all records
        import math
        units_used = set()
        for record in variant_records:
            # Check piece first (priority)
            if not math.isnan(record.get("cost_per_piece", float('nan'))) and not math.isnan(record.get("price_per_piece", float('nan'))):
                units_used.add("Piece")
            # Fall back to sq ft if piece is missing
            elif not math.isnan(record.get("sq_ft_cost", float('nan'))) and not math.isnan(record.get("sq_ft_price", float('nan'))):
                units_used.add("Sq Ft")

        # Only add Unit of Sale option if multiple units are used across colors
        # (e.g., some colors use Piece, others use Sq Ft)
        if len(units_used) > 1:
            # Maintain order: Piece, then Sq Ft
            ordered_units = []
            if "Piece" in units_used:
                ordered_units.append("Piece")
            if "Sq Ft" in units_used:
                ordered_units.append("Sq Ft")

            options.append({
                "name": "Unit of Sale",
                "position": 2,
                "values": ordered_units
            })
        elif len(units_used) == 1:
            # Single unit type - still add as option for Shopify compatibility
            options.append({
                "name": "Unit of Sale",
                "position": 2,
                "values": list(units_used)
            })

        return options

    def _generate_variants(
        self,
        variant_records: List[Dict[str, Any]],
        portal_data_by_color: Dict[str, Dict[str, Any]],
        product_title: str
    ) -> List[Dict[str, Any]]:
        """
        Generate Shopify variants from variant records.

        Creates ONE variant per color using simplified unit logic:
        - Priority: Piece (if cost_per_piece and price_per_piece exist)
        - Fallback: Sq Ft (if sq_ft_cost and sq_ft_price exist)

        Args:
            variant_records: List of variant records (one per color)
            portal_data_by_color: Portal data indexed by color
            product_title: Product title for logging

        Returns:
            List of variant dictionaries
        """
        import math
        variants = []
        variant_position = 1

        # Process each color
        for record in variant_records:
            color = record.get("color", "").strip()
            portal_data = portal_data_by_color.get(color, {})

            # Extract common data
            base_item_number = str(record.get("item_#", ""))
            model_number = portal_data.get("model_number", "")
            gallery_images = portal_data.get("gallery_images", [])

            # Get cube weight from portal (base weight for conversions)
            weight_info = portal_data.get("weight", "")
            cube_weight_value, weight_unit = self._parse_weight(weight_info)

            # Get conversion factors
            sq_ft_per_cube = record.get("sq_ft_per_cube", 0) or 0
            pieces_per_cube = record.get("pieces_per_cube", 0) or 0

            # Determine which unit to use (Piece priority, Sq Ft fallback)
            unit_config = None

            # Check Piece first (priority)
            piece_cost = record.get("cost_per_piece", float('nan'))
            piece_price = record.get("price_per_piece", float('nan'))
            if not math.isnan(piece_cost) and not math.isnan(piece_price):
                unit_config = {
                    "name": "Piece",
                    "cost": piece_cost,
                    "price": piece_price,
                    "conversion_factor": pieces_per_cube,
                    "conversion_name": "pieces_per_cube"
                }

            # Fall back to Sq Ft if Piece not available
            if unit_config is None:
                sqft_cost = record.get("sq_ft_cost", float('nan'))
                sqft_price = record.get("sq_ft_price", float('nan'))
                if not math.isnan(sqft_cost) and not math.isnan(sqft_price):
                    unit_config = {
                        "name": "Sq Ft",
                        "cost": sqft_cost,
                        "price": sqft_price,
                        "conversion_factor": sq_ft_per_cube,
                        "conversion_name": "sq_ft_per_cube"
                    }

            # Skip this color if no valid unit found
            if unit_config is None:
                continue

            # Validate conversion factor exists
            if unit_config["conversion_factor"] == 0:
                raise ValueError(
                    f"Product '{product_title}' color '{color}' has {unit_config['name']} cost/price data "
                    f"but {unit_config['conversion_name']} is zero or missing. Cannot calculate weight."
                )

            # Calculate weight
            if unit_config["conversion_factor"] and cube_weight_value:
                weight_value = cube_weight_value / unit_config["conversion_factor"]
                # Check if weight_value is NaN before converting to int
                if math.isnan(weight_value):
                    grams = 0
                else:
                    grams = int(weight_value * 453.592) if weight_unit == "lb" else 0
            else:
                weight_value = 0
                grams = 0

            # Generate SKU
            sku = self.sku_generator.generate_unique_sku()

            # Build variant with option keys grouped
            variant = {
                "sku": sku,
                "price": str(unit_config["price"]),
                "cost": str(unit_config["cost"]),
                "barcode": base_item_number,
                "inventory_quantity": self.config.get("inventory_quantity", 5),
                "position": variant_position,
                "option1": color,
                "option2": unit_config["name"],
                "inventory_policy": "deny",
                "compare_at_price": None,
                "fulfillment_service": "manual",
                "inventory_management": "shopify",
                "taxable": True,
                "grams": grams,
                "weight": weight_value,
                "weight_unit": weight_unit if weight_unit else "lb",
                "requires_shipping": True,
                "image_id": None,
                "metafields": []
            }

            # Add color_swatch_image metafield (first portal gallery image)
            if gallery_images:
                variant["metafields"].append({
                    "namespace": "custom",
                    "key": "color_swatch_image",
                    "value": gallery_images[0],
                    "type": "single_line_text_field"
                })

            # Add model number metafield if present
            if model_number:
                variant["metafields"].append({
                    "namespace": "custom",
                    "key": "model_number",
                    "value": model_number,
                    "type": "single_line_text_field"
                })

            # Add unit_of_sale metafield
            variant["metafields"].append({
                "namespace": "custom",
                "key": "unit_of_sale",
                "value": unit_config["name"],
                "type": "single_line_text_field"
            })

            variants.append(variant)
            variant_position += 1

        return variants

    def _parse_weight(self, weight_str: str) -> tuple:
        """
        Parse weight string into value and unit.

        Args:
            weight_str: Weight string like "50 lb", "25.5 kg", etc.

        Returns:
            Tuple of (weight_value, weight_unit)
        """
        if not weight_str:
            return (0, "")

        import re
        match = re.search(r"(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kgs|oz|g)", weight_str.lower())
        if match:
            value = float(match.group(1))
            unit = match.group(2).rstrip("s")  # Remove plural 's'
            return (value, unit)

        return (0, "")

    def _generate_images(
        self,
        public_data: Dict[str, Any],
        portal_data_by_color: Dict[str, Dict[str, Any]],
        product_title: str,
        variant_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate images array with proper ordering and alt tags.

        Creates separate image entries for each variant combination (color × unit_of_sale)
        to support Shopify's gallery filtering.

        Order:
        1. Product images from portal (all colors) with variant alt tags
        2. Hero image from public site with variant alt tags
        3. Gallery images from public site with variant alt tags

        All images receive variant alt tags for Shopify variant filtering.

        Deduplicates images case-insensitively before creating variant entries.

        Args:
            public_data: Public website data
            portal_data_by_color: Portal data indexed by color
            product_title: Product title
            variant_records: List of variant records

        Returns:
            List of image dictionaries with proper alt tags
        """
        import math
        images = []
        position = 1

        # Determine unit for each color (Piece priority, Sq Ft fallback)
        # Each color gets exactly ONE unit - match the logic from _generate_variants
        color_units = {}
        for record in variant_records:
            color = record.get("color", "").strip()

            # Check Piece first (priority)
            piece_cost = record.get("cost_per_piece", float('nan'))
            piece_price = record.get("price_per_piece", float('nan'))
            if not math.isnan(piece_cost) and not math.isnan(piece_price):
                color_units[color] = "Piece"
            # Fall back to Sq Ft
            elif not math.isnan(record.get("sq_ft_cost", float('nan'))) and not math.isnan(record.get("sq_ft_price", float('nan'))):
                color_units[color] = "Sq Ft"

        # Get unique units used across all colors (for alt tag generation)
        sorted_units = []
        if "Piece" in color_units.values():
            sorted_units.append("Piece")
        if "Sq Ft" in color_units.values():
            sorted_units.append("Sq Ft")

        # Get first color for public site images
        first_color = variant_records[0].get("color", "") if variant_records else ""

        # Step 1: Collect and deduplicate all unique image URLs (case-insensitive)
        # Format: [(url, type, color, counter)]
        # Note: Portal images are deduplicated PER COLOR (each color has unique images)
        # Public images (hero/gallery) are deduplicated GLOBALLY (shared across all colors)
        unique_images = []
        seen_urls = set()  # Track lowercase URLs to detect duplicates

        # Phase 1: Collect portal images (all colors)
        # Deduplicate within each color only (not across colors)
        portal_img_counter = {}
        for color, portal_data in portal_data_by_color.items():
            gallery_images = portal_data.get("gallery_images", [])

            if color not in portal_img_counter:
                portal_img_counter[color] = 0

            # Track URLs seen for THIS color only
            color_seen_urls = set()

            for img_url in gallery_images:
                cleaned_url = clean_and_verify_image_url(img_url, timeout=10)
                if cleaned_url:
                    url_lower = cleaned_url.lower()
                    # Only deduplicate within same color
                    if url_lower not in color_seen_urls:
                        color_seen_urls.add(url_lower)
                        seen_urls.add(url_lower)  # Add to global for public image deduplication
                        portal_img_counter[color] += 1
                        unique_images.append({
                            "url": cleaned_url,
                            "type": "portal",
                            "color": color,
                            "counter": portal_img_counter[color]
                        })

        # Phase 2: Collect hero image from public site
        hero_image = public_data.get("hero_image", "")
        if hero_image:
            cleaned_url = clean_and_verify_image_url(hero_image, timeout=10)
            if cleaned_url:
                url_lower = cleaned_url.lower()
                if url_lower not in seen_urls:
                    seen_urls.add(url_lower)
                    unique_images.append({
                        "url": cleaned_url,
                        "type": "hero",
                        "color": first_color,
                        "counter": 0
                    })

        # Phase 3: Collect gallery images from public site
        gallery_images = public_data.get("gallery_images", [])
        lifestyle_counter = 0
        for img_url in gallery_images:
            cleaned_url = clean_and_verify_image_url(img_url, timeout=10)
            if cleaned_url:
                url_lower = cleaned_url.lower()
                if url_lower not in seen_urls:
                    seen_urls.add(url_lower)
                    lifestyle_counter += 1
                    unique_images.append({
                        "url": cleaned_url,
                        "type": "lifestyle",
                        "color": first_color,
                        "counter": lifestyle_counter
                    })

        # Step 2: Create variant entries grouped by variant (easier for human review)
        # Group all images for each variant (color + unit) together in gallery order
        # Variants are combinations of color AND unit_of_sale

        # Get all unique colors from variant records
        colors_in_order = []
        seen_colors = set()
        for record in variant_records:
            color = record.get("color", "")
            if color and color not in seen_colors:
                colors_in_order.append(color)
                seen_colors.add(color)

        # For each color + unit combination (each variant)
        # Each color has exactly ONE unit (Piece or Sq Ft) based on color_units mapping
        for color in colors_in_order:
            # Only generate images for the unit this color actually has
            if color not in color_units:
                continue
            unit = color_units[color]

            # Add images for this specific variant (color + unit combination)
            # Order: portal images for this color, then hero, then lifestyle

            for img_info in unique_images:
                    img_url = img_info["url"]
                    img_type = img_info["type"]
                    img_color = img_info["color"]
                    counter = img_info["counter"]

                    # Only include portal images that match this color
                    # Public images (hero/lifestyle) are shown for all variants
                    if img_type == "portal" and img_color != color:
                        continue

                    # Generate base alt tag based on image type
                    if img_type == "portal":
                        alt_base = f"{product_title} - Product Image {counter}"
                    elif img_type == "hero":
                        alt_base = generate_lifestyle_alt_tag(product_title, "Hero")
                    else:  # lifestyle
                        alt_base = generate_lifestyle_alt_tag(product_title, f"Lifestyle {counter}")

                    # Create variant filter for this color + unit combination
                    variant_filter = generate_variant_alt_tag(
                        option1=color,
                        option2=unit,
                        option3="",
                        option4=""
                    )
                    alt_text = f"{alt_base} {variant_filter}" if variant_filter else alt_base

                    images.append({
                        "position": position,
                        "src": img_url,
                        "alt": alt_text
                    })
                    position += 1

        return images

    def _generate_metafields(self, public_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate product metafields from public data.

        Note: Specifications are now included in descriptionHTML instead of metafields.

        Args:
            public_data: Public website data

        Returns:
            List of metafield dictionaries
        """
        metafields = []

        # Hide online prices for all Cambridge products (still visible in POS)
        # This allows theme to conditionally hide prices on online store while
        # keeping them visible in Shopify POS for in-person sales
        metafields.append({
            "namespace": "custom",
            "key": "hide_online_price",
            "value": "true",
            "type": "boolean"
        })

        return metafields
