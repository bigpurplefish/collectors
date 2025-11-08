"""
Data validation utilities.
"""

from typing import List
from src.models import Product, ColorCategory, ProductRecord


def validate_color_categories(categories: List[ColorCategory]) -> bool:
    """
    Validate that color categories are properly extracted.

    Args:
        categories: List of ColorCategory objects

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if not categories:
        raise ValueError("No color categories found")

    for cat in categories:
        if not cat.category:
            raise ValueError(f"Color category missing category name: {cat}")
        if not cat.colors:
            raise ValueError(f"Color category has no colors: {cat.category}")

    return True


def validate_products(products: List[Product]) -> bool:
    """
    Validate that products are properly extracted.

    Args:
        products: List of Product objects

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if not products:
        raise ValueError("No products found")

    for prod in products:
        if not prod.title:
            raise ValueError(f"Product missing title: {prod}")
        if not prod.colors:
            raise ValueError(f"Product has no colors: {prod.title}")
        if prod.product_type not in ["paving_stone", "wall_stone"]:
            raise ValueError(f"Invalid product type: {prod.product_type}")

    return True


def validate_records(records: List[ProductRecord]) -> bool:
    """
    Validate that product records are properly formed.

    Args:
        records: List of ProductRecord objects

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if not records:
        raise ValueError("No product records generated")

    for record in records:
        if not record.title:
            raise ValueError(f"Record missing title: {record}")
        if not record.color:
            raise ValueError(f"Record missing color: {record}")
        if not record.color_category:
            raise ValueError(f"Record missing color_category: {record}")

    return True
