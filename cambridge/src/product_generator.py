"""
Product Generator for Cambridge Collector

Handles:
- Grouping input records by title (variant families)
- Generating Shopify GraphQL-compatible products
- Image ordering (product images first, then lifestyle images)
- Metafields creation
- SKU generation for products without SKUs
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Callable
from collections import defaultdict

# Add parent collectors directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from utils.sku_generator import SKUGenerator


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
        log: Callable = print
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group input records by title.

        Records with the same title are color variants of one product.

        Args:
            records: List of input records
            log: Logging function

        Returns:
            Dictionary mapping title -> list of variant records
        """
        grouped = defaultdict(list)

        for record in records:
            title = record.get("title", "").strip()
            if title:
                grouped[title].append(record)

        log(f"Grouped {len(records)} records into {len(grouped)} product families")

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
            "options": self._generate_options(variant_records),
            "variants": self._generate_variants(variant_records, portal_data_by_color),
            "images": self._generate_images(public_data, portal_data_by_color),
            "metafields": self._generate_metafields(public_data),
        }

        return product

    def _generate_description_html(self, public_data: Dict[str, Any]) -> str:
        """
        Generate HTML description from public data.

        Args:
            public_data: Public website data

        Returns:
            HTML description string
        """
        description = public_data.get("description", "")

        if not description:
            return ""

        # Wrap in paragraph tags
        return f"<p>{description}</p>"

    def _generate_options(self, variant_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate product options from variant records.

        Args:
            variant_records: List of variant records

        Returns:
            List of option dictionaries
        """
        # Extract unique colors
        colors = []
        for record in variant_records:
            color = record.get("color", "").strip()
            if color and color not in colors:
                colors.append(color)

        if not colors:
            return []

        return [
            {
                "name": "Color",
                "position": 1,
                "values": colors
            }
        ]

    def _generate_variants(
        self,
        variant_records: List[Dict[str, Any]],
        portal_data_by_color: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate Shopify variants from variant records.

        Args:
            variant_records: List of variant records
            portal_data_by_color: Portal data indexed by color

        Returns:
            List of variant dictionaries
        """
        variants = []

        for i, record in enumerate(variant_records):
            color = record.get("color", "").strip()
            portal_data = portal_data_by_color.get(color, {})

            # Extract data
            item_number = record.get("item_#", "")
            price = record.get("price", "")
            cost = portal_data.get("cost", "")
            weight = portal_data.get("weight", "")
            sales_unit = portal_data.get("sales_unit", "")
            model_number = portal_data.get("model_number", "")

            # Generate SKU (Cambridge products don't have SKUs)
            sku = self.sku_generator.generate_unique_sku()

            # Build variant
            variant = {
                "sku": sku,
                "price": str(price) if price else "0.00",
                "cost": cost,
                "barcode": sku,  # Use generated SKU as barcode
                "inventory_quantity": 0,
                "position": i + 1,
                "option1": color,
                "inventory_policy": "deny",
                "compare_at_price": None,
                "fulfillment_service": "manual",
                "inventory_management": "shopify",
                "taxable": True,
                "grams": 0,
                "weight": 0,
                "weight_unit": "lb",
                "requires_shipping": True,
                "image_id": None,  # Set later based on color-specific images
                "metafields": []
            }

            # Add metafields
            if weight:
                variant["metafields"].append({
                    "namespace": "custom",
                    "key": "weight_info",
                    "value": weight,
                    "type": "single_line_text_field"
                })

            if sales_unit:
                variant["metafields"].append({
                    "namespace": "custom",
                    "key": "unit_of_sale",
                    "value": sales_unit,
                    "type": "single_line_text_field"
                })

            if model_number:
                variant["metafields"].append({
                    "namespace": "custom",
                    "key": "model_number",
                    "value": model_number,
                    "type": "single_line_text_field"
                })

            variants.append(variant)

        return variants

    def _generate_images(
        self,
        public_data: Dict[str, Any],
        portal_data_by_color: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate images array with proper ordering.

        Order: Product images first, then lifestyle images.

        Args:
            public_data: Public website data
            portal_data_by_color: Portal data indexed by color

        Returns:
            List of image dictionaries
        """
        images = []
        position = 1

        # Phase 1: Add product images from portal (all colors)
        for color, portal_data in portal_data_by_color.items():
            gallery_images = portal_data.get("gallery_images", [])
            for img_url in gallery_images:
                images.append({
                    "position": position,
                    "src": img_url,
                    "alt": f"{public_data.get('title', '')} - {color}"
                })
                position += 1

        # Phase 2: Add lifestyle images from public site
        # Hero image first
        hero_image = public_data.get("hero_image", "")
        if hero_image:
            images.append({
                "position": position,
                "src": hero_image,
                "alt": f"{public_data.get('title', '')} - Hero"
            })
            position += 1

        # Gallery images
        gallery_images = public_data.get("gallery_images", [])
        for img_url in gallery_images:
            images.append({
                "position": position,
                "src": img_url,
                "alt": f"{public_data.get('title', '')} - Lifestyle"
            })
            position += 1

        return images

    def _generate_metafields(self, public_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate product metafields from public data.

        Args:
            public_data: Public website data

        Returns:
            List of metafield dictionaries
        """
        metafields = []

        # Specifications metafield
        specifications = public_data.get("specifications", "")
        if specifications:
            metafields.append({
                "namespace": "custom",
                "key": "specifications",
                "value": f"<p>{specifications}</p>",
                "type": "rich_text_field"
            })

        # Collection metafield
        collection = public_data.get("collection", "")
        if collection:
            metafields.append({
                "namespace": "custom",
                "key": "collection",
                "value": collection,
                "type": "single_line_text_field"
            })

        return metafields
