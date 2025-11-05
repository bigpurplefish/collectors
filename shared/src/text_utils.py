"""
Text processing utilities for product collectors.

Provides HTML stripping, entity unescaping, and text normalization functions.
"""

import html
import re
from typing import Optional


def text_only(s: Optional[str]) -> str:
    """
    Strip HTML tags and unescape HTML entities.

    Converts <br> tags to newlines before stripping all other HTML.

    Args:
        s: HTML string to process

    Returns:
        Plain text with HTML removed and entities unescaped
    """
    if s is None:
        return ""
    # Convert <br> tags to newlines
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    # Remove all HTML tags
    s = re.sub(r"<[^>]+>", "", s)
    # Unescape HTML entities
    return html.unescape(s).strip()


def plain_text(html_content: Optional[str]) -> str:
    """
    Convert HTML to plain text with enhanced whitespace normalization.

    Similar to text_only but with more aggressive whitespace handling.

    Args:
        html_content: HTML string to process

    Returns:
        Plain text with normalized whitespace
    """
    if not html_content:
        return ""
    # Convert <br> tags to newlines
    txt = re.sub(r"<\s*br\s*/?>", "\n", html_content, flags=re.I)
    # Remove all HTML tags
    txt = re.sub(r"<[^>]+>", " ", txt)
    # Normalize horizontal whitespace
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    # Normalize vertical whitespace
    txt = re.sub(r"\s*\n\s*", "\n", txt)
    return txt.strip()


def normalize_whitespace(s: str) -> str:
    """
    Collapse multiple whitespace characters into single spaces.

    Args:
        s: String to normalize

    Returns:
        String with collapsed whitespace
    """
    return re.sub(r"\s+", " ", (s or "").strip())


def extract_bullet_points(description: str) -> list[str]:
    """
    Extract bullet points from a description if it looks like a list.

    Detects common list markers (bullets, dashes, semicolons) and
    extracts individual items if the description appears to be a bulleted list.

    Args:
        description: Description text to process

    Returns:
        List of bullet points, or empty list if not a bulleted format
    """
    if not description:
        return []

    # Normalize line endings
    norm = description.strip().replace("\r\n", "\n").replace("\r", "\n")
    # Replace various bullet separators with newlines
    norm = norm.replace("..", "\n").replace(";", "\n")
    norm = norm.replace("•", "\n").replace("·", "\n").replace("●", "\n")
    # Replace dash bullets
    norm = re.sub(r"\n?\s*[–—-]\s+", "\n", norm)

    # Split and clean parts
    parts = [p.strip(" .•\t") for p in norm.split("\n")]
    parts = [p for p in parts if p]

    # Check if it looks like a list (at least 2 items, most items short-ish)
    looks_like_list = (
        len(parts) >= 2 and
        sum(1 for p in parts if len(p) <= 140) >= max(2, int(0.6 * len(parts)))
    )

    if not looks_like_list:
        return []

    def tidy(x: str) -> str:
        """Clean up individual bullet point."""
        x = x.strip()
        # Remove trailing period
        if x.endswith("."):
            x = x[:-1].strip()
        # Convert ALL CAPS to Title Case
        if len(x) > 2 and x.isupper():
            x = x[:1].upper() + x[1:].lower()
        return x

    # Deduplicate while preserving order
    seen, out = set(), []
    for b in (tidy(p) for p in parts):
        k = b.lower()
        if b and k not in seen:
            out.append(b)
            seen.add(k)

    return out
