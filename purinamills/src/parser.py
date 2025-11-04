"""
Page parsing for Purinamills collector.

Extracts comprehensive product data from both shop.purinamills.com and www.purinamills.com pages
for Shopify product import.
"""

import re
import json
from typing import Dict, Any, List, Optional
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
        """Clean and normalize URL, removing size parameters."""
        if not url:
            return ""
        url = url.strip().strip('"').strip("'")

        # Make absolute
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = f"{origin.rstrip('/')}{url}"
        elif not url.startswith("http"):
            url = f"{origin.rstrip('/')}/{url.lstrip('/')}"

        # Convert to HTTPS
        url = url.replace("http://", "https://")

        # Remove size parameters (_300x, _400x, etc.) to get full-size image
        url = re.sub(r'(_\d+x\d+|\d+x\.jpg|\d+x\.png)', '', url)

        # Remove query parameters
        if "?" in url:
            url = url.split("?")[0]

        return url

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
        return "shop"

    def _extract_shop_variants(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract product variants from shop site (sizes/options)."""
        variants = []

        # Look for variant select dropdown
        variant_select = soup.find('select', {'name': 'id'})
        if variant_select:
            options = variant_select.find_all('option')
            for opt in options:
                value = opt.get('value', '')
                text = opt.get_text(strip=True)

                # Parse "50 LB / BG - $32.99"
                match = re.match(r'(.+?)\s*-\s*\$?([\d,.]+)', text)
                if match:
                    option_text = match.group(1).strip()
                    price = match.group(2).replace(',', '')

                    # Split option text (e.g., "50 LB / BG" -> size="50 LB", material="BG")
                    parts = [p.strip() for p in option_text.split('/')]

                    variants.append({
                        'variant_id': value,
                        'option_text': option_text,
                        'size': parts[0] if len(parts) > 0 else '',
                        'material': parts[1] if len(parts) > 1 else '',
                        'price': price
                    })

        # Also look for JSON variant data in scripts
        for script in soup.find_all('script'):
            if script.string and 'variant' in script.string.lower():
                try:
                    # Try to extract JSON variant data
                    json_match = re.search(r'var\s+\w+\s*=\s*({.*?variants.*?});', script.string, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        if 'variants' in data:
                            for var in data['variants']:
                                if isinstance(var, dict):
                                    variants.append({
                                        'variant_id': var.get('id', ''),
                                        'sku': var.get('sku', ''),
                                        'price': str(var.get('price', 0) / 100) if 'price' in var else '',
                                        'option1': var.get('option1', ''),
                                        'option2': var.get('option2', ''),
                                        'option3': var.get('option3', ''),
                                    })
                except:
                    pass

        return variants

    def _extract_shop_images(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract full-size gallery images from shop site (thumbnails only).

        Parses the thumbnail gallery structure:
        <ul class="thumbnail-list">
          <li class="thumbnail-list__item">
            <button class="thumbnail">
              <img src="//shop.purinamills.com/cdn/shop/files/..." alt="..." />
            </button>
          </li>
        </ul>
        """
        images = []
        seen = set()

        # Primary method: Extract from thumbnail gallery
        # Look for thumbnail list (the authoritative source for gallery images)
        thumbnail_list = soup.find('ul', class_=lambda x: x and 'thumbnail-list' in str(x))

        if thumbnail_list:
            # Find all thumbnail buttons
            for li in thumbnail_list.find_all('li', class_=lambda x: x and 'thumbnail-list__item' in str(x)):
                # Find the img inside the button
                img = li.find('img')
                if img:
                    src = img.get('src') or ''
                    if src:
                        # Clean URL - _clean_url removes ALL query parameters
                        # to get the largest image available from Shopify CDN
                        # Example: //shop.purinamills.com/cdn/shop/files/image.jpg?v=1748440581&width=416
                        # Becomes: https://shop.purinamills.com/cdn/shop/files/image.jpg
                        clean = self._clean_url(src, self.shop_origin)

                        if clean and clean not in seen:
                            images.append(clean)
                            seen.add(clean)

        # Fallback: If no thumbnails found, try JSON-LD
        if not images:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        imgs = data.get('image', [])
                        if isinstance(imgs, list):
                            for img_url in imgs:
                                clean = self._clean_url(str(img_url), self.shop_origin)
                                if clean and clean not in seen:
                                    images.append(clean)
                                    seen.add(clean)
                        elif isinstance(imgs, str):
                            clean = self._clean_url(imgs, self.shop_origin)
                            if clean and clean not in seen:
                                images.append(clean)
                                seen.add(clean)
                except:
                    pass

        return images

    def _extract_shop_tab_content(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract content from tabs (Features & Benefits, Nutrients, Feeding Directions)."""
        tab_content = {}

        # Look for tab container
        tabs_container = soup.find('div', class_=lambda x: x and 'tab' in str(x).lower())

        if tabs_container:
            # Find all sections that might be tab content
            sections = tabs_container.find_all(['div', 'section'], recursive=True)

            for section in sections:
                section_text = section.get_text(strip=True)
                section_html = str(section)

                # Features & Benefits
                if any(term in section_text.lower() for term in ['features', 'benefit']):
                    # Extract as HTML list
                    ul = section.find('ul')
                    if ul:
                        tab_content['features_benefits'] = str(ul)
                    elif section_text:
                        # Convert to list
                        items = [li.strip() for li in section_text.split('\n') if li.strip() and len(li.strip()) > 10]
                        if items:
                            tab_content['features_benefits'] = '<ul>\n' + '\n'.join(f'  <li>{item}</li>' for item in items) + '\n</ul>'

                # Nutrients / Guaranteed Analysis
                if any(term in section_text.lower() for term in ['nutrient', 'guaranteed analysis', 'analysis']):
                    table = section.find('table')
                    if table:
                        tab_content['nutrients'] = str(table)
                    else:
                        tab_content['nutrients'] = section_html

                # Feeding Directions
                if any(term in section_text.lower() for term in ['feeding direction', 'directions for use', 'how to feed']):
                    ul = section.find('ul')
                    if ul:
                        tab_content['feeding_directions'] = str(ul)
                    elif section_text:
                        # Convert to list
                        items = [li.strip() for li in section_text.split('\n') if li.strip() and len(li.strip()) > 15]
                        if items:
                            tab_content['feeding_directions'] = '<ul>\n' + '\n'.join(f'  <li>{item}</li>' for item in items) + '\n</ul>'

        # Fallback: search entire document for these sections
        if not tab_content.get('features_benefits'):
            for elem in soup.find_all(string=re.compile(r'features?\s*(&|and)?\s*benefits?', re.I)):
                parent = elem.parent
                while parent:
                    ul = parent.find('ul')
                    if ul:
                        tab_content['features_benefits'] = str(ul)
                        break
                    parent = parent.parent
                    if parent and parent.name in ['body', 'html']:
                        break

        if not tab_content.get('nutrients'):
            for elem in soup.find_all(string=re.compile(r'guaranteed analysis|nutrients?', re.I)):
                parent = elem.parent
                while parent:
                    table = parent.find('table')
                    if table:
                        tab_content['nutrients'] = str(table)
                        break
                    parent = parent.parent
                    if parent and parent.name in ['body', 'html']:
                        break

        if not tab_content.get('feeding_directions'):
            for elem in soup.find_all(string=re.compile(r'feeding directions?|directions for use', re.I)):
                parent = elem.parent
                while parent:
                    ul = parent.find('ul')
                    if ul:
                        tab_content['feeding_directions'] = str(ul)
                        break
                    parent = parent.parent
                    if parent and parent.name in ['body', 'html']:
                        break

        return tab_content

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

        # Extract variants
        variants = self._extract_shop_variants(soup)

        # Extract gallery images (full-size)
        gallery_images = self._extract_shop_images(soup)

        # Extract tab content
        tab_content = self._extract_shop_tab_content(soup)

        return {
            "title": title,
            "brand_hint": brand_hint,
            "description": description,
            "variants": variants,
            "gallery_images": gallery_images,
            "features_benefits": tab_content.get("features_benefits", ""),
            "nutrients": tab_content.get("nutrients", ""),
            "feeding_directions": tab_content.get("feeding_directions", ""),
            "site_source": "shop"
        }

    def _extract_www_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract full-size product images from www site."""
        images = []
        seen = set()

        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if src:
                clean = self._clean_url(src, self.www_origin)
                # Filter for product/feed images
                if clean and any(x in clean.lower() for x in ['product', 'feed', 'bag', 'amplify', 'equine', 'horse']):
                    if clean not in seen and not any(x in clean.lower() for x in ['logo', 'icon', 'favicon', 'banner', 'mic-w']):
                        images.append(clean)
                        seen.add(clean)

        return images

    def _extract_www_documents(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract documents from Additional Materials section."""
        documents = []

        # Look for document links (PDFs, etc.)
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Check if it's a document link
            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '/document/', '/media/']):
                clean_url = self._clean_url(href, self.www_origin)
                if clean_url:
                    documents.append({
                        'title': text or 'Document',
                        'url': clean_url,
                        'type': 'pdf' if '.pdf' in href.lower() else 'document'
                    })

        return documents

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

        # Extract description - try meta description first
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = text_only(meta_desc["content"])

        # Try DOM elements if no meta description
        if not description or len(description) < 100:
            desc_candidates = soup.select('[class*="overview"], [class*="description"], [id*="overview"], p')
            for el in desc_candidates:
                desc_text = text_only(el.get_text(" ", strip=True))
                if len(desc_text) > 100 and any(word in desc_text.lower() for word in ["feed", "formulated", "nutrition", "supplement"]):
                    description = desc_text
                    break

        # Extract features/benefits
        features_benefits = ""
        feature_sections = soup.select('[class*="benefit"], [class*="feature"], [class*="key-point"]')
        if feature_sections:
            items = []
            for section in feature_sections:
                for li in section.find_all("li"):
                    benefit_text = text_only(li.get_text(" ", strip=True))
                    if benefit_text and len(benefit_text) > 15:
                        items.append(benefit_text)
            if items:
                features_benefits = '<ul>\n' + '\n'.join(f'  <li>{item}</li>' for item in items) + '\n</ul>'

        # Extract guaranteed analysis
        nutrients = ""
        nutrition_section = soup.find(string=re.compile(r"guaranteed analysis", re.I))
        if nutrition_section:
            parent = nutrition_section.parent
            while parent:
                table = parent.find('table')
                if table:
                    nutrients = str(table)
                    break
                parent = parent.parent
                if parent and parent.name in ["body", "html"]:
                    break

        # Extract feeding directions
        feeding_directions = ""
        directions_section = soup.find(string=re.compile(r"feeding directions?|how to feed", re.I))
        if directions_section:
            parent = directions_section.parent
            while parent:
                ul = parent.find('ul')
                if ul:
                    feeding_directions = str(ul)
                    break
                # Also look for paragraphs with directions
                text = text_only(parent.get_text(" ", strip=True))
                if 'feed' in text.lower() and len(text) > 100:
                    feeding_directions = f'<p>{text}</p>'
                    break
                parent = parent.parent
                if parent and parent.name in ["body", "html"]:
                    break

        # Extract images
        gallery_images = self._extract_www_images(soup)

        # Extract documents (ALWAYS scrape these)
        documents = self._extract_www_documents(soup)

        return {
            "title": title,
            "brand_hint": brand_hint,
            "description": description,
            "features_benefits": features_benefits,
            "nutrients": nutrients,
            "feeding_directions": feeding_directions,
            "gallery_images": gallery_images,
            "documents": documents,
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
                - description: Product description
                - variants: List of product variants (shop site only)
                - gallery_images: List of image URLs
                - features_benefits: HTML content
                - nutrients: HTML table or content
                - feeding_directions: HTML content
                - documents: List of document objects (www site)
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
