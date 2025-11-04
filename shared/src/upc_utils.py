"""
UPC processing utilities for product collectors.

Provides UPC normalization and validation functions.
"""

import re
from typing import Optional


def normalize_upc(upc: Optional[str]) -> str:
    """
    Normalize UPC to digits only.

    Removes all non-digit characters from a UPC string.

    Args:
        upc: UPC string (may contain dashes, spaces, etc.)

    Returns:
        UPC with only digits
    """
    if not upc:
        return ""
    return re.sub(r"\D", "", str(upc))


def is_valid_upc(upc: str) -> bool:
    """
    Check if UPC is valid (12 or 13 digits).

    Args:
        upc: UPC string to validate

    Returns:
        True if UPC is 12 or 13 digits, False otherwise
    """
    clean = normalize_upc(upc)
    return len(clean) in (12, 13)


def upc_12_to_13(upc: str) -> str:
    """
    Convert 12-digit UPC to 13-digit EAN by adding leading zero.

    Args:
        upc: 12-digit UPC

    Returns:
        13-digit EAN or original if not 12 digits
    """
    clean = normalize_upc(upc)
    if len(clean) == 12:
        return "0" + clean
    return clean


def upc_13_to_12(upc: str) -> str:
    """
    Convert 13-digit EAN to 12-digit UPC by removing leading zero.

    Only converts if the 13-digit code starts with 0.

    Args:
        upc: 13-digit EAN

    Returns:
        12-digit UPC or original if not convertible
    """
    clean = normalize_upc(upc)
    if len(clean) == 13 and clean.startswith("0"):
        return clean[1:]
    return clean


def extract_upcs_from_text(text: str) -> list[str]:
    """
    Extract all UPCs (12 or 13 digits) from text.

    Args:
        text: Text that may contain UPCs

    Returns:
        List of unique UPCs found in text
    """
    if not text:
        return []

    upcs = set()
    # Find all 12-13 digit sequences
    for match in re.finditer(r"\b(\d{12,13})\b", text):
        upc = match.group(1)
        # Normalize 13-digit to 12-digit if starts with 0
        if len(upc) == 13 and upc.startswith("0"):
            upc = upc[1:]
        if len(upc) == 12:
            upcs.add(upc)

    return sorted(upcs)
