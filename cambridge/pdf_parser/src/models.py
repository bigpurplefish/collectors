"""
Data models for the PDF parser.

This module defines the data structures used throughout the application
to represent color categories, products, and output records.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ColorCategory:
    """
    Represents a color pricing category from page 2.

    Attributes:
        category: The pricing category name (e.g., "Standard", "Premium")
        reason: The reason for the upcharge
        colors: List of colors that belong to this category
    """
    category: str
    reason: str
    colors: List[str]


@dataclass
class Product:
    """
    Represents a product from pages 4-5.

    Attributes:
        title: The product name
        colors: List of colors available for this product
        product_type: Either "paving_stone" or "wall_stone"
        order_index: Position in the PDF (for maintaining original order)
    """
    title: str
    colors: List[str]
    product_type: str
    order_index: int = 0


@dataclass
class ProductRecord:
    """
    Represents a single row in the output Excel file.

    Attributes:
        vendor_type: Product type ("Paving Stones" or "Wall Stones")
        title: Product name
        color_category: Color pricing category
        color: Product color
        price: Price (blank in output)
        item_number: Item number (blank in output)
        order_index: Position in PDF (for maintaining original order)
    """
    vendor_type: str
    title: str
    color_category: str
    color: str
    price: str = ""
    item_number: str = ""
    order_index: int = 0

    def to_list(self) -> List[str]:
        """Convert record to list for Excel row output."""
        return [
            self.vendor_type,
            self.title,
            self.color_category,
            self.color,
            self.item_number,
            self.price
        ]
