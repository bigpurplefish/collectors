"""
Page parsing for Purinamills collector.

Extracts product data from both shop.purinamills.com and www.purinamills.com pages.
"""

import re
import json
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import text_only


class PurinamillsParser:
    """Parses Purinamills product pages from both shop and www sites."""

    def __init__(self, config: dict):
        """
        Initialize parser.

        Args:
            config: Site configuration dict
        """
        self.shop_origin = config.get("shop_origin", "https://shop.purinamills.com")
        self.www_origin = config.get("www_origin", "https://www.purinamills.com")

    def _clean_url(self, url: str, origin: str) -> str:
        """Clean and normalize image URL."""
        if not url:
            return ""
        url = url.strip().strip('"').strip("'")
        # Remove query parameters
        qpos = url.find("?")
        if qpos != -1:
            url = url[:qpos]
        # Make absolute
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = f"{origin.rstrip('/')}{url}"
        elif not url.startswith("http"):
            url = f"{origin.rstrip('/')}/{url.lstrip('/')}"
        return url.replace("http://", "https://")

    def _detect_site_type(self, soup: BeautifulSoup, html_text: str) -> str:
        """Detect whether this is a shop or www site page."""
        # Check for Shopify-specific markers
        if 'Shopify' in html_text or 'shopify' in html_text:
            return "shop"
        # Check canonical URL
        canon = soup.find('link', rel='canonical')
        if canon and canon.get('href'):
            if 'shop.purinamills.com' in canon['href']:
                return "shop"
            elif 'www.purinamills.com' in canon['href']:
                return "www"
        # Check OG URL
        og_url = soup.find('meta', property='og:url')
        if og_url and og_url.get('content'):
            if 'shop.purinamills.com' in og_url['content']:
                return "shop"
            elif 'www.purinamills.com' in og_url['content']:
                return "www"
        # Default to shop
        return "shop"

    def _parse_shop_site(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse product page from shop.purinamills.com (Shopify)."""
        # Extract title
        title = ""
        title_el = soup.find("h1") or soup.select_one(".product__title")
        if title_el:
            title = text_only(title_el.get_text(strip=True))
            # Remove duplication if title appears twice
            if title and len(title) > 30:
                mid = len(title) // 2
                if title[:mid] == title[mid:]:
                    title = title[:mid]

        # Extract brand
        brand_hint = "Purina"
        if "®" in title:
            brand_hint = title.split("®")[0].strip()

        # Extract description - try JSON-LD first
        description = ""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    description = data.get("description", "")
                    if description:
                        break
            except:
                pass

        # Fallback to DOM
        if not description:
            desc_el = soup.select_one(".product__description") or soup.select_one(".product-description")
            if desc_el:
                description = text_only(desc_el.get_text(" ", strip=True))

        # Extract benefits (bullet lists)
        benefits: List[Dict[str, str]] = []
        for ul in soup.find_all("ul"):
            # Skip navigation and footer lists
            if any(cls in str(ul.get("class", [])) for cls in ["nav", "menu", "footer", "list-menu"]):
                continue
            for li in ul.find_all("li", recursive=False):
                benefit_text = text_only(li.get_text(" ", strip=True))
                if benefit_text and len(benefit_text) > 15:  # Filter out short items
                    benefits.append({"title": "", "description": benefit_text})
            if len(benefits) >= 3:  # Found meaningful list
                break

        # Extract gallery images - try JSON-LD first
        gallery_images: List[str] = []
        seen = set()

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    imgs = data.get("image", [])
                    if isinstance(imgs, list):
                        for img_url in imgs:
                            clean = self._clean_url(str(img_url), self.shop_origin)
                            if clean and clean not in seen:
                                gallery_images.append(clean)
                                seen.add(clean)
                    elif isinstance(imgs, str):
                        clean = self._clean_url(imgs, self.shop_origin)
                        if clean and clean not in seen:
                            gallery_images.append(clean)
                            seen.add(clean)
            except:
                pass

        # Extract from DOM - look for product images
        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src") or ""
            if src:
                clean = self._clean_url(src, self.shop_origin)
                # Filter for product images (exclude logos, icons, etc.)
                if clean and any(x in clean.lower() for x in ["product", "cdn.shop", "/products/", "_horse-", "_cattle-"]):
                    if clean not in seen and not any(x in clean.lower() for x in ["logo", "icon", "favicon"]):
                        gallery_images.append(clean)
                        seen.add(clean)

        # Extract nutrition/guaranteed analysis
        nutrition_text = ""
        nutrition_section = soup.find(string=re.compile(r"guaranteed analysis", re.I))
        if nutrition_section:
            parent = nutrition_section.parent
            while parent and not nutrition_text:
                parent_text = text_only(parent.get_text(" ", strip=True))
                if "guaranteed analysis" in parent_text.lower() and len(parent_text) > 50:
                    nutrition_text = parent_text
                    break
                parent = parent.parent
                if parent and parent.name in ["body", "html"]:
                    break

        # Extract feeding directions
        directions_for_use = ""
        directions_section = soup.find(string=re.compile(r"feeding directions?|directions for use", re.I))
        if directions_section:
            parent = directions_section.parent
            while parent and not directions_for_use:
                parent_text = text_only(parent.get_text(" ", strip=True))
                if any(x in parent_text.lower() for x in ["feeding direction", "directions for use"]) and len(parent_text) > 50:
                    directions_for_use = parent_text
                    break
                parent = parent.parent
                if parent and parent.name in ["body", "html"]:
                    break

        return {
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "gallery_images": gallery_images,
            "nutrition_text": nutrition_text,
            "directions_for_use": directions_for_use,
            "site_source": "shop"
        }

    def _parse_www_site(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse product page from www.purinamills.com (information site)."""
        # Extract title
        title = ""
        title_el = soup.find("h1")
        if title_el:
            title = text_only(title_el.get_text(strip=True))

        # Extract brand
        brand_hint = "Purina"
        if "®" in title:
            brand_hint = title.split("®")[0].strip()

        # Extract description - look for product overview or meta description
        description = ""

        # Try meta description first
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = text_only(meta_desc["content"])

        # Try DOM elements if no meta description
        if not description or len(description) < 100:
            desc_candidates = soup.select('[class*="overview"], [class*="description"], [id*="overview"], p')
            for el in desc_candidates:
                desc_text = text_only(el.get_text(" ", strip=True))
                if len(desc_text) > 100 and any(word in desc_text.lower() for word in ["feed", "formulated", "nutrition"]):
                    description = desc_text
                    break

        # Extract benefits/features
        benefits: List[Dict[str, str]] = []
        feature_sections = soup.select('[class*="benefit"], [class*="feature"], [class*="key-point"]')
        for section in feature_sections:
            for li in section.find_all("li"):
                benefit_text = text_only(li.get_text(" ", strip=True))
                if benefit_text and len(benefit_text) > 15:
                    benefits.append({"title": "", "description": benefit_text})

        # If no benefits found, look for any meaningful lists
        if not benefits:
            for ul in soup.find_all("ul"):
                if any(cls in str(ul.get("class", [])) for cls in ["nav", "menu", "footer"]):
                    continue
                for li in ul.find_all("li", recursive=False):
                    benefit_text = text_only(li.get_text(" ", strip=True))
                    if benefit_text and len(benefit_text) > 15:
                        benefits.append({"title": "", "description": benefit_text})
                if len(benefits) >= 3:
                    break

        # Extract images - look for product images
        gallery_images: List[str] = []
        seen = set()

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if src:
                clean = self._clean_url(src, self.www_origin)
                # Filter for product/feed images
                if clean and any(x in clean.lower() for x in ["product", "feed", "bag", "purina"]):
                    if clean not in seen and not any(x in clean.lower() for x in ["logo", "icon", "favicon", "banner"]):
                        gallery_images.append(clean)
                        seen.add(clean)

        # Extract guaranteed analysis
        nutrition_text = ""
        nutrition_section = soup.find(string=re.compile(r"guaranteed analysis", re.I))
        if nutrition_section:
            parent = nutrition_section.parent
            while parent and not nutrition_text:
                parent_text = text_only(parent.get_text(" ", strip=True))
                if "guaranteed analysis" in parent_text.lower() and len(parent_text) > 50:
                    nutrition_text = parent_text
                    break
                parent = parent.parent
                if parent and parent.name in ["body", "html"]:
                    break

        # Extract feeding directions
        directions_for_use = ""
        directions_section = soup.find(string=re.compile(r"feeding directions?|how to feed", re.I))
        if directions_section:
            parent = directions_section.parent
            while parent and not directions_for_use:
                parent_text = text_only(parent.get_text(" ", strip=True))
                if any(x in parent_text.lower() for x in ["feeding direction", "how to feed"]) and len(parent_text) > 50:
                    directions_for_use = parent_text
                    break
                parent = parent.parent
                if parent and parent.name in ["body", "html"]:
                    break

        return {
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "gallery_images": gallery_images,
            "nutrition_text": nutrition_text,
            "directions_for_use": directions_for_use,
            "site_source": "www"
        }

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Extract product information from HTML.

        Automatically detects site type (shop vs www) and uses appropriate parser.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data:
                - title: Product title
                - brand_hint: Brand name
                - benefits: List of product benefits
                - description: Product description
                - gallery_images: List of image URLs
                - nutrition_text: Nutrition/guaranteed analysis
                - directions_for_use: Feeding directions
                - site_source: "shop" or "www"
        """
        soup = BeautifulSoup(html_text or "", "html.parser")

        # Detect site type
        site_type = self._detect_site_type(soup, html_text)

        # Parse using appropriate method
        if site_type == "shop":
            return self._parse_shop_site(soup)
        else:
            return self._parse_www_site(soup)
