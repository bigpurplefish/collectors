"""
Image processing for Fromm Family Foods collector.

Handles Fromm-specific image extraction from carousel.
"""

import re
from typing import List
from urllib.parse import urlsplit, urlunsplit
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import deduplicate_urls


class FrommImageProcessor:
    """Handles Fromm Family Foods image processing."""

    @staticmethod
    def clean_url(url: str) -> str:
        """
        Clean URL by normalizing to HTTPS and removing query params.

        Args:
            url: URL to clean

        Returns:
            Cleaned URL
        """
        if not url:
            return ""
        parts = urlsplit(url)
        return urlunsplit(("https", parts.netloc, parts.path, "", ""))

    @classmethod
    def extract_gallery_images(cls, html_text: str) -> List[str]:
        """
        Extract full-size product gallery images from #mainCarousel.

        Args:
            html_text: HTML content

        Returns:
            List of normalized, deduplicated image URLs
        """
        media = []

        # Prefer data-src attribute
        for match in re.finditer(
            r'id="mainCarousel"[\s\S]*?<div[^>]*class="carousel__slide"[^>]*\sdata-src="([^"]+)"',
            html_text,
            flags=re.I
        ):
            media.append(match.group(1))

        # Fallback: <img src>
        for match in re.finditer(
            r'id="mainCarousel"[\s\S]*?<div[^>]*class="carousel__slide"[\s\S]*?<img[^>]*\ssrc="([^"]+)"',
            html_text,
            flags=re.I
        ):
            media.append(match.group(1))

        # Filter to Fromm CDN URLs only and normalize
        out = []
        seen = set()

        for url in media:
            if "cdn.frommfamily.com/media/" not in url:
                continue

            cleaned = cls.clean_url(url)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                out.append(cleaned)

        return out
