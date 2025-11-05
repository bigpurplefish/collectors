"""
Size extraction and matching for Ethical Products collector.

Handles measurement extraction and fuzzy size matching.
"""

import re
from typing import Dict, List

# Unit family mappings (unit -> (base_unit, multiplier))
UNIT_FAMILY_MAP = {
    "IN": ("IN", 1.0),
    "OZ": ("OZ", 1.0), "OUNCE": ("OZ", 1.0), "OUNCES": ("OZ", 1.0),
    "LB": ("OZ", 16.0), "LBS": ("OZ", 16.0), "POUND": ("OZ", 16.0), "POUNDS": ("OZ", 16.0),
    "G": ("G", 1.0), "GRAM": ("G", 1.0), "GRAMS": ("G", 1.0), "KG": ("G", 1000.0),
    "ML": ("ML", 1.0), "MLS": ("ML", 1.0), "L": ("ML", 1000.0), "LITER": ("ML", 1000.0), "LITERS": ("ML", 1000.0),
    "QT": ("QT", 1.0), "QTS": ("QT", 1.0), "QUART": ("QT", 1.0), "QUARTS": ("QT", 1.0),
    "GAL": ("QT", 4.0), "GALS": ("QT", 4.0), "GALLON": ("QT", 4.0), "GALLONS": ("QT", 4.0),
}


def extract_sizes(text: str) -> Dict[str, List[float]]:
    """
    Extract all size measurements from text.

    Groups measurements by unit family (IN, OZ, G, ML, QT).

    Args:
        text: Text containing size measurements

    Returns:
        Dictionary mapping unit family to list of values
    """
    families: Dict[str, List[float]] = {}
    if not text:
        return families

    s = " " + text.upper().replace(""", '"').replace(""", '"') + " "

    # Extract inches with various formats
    for match in re.finditer(r'(?<!\d)(\d+(?:\.\d+)?)\s*(?:\"|INCH(?:ES)?|IN)\b', s, re.I):
        families.setdefault("IN", []).append(float(match.group(1)))

    # Extract other units
    for match in re.finditer(r'(?<!\d)(\d+(?:\.\d+)?)\s*([A-Z]+)\b', s):
        value = float(match.group(1))
        unit = match.group(2).upper()

        if unit in UNIT_FAMILY_MAP:
            base, mult = UNIT_FAMILY_MAP[unit]
            families.setdefault(base, []).append(value * mult)

    return families


def sizes_match(
    query_sizes: Dict[str, List[float]],
    product_sizes: Dict[str, List[float]],
    tolerance_ratio: float = 0.08
) -> bool:
    """
    Check if size measurements match within tolerance.

    Args:
        query_sizes: Sizes from search query
        product_sizes: Sizes from product page
        tolerance_ratio: Allowed deviation as ratio (default 8%)

    Returns:
        True if all common size families match within tolerance
    """
    for family, product_vals in product_sizes.items():
        if not product_vals:
            continue

        query_vals = query_sizes.get(family, [])
        if not query_vals:
            continue

        # Check if any pair matches within tolerance
        matched = False
        for pval in product_vals:
            for qval in query_vals:
                if pval and abs(pval - qval) / pval <= tolerance_ratio:
                    matched = True
                    break
            if matched:
                break

        if not matched:
            return False

    return True
