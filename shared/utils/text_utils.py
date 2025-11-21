"""
Text Normalization Utilities

Provides shared text normalization functions for consistent data processing
across all collectors.
"""

import re
from typing import Any, Dict, List, Union


def normalize_text(text: str) -> str:
    """
    Normalize text for consistent matching and storage.

    Applies the following normalizations:
    1. Converts escaped quotes (\") to actual quotes (")
    2. Converts copyright symbol (©) to (C)
    3. Collapses multiple whitespace to single space
    4. Strips leading/trailing whitespace

    Args:
        text: String to normalize

    Returns:
        Normalized string

    Examples:
        >>> normalize_text('Product  Name')
        'Product Name'
        >>> normalize_text('Product\\"Name')
        'Product"Name'
        >>> normalize_text('Product © 2024')
        'Product (C) 2024'
        >>> normalize_text('  Product   Name  ')
        'Product Name'
    """
    if not isinstance(text, str):
        return text

    # Normalize escaped quotes to actual quotes
    text = text.replace('\\"', '"')

    # Normalize copyright symbol to (C)
    text = text.replace('©', '(C)')

    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def normalize_dict_strings(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all string values in a dictionary.

    Recursively normalizes all string values in the dictionary,
    leaving non-string values unchanged.

    Args:
        data: Dictionary to normalize

    Returns:
        Dictionary with normalized string values

    Examples:
        >>> normalize_dict_strings({'name': 'Product  Name', 'count': 5})
        {'name': 'Product Name', 'count': 5}
    """
    normalized = {}

    for key, value in data.items():
        if isinstance(value, str):
            normalized[key] = normalize_text(value)
        elif isinstance(value, dict):
            normalized[key] = normalize_dict_strings(value)
        elif isinstance(value, list):
            normalized[key] = normalize_list_strings(value)
        else:
            normalized[key] = value

    return normalized


def normalize_list_strings(data: List[Any]) -> List[Any]:
    """
    Normalize all string values in a list.

    Recursively normalizes all string values in the list,
    leaving non-string values unchanged.

    Args:
        data: List to normalize

    Returns:
        List with normalized string values

    Examples:
        >>> normalize_list_strings(['Product  Name', 5, 'Another  Product'])
        ['Product Name', 5, 'Another Product']
    """
    normalized = []

    for item in data:
        if isinstance(item, str):
            normalized.append(normalize_text(item))
        elif isinstance(item, dict):
            normalized.append(normalize_dict_strings(item))
        elif isinstance(item, list):
            normalized.append(normalize_list_strings(item))
        else:
            normalized.append(item)

    return normalized


def normalize_product_titles(
    products: List[Dict[str, Any]],
    title_field: str = "title"
) -> List[Dict[str, Any]]:
    """
    Normalize product titles in a list of product dictionaries.

    Useful for normalizing product indexes after loading from cache.

    Args:
        products: List of product dictionaries
        title_field: Name of the field containing the title (default: "title")

    Returns:
        List of products with normalized titles

    Examples:
        >>> products = [{'title': 'Product  Name', 'price': 10}]
        >>> normalize_product_titles(products)
        [{'title': 'Product Name', 'price': 10}]
    """
    for product in products:
        if title_field in product and isinstance(product[title_field], str):
            product[title_field] = normalize_text(product[title_field])

    return products
