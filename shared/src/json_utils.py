"""
JSON processing utilities for product collectors.

Provides JSON extraction from HTML and file I/O helpers.
"""

import json
import re
from typing import Optional, Dict, Any, List


def extract_json_from_script(
    html: str,
    variable_name: Optional[str] = None,
    type_filter: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Extract JSON data from JavaScript in HTML.

    Can extract from:
    - JSON-LD script tags (type="application/ld+json")
    - JavaScript variable assignments (var varName = {...})

    Args:
        html: HTML content containing JavaScript
        variable_name: JavaScript variable name to extract (e.g., "modelProduct")
        type_filter: JSON-LD @type to filter for (e.g., "Product")

    Returns:
        Parsed JSON object or None if not found
    """
    # Extract from JSON-LD script tags
    if not variable_name:
        for match in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            flags=re.I | re.DOTALL
        ):
            try:
                data = json.loads(match.group(1).strip())
                # Apply type filter if specified
                if type_filter:
                    if isinstance(data, dict) and data.get("@type") == type_filter:
                        return data
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("@type") == type_filter:
                                return item
                else:
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    # Extract from JavaScript variable
    pattern = rf"var\s+{re.escape(variable_name)}\s*=\s*(\{{.*?\}});?"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None

    try:
        # Unescape HTML entities and normalize protocols
        json_str = match.group(1)
        import html as html_module
        json_str = html_module.unescape(json_str)
        json_str = json_str.rstrip(";").replace("http://", "https://")
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


def load_json_file(file_path: str) -> Any:
    """
    Load JSON from file with error handling.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        RuntimeError: If file doesn't exist or JSON is invalid
    """
    import os

    if not os.path.isfile(file_path):
        raise RuntimeError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to read {file_path}: {e}")


def save_json_file(data: Any, file_path: str, indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Data to serialize
        file_path: Path to output file
        indent: JSON indentation (default: 2)
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def build_catalog_index(
    catalog_data: List[Dict[str, Any]],
    upc_field: str = "upc",
    url_field: str = "product_url"
) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Build indexes for fast catalog lookups.

    Creates two indexes:
    - by_upc: Maps normalized UPC to product record
    - by_url: Maps product URL to product record

    Args:
        catalog_data: List of product records
        upc_field: Field name containing UPC
        url_field: Field name containing product URL

    Returns:
        Tuple of (by_upc dict, by_url dict)
    """
    from .upc_utils import normalize_upc

    by_upc: Dict[str, Dict[str, Any]] = {}
    by_url: Dict[str, Dict[str, Any]] = {}

    for record in catalog_data:
        # Index by UPC
        upc = record.get(upc_field)
        if upc:
            upc_clean = normalize_upc(str(upc))
            if upc_clean:
                by_upc[upc_clean] = record

        # Index by URL
        url = record.get(url_field)
        if url:
            url_clean = str(url).strip()
            if url_clean:
                by_url[url_clean] = record

    return by_upc, by_url
