"""
Page parsing for Orgill collector.

Extracts product data from HTML pages.
"""

import re
import html
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import text_only


class OrgillParser:
    """Parses Orgill product pages."""

    def __init__(self, origin: str):
        """
        Initialize parser.

        Args:
            origin: Site origin URL
        """
        self.origin = origin

    def _grab_id(self, soup: BeautifulSoup, html_text: str, element_id: str) -> str:
        """
        Extract text from element by ID.

        Args:
            soup: BeautifulSoup object
            html_text: Raw HTML text
            element_id: Element ID to find

        Returns:
            Extracted text
        """
        el = soup.select_one(f"#{element_id}")
        if el:
            return text_only(el.get_text(" ", strip=True))
        m = re.search(rf'id="{re.escape(element_id)}"\s*>\s*([^<]+)<', html_text or "")
        return text_only(m.group(1)) if m else ""

    def _first_overview_paragraph(self, container) -> str:
        """Extract first overview paragraph."""
        if not container:
            return ""
        p = container.find("p", class_=re.compile(r"\btext-details-description\b", re.I))
        return text_only(p.get_text(" ", strip=True)) if p else ""

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Returns:
            title: Product title
            brand_hint: Brand name (Vendor)
            benefits: List of product benefits (Features)
            description: Product description (Product Overview)
            gallery_images: List of image URLs
            country_of_origin: Country of origin
            orgill_item_number: Orgill item number

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        soup = BeautifulSoup(html_text or "", "html.parser")

        # Extract title
        title = self._grab_id(
            soup, html_text, "cphMainContent_ctl00_lblDescription"
        ) or self._grab_id(soup, html_text, "cphMainContent_lblDescription")

        # Extract brand (Vendor)
        brand_el = soup.select_one(
            "#cphMainContent_ctl00_lblVendorName"
        ) or soup.select_one("#cphMainContent_lblVendorName")
        brand = text_only(brand_el.get_text(" ", strip=True)) if brand_el else ""

        # Extract description (Product Overview)
        pov = soup.select_one("#cphMainContent_ctl00_lblProductOverview")
        pov_xs = soup.select_one("#cphMainContent_ctl00_lblProductOverviewxs")
        description = self._first_overview_paragraph(pov) or self._first_overview_paragraph(
            pov_xs
        )

        # Extract benefits (Features list)
        benefits: List[str] = []

        # Find the "Features" header
        header = None
        for h in soup.find_all(
            ["h3", "h4"], class_=re.compile(r"\btext-details-header\b", re.I)
        ):
            if text_only(h.get_text()).lower() == "features":
                header = h
                break

        # From that header, locate the first following UL/OL
        if header:
            list_container = header.find_next(
                lambda t: (
                    t.name in ("ul", "ol")
                    or (t.name in ("div", "section") and t.find("li"))
                )
            )
            if list_container:
                for li in list_container.find_all("li"):
                    txt = text_only(li.get_text(" ", strip=True))
                    if txt:
                        benefits.append(txt)

        # Fallback: if nothing found, try any block adjacent to "Features" label
        if not benefits:
            cand = soup.find(string=re.compile(r"^\s*Features\s*$", re.I))
            if cand:
                parent = getattr(cand, "parent", None)
                block = (
                    parent.find_next(
                        lambda t: t and (t.name in ("ul", "ol") or t.find("li"))
                    )
                    if parent
                    else None
                )
                if block:
                    for li in block.find_all("li"):
                        txt = text_only(li.get_text(" ", strip=True))
                        if txt:
                            benefits.append(txt)

        # Extract gallery images (Orgill CDN)
        imgs: List[str] = []
        for m in re.finditer(
            r"https?://images\.orgill\.com/weblarge/[^\"]+\.jpg",
            html_text or "",
            flags=re.I,
        ):
            u = html.unescape(m.group(0))
            if u not in imgs:
                imgs.append(u)

        # Extract additional metadata
        country = self._grab_id(
            soup, html_text, "cphMainContent_ctl00_lblCountryOfOrigin"
        )
        item_number = self._grab_id(
            soup, html_text, "cphMainContent_ctl00_lblOrgillItemNumber"
        )

        return {
            "title": title,
            "brand_hint": brand,
            "description": description,
            "benefits": benefits,
            "gallery_images": imgs,
            "country_of_origin": country,
            "orgill_item_number": item_number,
        }
