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
            "variants": self._generate_variants(variant_records, portal_data_by_color, title),
            "images": self._generate_images(public_data, portal_data_by_color, title, variant_records),
            "metafields": self._generate_metafields(public_data),
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
            portal_data_by_color: Portal data indexed by color

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

        # Option 2: Unit of Sale (if available)
        sales_units = []
        for color, portal_data in portal_data_by_color.items():
            sales_unit = portal_data.get("sales_unit", "").strip()
            if sales_unit and sales_unit not in sales_units:
                sales_units.append(sales_unit)

        if sales_units:
            # Always add as option when present, even if only one value
            options.append({
                "name": "Unit of Sale",
                "position": 2,
                "values": sales_units
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

        Args:
            variant_records: List of variant records
            portal_data_by_color: Portal data indexed by color
            product_title: Product title for logging

        Returns:
            List of variant dictionaries
        """
        variants = []

        for i, record in enumerate(variant_records):
            color = record.get("color", "").strip()
            portal_data = portal_data_by_color.get(color, {})

            # Extract data from input record
            item_number = record.get("item_#", "")
            price = record.get("price", "")  # From input file
            cost = record.get("cost", "")    # From input file

            # Extract data from portal
            weight_info = portal_data.get("weight", "")
            sales_unit = portal_data.get("sales_unit", "")
            model_number = portal_data.get("model_number", "")

            # Parse weight into value and unit
            weight_value, weight_unit = self._parse_weight(weight_info)

            # Generate SKU (Cambridge products don't have SKUs)
            sku = self.sku_generator.generate_unique_sku()

            # Check if sales_unit should be included as option2
            all_sales_units = set()
            for pd in portal_data_by_color.values():
                su = pd.get("sales_unit", "").strip()
                if su:
                    all_sales_units.add(su)

            # Build variant with option keys grouped at top for readability
            variant = {
                "sku": sku,
                "price": str(price) if price else "0.00",
                "cost": str(cost) if cost else "",
                "barcode": sku,  # Use generated SKU as barcode
                "inventory_quantity": 0,
                "position": i + 1,
                "option1": color,
                "inventory_policy": "deny",
                "compare_at_price": None,
                "fulfillment_service": "manual",
                "inventory_management": "shopify",
                "taxable": True,
                "grams": int(weight_value * 453.592) if weight_value and weight_unit == "lb" else 0,  # Convert lbs to grams
                "weight": weight_value if weight_value else 0,
                "weight_unit": weight_unit if weight_unit else "lb",
                "requires_shipping": True,
                "image_id": None,  # Set later based on color-specific images
                "metafields": []
            }

            # Add option2 immediately after option1 if sales_unit exists
            if all_sales_units and sales_unit:
                # Insert option2 right after option1 for better readability
                # Need to rebuild variant dict with proper ordering
                variant = {
                    "sku": variant["sku"],
                    "price": variant["price"],
                    "cost": variant["cost"],
                    "barcode": variant["barcode"],
                    "inventory_quantity": variant["inventory_quantity"],
                    "position": variant["position"],
                    "option1": variant["option1"],
                    "option2": sales_unit,  # Add option2 right after option1
                    "inventory_policy": variant["inventory_policy"],
                    "compare_at_price": variant["compare_at_price"],
                    "fulfillment_service": variant["fulfillment_service"],
                    "inventory_management": variant["inventory_management"],
                    "taxable": variant["taxable"],
                    "grams": variant["grams"],
                    "weight": variant["weight"],
                    "weight_unit": variant["weight_unit"],
                    "requires_shipping": variant["requires_shipping"],
                    "image_id": variant["image_id"],
                    "metafields": variant["metafields"]
                }

            # Add color_swatch_image metafield (first portal gallery image)
            gallery_images = portal_data.get("gallery_images", [])
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

            # Add sales_unit metafield if present
            if sales_unit:
                variant["metafields"].append({
                    "namespace": "custom",
                    "key": "unit_of_sale",
                    "value": sales_unit,
                    "type": "single_line_text_field"
                })

            variants.append(variant)

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

        Order:
        1. Product images from portal (all colors) with variant alt tags
        2. Hero image from public site with variant alt tag (first color)
        3. Gallery images from public site with variant alt tags (first color)

        All images receive variant alt tags for Shopify variant filtering.

        Args:
            public_data: Public website data
            portal_data_by_color: Portal data indexed by color
            product_title: Product title
            variant_records: List of variant records

        Returns:
            List of image dictionaries with proper alt tags
        """
        images = []
        position = 1

        # Determine if we have sales units for option2
        all_sales_units = set()
        for pd in portal_data_by_color.values():
            su = pd.get("sales_unit", "").strip()
            if su:
                all_sales_units.add(su)
        has_unit_option = bool(all_sales_units)

        # Phase 1: Add product images from portal (all colors) with descriptive alt tags + variant filters
        portal_img_counter = {}  # Track image count per color for unique descriptions
        for color, portal_data in portal_data_by_color.items():
            gallery_images = portal_data.get("gallery_images", [])

            if color not in portal_img_counter:
                portal_img_counter[color] = 0

            # Generate variant filter for this color
            sales_unit = portal_data.get("sales_unit", "") if has_unit_option else ""
            variant_filter = generate_variant_alt_tag(
                option1=color,
                option2=sales_unit if has_unit_option else "",
                option3="",
                option4=""
            )

            for img_url in gallery_images:
                # Clean and verify URL
                cleaned_url = clean_and_verify_image_url(img_url, timeout=10)
                if cleaned_url:
                    portal_img_counter[color] += 1
                    # Portal alt: "Product Title - Product Image 1 #option1#option2"
                    portal_alt = f"{product_title} - Product Image {portal_img_counter[color]}"
                    if variant_filter:
                        portal_alt = f"{portal_alt} {variant_filter}"

                    images.append({
                        "position": position,
                        "src": cleaned_url,
                        "alt": portal_alt
                    })
                    position += 1

        # Phase 2 & 3: Add hero and gallery images from public site with variant alt tags
        # Public images are shared across all variants, so use the first variant's alt tag
        if variant_records:
            first_color = variant_records[0].get("color", "")
            first_portal_data = portal_data_by_color.get(first_color, {})
            first_sales_unit = first_portal_data.get("sales_unit", "") if has_unit_option else ""

            # Generate variant filter tag for first variant (all public images use this)
            variant_filter = generate_variant_alt_tag(
                option1=first_color,
                option2=first_sales_unit if has_unit_option else "",
                option3="",
                option4=""
            )

            # Add hero image with descriptive alt tag + variant filter
            hero_image = public_data.get("hero_image", "")
            if hero_image:
                cleaned_url = clean_and_verify_image_url(hero_image, timeout=10)
                if cleaned_url:
                    # Hero alt: "Product Title - Hero #option1#option2"
                    hero_alt = generate_lifestyle_alt_tag(product_title, "Hero")
                    if variant_filter:
                        hero_alt = f"{hero_alt} {variant_filter}"

                    images.append({
                        "position": position,
                        "src": cleaned_url,
                        "alt": hero_alt
                    })
                    position += 1

            # Add gallery images with descriptive alt tags + variant filters
            gallery_images = public_data.get("gallery_images", [])
            lifestyle_counter = 0  # Track lifestyle image count for unique descriptions
            for img_url in gallery_images:
                cleaned_url = clean_and_verify_image_url(img_url, timeout=10)
                if cleaned_url:
                    lifestyle_counter += 1
                    # Gallery alt: "Product Title - Lifestyle 1 #option1#option2"
                    gallery_alt = generate_lifestyle_alt_tag(product_title, f"Lifestyle {lifestyle_counter}")
                    if variant_filter:
                        gallery_alt = f"{gallery_alt} {variant_filter}"

                    images.append({
                        "position": position,
                        "src": cleaned_url,
                        "alt": gallery_alt
                    })
                    position += 1

        # Deduplicate while preserving order
        deduplicated = deduplicate_images(images)

        # Renumber positions after deduplication
        for i, img in enumerate(deduplicated, 1):
            img["position"] = i

        return deduplicated

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

        # No metafields currently needed for Cambridge products
        # (Specifications moved to descriptionHTML)

        return metafields
