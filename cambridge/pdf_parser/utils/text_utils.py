"""
Text utility functions for cleaning and normalizing text extracted from PDFs.
"""

import re


def clean_text(text: str) -> str:
    """
    Clean and normalize text extracted from PDF.

    Args:
        text: Raw text string

    Returns:
        Cleaned text with normalized whitespace
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = " ".join(text.split())

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def normalize_color_name(color: str) -> str:
    """
    Normalize a color name for consistent comparison.

    Args:
        color: Raw color name

    Returns:
        Normalized color name (cleaned, lowercase)
    """
    color = clean_text(color)
    return color.lower()


def split_color_list(color_text: str) -> list[str]:
    """
    Split a comma-separated list of colors into individual color names.

    Args:
        color_text: Text containing comma-separated colors

    Returns:
        List of individual color names
    """
    if not color_text:
        return []

    # Fix known typo: "Salmon Toffee/Onyx" should be "Salmon, Toffee/Onyx"
    color_text = color_text.replace("Salmon Toffee/Onyx", "Salmon, Toffee/Onyx")

    # Split on commas
    colors = [c.strip() for c in color_text.split(",")]

    # Filter out empty strings
    colors = [c for c in colors if c]

    return colors


def is_empty_cell(text: str) -> bool:
    """
    Check if a table cell is effectively empty.

    Args:
        text: Cell text content

    Returns:
        True if cell is empty or contains only whitespace
    """
    return not text or not text.strip()
