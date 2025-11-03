"""
Image processing for Ethical Products collector.

Handles WordPress/WooCommerce image extraction and normalization.
"""

import re
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import strip_query_params, make_absolute_url, deduplicate_urls


# Size suffix pattern
SIZE_SUFFIX = re.compile(r"-(\d{2,4}x\d{2,4})(?=\.[a-z]{3,4}$)", re.I)


class EthicalImageProcessor:
    """Handles Ethical Products image processing."""

    def __init__(self, origin: str):
        """
        Initialize image processor.

        Args:
            origin: Site origin URL
        """
        self.origin = origin

    def extract_hires_map(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Build map of hi-res image URLs from .hires links.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary mapping stem roots to hi-res URLs
        """
        hires_map = {}
        for link in soup.select(".hires a[href]"):
            href = strip_query_params(link.get("href") or "")
            if not href:
                continue

            name = href.rsplit("/", 1)[-1]
            stem, ext = self._split_name_ext(name)
            stem_root = self._root_stem(stem)
            hires_map[stem_root] = href

        return hires_map

    def upsize_wp_image(self, url: str, hires_map: Dict[str, str]) -> str:
        """
        Convert WordPress thumbnail URL to full-size URL.

        Removes size suffixes like -150x150, -300x300, -scaled.

        Args:
            url: Image URL (possibly sized)
            hires_map: Map of stem roots to hi-res URLs

        Returns:
            Full-size image URL
        """
        u = strip_query_params(url)
        name = u.rsplit("/", 1)[-1]
        stem, ext = self._split_name_ext(name)
        stem_root = self._root_stem(stem)

        # Check if we have a hi-res version
        hires = hires_map.get(stem_root)
        if hires:
            return make_absolute_url(self.origin, hires)

        # Otherwise, remove size suffix
        new_name = self._root_stem(stem) + ext
        if new_name != name:
            return u.rsplit("/", 1)[0] + "/" + new_name

        return u

    def extract_carousel_images(
        self,
        soup: BeautifulSoup,
        selectors: List[str]
    ) -> List[str]:
        """
        Extract images from Elastislide carousel.

        Args:
            soup: BeautifulSoup object
            selectors: List of CSS selectors to try

        Returns:
            List of image URLs
        """
        images = []

        for selector in selectors:
            for img in soup.select(selector):
                url = img.get("data-largeimg")
                if url:
                    images.append(
                        strip_query_params(
                            make_absolute_url(self.origin, url.strip())
                        )
                    )
            if images:
                break

        return images

    def extract_fallback_images(self, soup: BeautifulSoup, html: str) -> List[str]:
        """
        Extract images using fallback methods.

        Args:
            soup: BeautifulSoup object
            html: Raw HTML

        Returns:
            List of image URLs
        """
        images = []

        # Try .image-preload
        for img in soup.select(".image-preload img[src]"):
            images.append(
                strip_query_params(
                    make_absolute_url(self.origin, img.get("src", "").strip())
                )
            )

        if not images:
            # Try .photos .demowrap
            hero = soup.select_one(".photos .demowrap img[src]")
            if hero and hero.get("src"):
                images.append(
                    strip_query_params(
                        make_absolute_url(self.origin, hero.get("src").strip())
                    )
                )

        if not images:
            # Try WooCommerce gallery
            for link in soup.select(".woocommerce-product-gallery__image a[href]"):
                images.append(
                    strip_query_params(
                        make_absolute_url(self.origin, link.get("href", "").strip())
                    )
                )
            for img in soup.select(".woocommerce-product-gallery__image img[src]"):
                images.append(
                    strip_query_params(
                        make_absolute_url(self.origin, img.get("src", "").strip())
                    )
                )

        if not images:
            # Try og:image
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                images.append(
                    strip_query_params(
                        make_absolute_url(self.origin, og.get("content").strip())
                    )
                )

        if not images:
            # Try bigImageSrc JavaScript variable
            match = re.search(r"bigImageSrc\s*:\s*[\'\"]([^\'\"]+)", html, re.I)
            if match:
                images.append(
                    strip_query_params(
                        make_absolute_url(self.origin, match.group(1).strip())
                    )
                )

        return images

    @staticmethod
    def _split_name_ext(name: str) -> Tuple[str, str]:
        """Split filename into stem and extension."""
        i = name.rfind(".")
        return (name, "") if i == -1 else (name[:i], name[i:])

    @staticmethod
    def _root_stem(stem: str) -> str:
        """Remove size suffixes from stem."""
        s = SIZE_SUFFIX.sub("", stem)
        s = re.sub(r"-scaled$", "", s, flags=re.I)
        return s
