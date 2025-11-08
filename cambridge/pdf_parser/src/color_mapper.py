"""
Color mapping module.

This module handles mapping product colors to pricing categories based on
the color category table from page 2.
"""

from typing import List, Dict, Optional
from src.models import ColorCategory, Product, ProductRecord
from utils.text_utils import normalize_color_name


class ColorMapper:
    """
    Maps product colors to pricing categories.
    """

    def __init__(self, color_categories: List[ColorCategory]):
        """
        Initialize the color mapper.

        Args:
            color_categories: List of ColorCategory objects from page 2
        """
        self.color_categories = color_categories
        self._color_map = self._build_color_map()

    def _build_color_map(self) -> Dict[str, str]:
        """
        Build a normalized color-to-category mapping.

        Returns:
            Dictionary mapping normalized color names to category names
        """
        color_map = {}

        for category in self.color_categories:
            for color in category.colors:
                # Normalize color name for consistent lookups
                normalized = normalize_color_name(color)
                color_map[normalized] = category.category

        return color_map

    def get_color_category(self, color: str) -> Optional[str]:
        """
        Get the pricing category for a color.

        Args:
            color: Color name

        Returns:
            Category name, or None if color not found
        """
        normalized = normalize_color_name(color)

        # Try exact match first
        if normalized in self._color_map:
            return self._color_map[normalized]

        # Try replacing space with slash (e.g., "Ruby Onyx" -> "ruby/onyx")
        if ' ' in normalized:
            with_slash = normalized.replace(' ', '/')
            if with_slash in self._color_map:
                return self._color_map[with_slash]

        # Try replacing slash with space (e.g., "Toffee/Onyx" -> "toffee onyx")
        if '/' in normalized:
            with_space = normalized.replace('/', ' ')
            if with_space in self._color_map:
                return self._color_map[with_space]

        return None

    def create_product_records(self, products: List[Product]) -> List[ProductRecord]:
        """
        Create ProductRecord objects for all product-color combinations.

        Args:
            products: List of Product objects

        Returns:
            List of ProductRecord objects, sorted by vendor_type, title, color_category, color
        """
        from src.config import VENDOR_TYPE_PAVING, VENDOR_TYPE_WALL

        records = []

        for product in products:
            # Map product_type to vendor_type
            if product.product_type == "paving_stone":
                vendor_type = VENDOR_TYPE_PAVING
            elif product.product_type == "wall_stone":
                vendor_type = VENDOR_TYPE_WALL
            else:
                vendor_type = "Unknown"

            for color in product.colors:
                # Get the color category
                color_category = self.get_color_category(color)

                if color_category:
                    record = ProductRecord(
                        vendor_type=vendor_type,
                        title=product.title,
                        color_category=color_category,
                        color=color,
                        price="",  # Blank as per requirements
                        item_number="",  # Blank as per requirements
                        order_index=product.order_index
                    )
                    records.append(record)
                else:
                    # Log warning but continue processing
                    print(f"Warning: No category found for color '{color}' "
                          f"in product '{product.title}'")

        # Define custom order for color categories
        category_order = {
            "STANDARD COLORS": 0,
            "COLOR PLUS": 1,
            "PREMIER COLORS": 2
        }

        # Sort by vendor_type, order_index (PDF position), color_category (custom order), color (alphabetically)
        records.sort(key=lambda r: (
            r.vendor_type,
            r.order_index,
            category_order.get(r.color_category, 999),  # Use 999 for unknown categories
            r.color
        ))

        return records

    def get_unmapped_colors(self, products: List[Product]) -> List[str]:
        """
        Get list of colors that don't have a category mapping.

        Args:
            products: List of Product objects

        Returns:
            List of colors without category mappings
        """
        unmapped = []

        for product in products:
            for color in product.colors:
                if not self.get_color_category(color):
                    normalized = normalize_color_name(color)
                    if normalized not in unmapped:
                        unmapped.append(color)

        return sorted(unmapped)
