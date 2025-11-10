"""
Parser for Cambridge public website (www.cambridgepavers.com).

Extracts:
- Hero image (top of page)
- Gallery images (carousel)
- Product description
- Specifications
"""

import re
import sys
import os
from typing import Dict, List, Any
from bs4 import BeautifulSoup

# Add parent directories to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class CambridgePublicParser:
    """Parser for Cambridge public website product pages."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize parser.

        Args:
            config: Site configuration dictionary
        """
        self.config = config
        self.origin = config.get("public_origin", "https://www.cambridgepavers.com")

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Parse product page HTML from public website.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted data:
            - hero_image: URL of hero image
            - gallery_images: List of gallery image URLs
            - description: Product description text
            - specifications: Product specifications text
        """
        soup = BeautifulSoup(html_text, "lxml")

        return {
            "hero_image": self._extract_hero_image(soup),
            "gallery_images": self._extract_gallery_images(soup),
            "description": self._extract_description(soup),
            "specifications": self._extract_specifications(soup),
            "title": self._extract_title(soup),
            "collection": self._extract_collection(soup),
            "colors": self._extract_colors(soup),
        }

    def _extract_hero_image(self, soup: BeautifulSoup) -> str:
        """
        Extract hero image URL from page.

        The hero image is the main product image at the top of the page.

        Args:
            soup: BeautifulSoup object

        Returns:
            Hero image URL or empty string
        """
        # Look for the main product image in the image-box
        # Pattern: <div class="image-box style-2 ..."><img src="..." alt="..."></div>
        image_box = soup.find("div", class_="image-box")
        if image_box:
            img = image_box.find("img", src=True)
            if img:
                src = img["src"]
                return self._normalize_image_url(src)

        return ""

    def _extract_gallery_images(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract gallery images from carousel.

        Gallery images are in the owl-carousel div below the hero image.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of gallery image URLs
        """
        gallery_urls = []

        # Find the owl-carousel div
        carousel = soup.find("div", class_="owl-carousel")
        if not carousel:
            return gallery_urls

        # Find all images in the carousel
        for overlay_container in carousel.find_all("div", class_="overlay-container"):
            img = overlay_container.find("img", src=True)
            if img:
                src = img["src"]
                url = self._normalize_image_url(src)
                if url:
                    gallery_urls.append(url)

        return gallery_urls

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """
        Extract product description.

        Description is in a paragraph following <strong>Description:</strong>

        Args:
            soup: BeautifulSoup object

        Returns:
            Description text or empty string
        """
        # Find the <strong>Description:</strong> tag
        description_label = soup.find("strong", string=re.compile(r"Description:", re.IGNORECASE))
        if not description_label:
            return ""

        # Find the parent element and get the next paragraph
        parent = description_label.find_parent()
        if not parent:
            return ""

        # Get text from the paragraph, skipping the "Description:" label
        text = parent.get_text(separator=" ", strip=True)

        # Remove "Description:" prefix if present
        text = re.sub(r"^Description:\s*", "", text, flags=re.IGNORECASE)

        return text.strip()

    def _extract_specifications(self, soup: BeautifulSoup) -> str:
        """
        Extract product specifications.

        Specifications are in a paragraph following <strong>Specifications:</strong>

        Args:
            soup: BeautifulSoup object

        Returns:
            Specifications text or empty string
        """
        # Find the <strong>Specifications:</strong> tag
        specs_label = soup.find("strong", string=re.compile(r"Specifications:", re.IGNORECASE))
        if not specs_label:
            return ""

        # Find the parent element and get the next <p> tag
        parent = specs_label.find_parent()
        if not parent:
            return ""

        # Look for the next <p> tag after the specs label
        specs_p = parent.find("p")
        if specs_p:
            text = specs_p.get_text(separator="\n", strip=True)
            return text.strip()

        # Fallback: get all text after specs label
        text = parent.get_text(separator="\n", strip=True)
        text = re.sub(r"^Specifications:\s*", "", text, flags=re.IGNORECASE)

        return text.strip()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extract product title from page.

        Args:
            soup: BeautifulSoup object

        Returns:
            Product title or empty string
        """
        # Look for the page title
        title_tag = soup.find("h1", class_="page-title")
        if title_tag:
            strong_tag = title_tag.find("strong")
            if strong_tag:
                return strong_tag.get_text(strip=True)

        # Fallback: use meta title or h1
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return ""

    def _extract_collection(self, soup: BeautifulSoup) -> str:
        """
        Extract collection name (e.g., "Sherwood Collection").

        Args:
            soup: BeautifulSoup object

        Returns:
            Collection name or empty string
        """
        # Look for the collection name in h4 tag
        # Pattern: <h4><span style="text-transform: uppercase;">Sherwood Collection</span></h4>
        h4 = soup.find("h4")
        if h4:
            span = h4.find("span")
            if span:
                return span.get_text(strip=True)

        return ""

    def _extract_colors(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract available colors for this product.

        Colors are displayed as swatches with names in the "Color Selection" section.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of color names
        """
        colors = []

        # Find the "Color Selection:" section
        color_section_label = soup.find("strong", string=re.compile(r"Color Selection:", re.IGNORECASE))
        if not color_section_label:
            return colors

        # Find the parent row containing all color swatches
        parent_row = color_section_label.find_parent("div", class_="row")
        if not parent_row:
            return colors

        # Find the row containing color swatches
        swatches_row = parent_row.find_next_sibling("div", class_="row")
        if not swatches_row:
            return colors

        # Extract color names from each swatch
        for col in swatches_row.find_all("div", class_=re.compile(r"col-")):
            # Color name is in a <span class="small"> tag
            color_span = col.find("span", class_="small")
            if color_span:
                color_name = color_span.get_text(strip=True)
                if color_name:
                    colors.append(color_name)

        return colors

    def _normalize_image_url(self, url: str) -> str:
        """
        Normalize image URL to absolute HTTPS URL.

        Args:
            url: Raw image URL

        Returns:
            Normalized absolute URL
        """
        if not url:
            return ""

        url = url.strip()

        # Handle protocol-relative URLs
        if url.startswith("//"):
            url = f"https:{url}"

        # Handle relative URLs
        elif url.startswith("/"):
            url = f"{self.origin}{url}"

        # Ensure HTTPS
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        return url
