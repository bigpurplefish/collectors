"""
Parser for Cambridge public website (www.cambridgepavers.com).

Extracts all product data from JS-rendered DOM via Playwright:
- Hero image
- Gallery images (lightbox, 20+ images)
- Product description
- Specifications
- Title, collection, colors, swatch images
"""

import logging
import re
import sys
import os
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

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

    def scrape_page(
        self,
        product_url: str,
        log: Callable = print,
        shared_browser=None
    ) -> Dict[str, Any]:
        """
        Scrape a product page using Playwright (single navigation).

        Navigates to the product URL, waits for JS rendering, then extracts
        all fields from the rendered DOM. Also opens the lightbox to extract
        all gallery images (20+).

        Args:
            product_url: Full product URL to visit
            log: Logging function
            shared_browser: Optional shared Playwright browser instance (avoids asyncio conflicts)

        Returns:
            Dictionary with extracted data:
            - hero_image: URL of hero image
            - gallery_images: List of gallery image URLs
            - description: Product description text
            - specifications: Product specifications text
            - title: Product title
            - collection: Collection name
            - colors: List of color names
            - color_swatches: Dict mapping color name to swatch image URL
        """
        result = {
            "hero_image": "",
            "gallery_images": [],
            "description": "",
            "specifications": "",
            "title": "",
            "collection": "",
            "colors": [],
            "color_swatches": {},
        }

        playwright_instance = None
        page = None

        try:
            # Use shared browser if provided, otherwise create new instance
            if shared_browser:
                browser = shared_browser
                page = browser.new_page()
                should_close_browser = False
            else:
                playwright_instance = sync_playwright().start()
                browser = playwright_instance.chromium.launch(headless=True)
                page = browser.new_page()
                should_close_browser = True

            # Navigate to product page (retry once on timeout)
            log(f"    Navigating to {product_url}")
            try:
                page.goto(product_url, wait_until="networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                logging.warning(f"Page load timeout, retrying: {product_url}")
                log(f"    Page load timeout, retrying...")
                time.sleep(3)
                page.goto(product_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # Extract text fields from rendered DOM
            fields = page.evaluate("""
                (() => {
                    const data = {};

                    // Title: h1.page-title strong, fallback title tag, fallback h1
                    const pageTitle = document.querySelector('h1.page-title strong');
                    if (pageTitle) {
                        data.title = pageTitle.textContent.trim();
                    } else {
                        const titleTag = document.querySelector('title');
                        if (titleTag) {
                            data.title = titleTag.textContent.trim();
                        } else {
                            const h1 = document.querySelector('h1');
                            data.title = h1 ? h1.textContent.trim() : '';
                        }
                    }

                    // Collection: h4 span
                    const h4 = document.querySelector('h4');
                    if (h4) {
                        const span = h4.querySelector('span');
                        data.collection = span ? span.textContent.trim() : '';
                    } else {
                        data.collection = '';
                    }

                    // Description: strong containing "Description:", get parent text minus label
                    data.description = '';
                    const allStrong = document.querySelectorAll('strong');
                    for (const s of allStrong) {
                        if (/description:/i.test(s.textContent)) {
                            const parent = s.parentElement;
                            if (parent) {
                                let text = parent.textContent.trim();
                                text = text.replace(/^Description:\\s*/i, '');
                                data.description = text.trim();
                            }
                            break;
                        }
                    }

                    // Specifications: strong containing "Specifications:", get sibling p or parent text
                    data.specifications = '';
                    for (const s of allStrong) {
                        if (/specifications:/i.test(s.textContent)) {
                            const parent = s.parentElement;
                            if (parent) {
                                const p = parent.querySelector('p');
                                if (p) {
                                    data.specifications = p.textContent.trim();
                                } else {
                                    let text = parent.textContent.trim();
                                    text = text.replace(/^Specifications:\\s*/i, '');
                                    data.specifications = text.trim();
                                }
                            }
                            break;
                        }
                    }

                    // Colors + swatches: strong containing "Color Selection:", sibling row, col-* divs
                    data.colors = [];
                    data.color_swatches = {};
                    for (const s of allStrong) {
                        if (/color selection:/i.test(s.textContent)) {
                            const parentRow = s.closest('.row');
                            if (parentRow) {
                                const swatchesRow = parentRow.nextElementSibling;
                                if (swatchesRow && swatchesRow.classList.contains('row')) {
                                    const cols = swatchesRow.querySelectorAll('[class*="col-"]');
                                    for (const col of cols) {
                                        const nameSpan = col.querySelector('span.small');
                                        if (nameSpan) {
                                            const name = nameSpan.textContent.trim();
                                            if (name) {
                                                data.colors.push(name);
                                                const img = col.querySelector('img');
                                                if (img && img.src) {
                                                    data.color_swatches[name] = img.src;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            break;
                        }
                    }

                    return data;
                })()
            """)

            result["title"] = fields.get("title", "")
            result["collection"] = fields.get("collection", "")
            result["description"] = fields.get("description", "")
            result["specifications"] = fields.get("specifications", "")
            result["colors"] = fields.get("colors", [])

            # Normalize swatch URLs
            raw_swatches = fields.get("color_swatches", {})
            for name, url in raw_swatches.items():
                result["color_swatches"][name] = self._normalize_image_url(url)

            # Extract hero image from .image-box
            try:
                hero_src = page.evaluate("""
                    (() => {
                        const box = document.querySelector('.image-box');
                        if (!box) return '';
                        const img = box.querySelector('img[src]');
                        return img ? img.src : '';
                    })()
                """)
                if hero_src:
                    result["hero_image"] = self._normalize_image_url(hero_src)
                    log(f"    Hero image: {result['hero_image']}")
            except Exception as e:
                log(f"    Hero image extraction failed: {e}")

            # Extract gallery images from lightbox
            gallery_urls = []
            try:
                first_image = page.locator("a.popup-img").first
                image_count = first_image.count()
                log(f"    Found {image_count} popup-img links")

                if image_count > 0:
                    log(f"    Clicking first image to open lightbox...")
                    page.evaluate("document.querySelector('a.popup-img').click()")
                    time.sleep(1)

                    log(f"    Waiting for lightbox...")
                    page.wait_for_selector(".mfp-img", timeout=5000)

                    counter = page.locator(".mfp-counter").text_content()
                    log(f"    Lightbox counter: {counter}")

                    if " of " in counter:
                        total_images = int(counter.split(" of ")[1])
                    else:
                        total_images = 10

                    log(f"    Extracting {total_images} images from lightbox...")

                    for i in range(total_images):
                        img_element = page.locator(".mfp-img")
                        if img_element.count() > 0:
                            src = img_element.get_attribute("src")
                            if src:
                                url = self._normalize_image_url(src)
                                gallery_urls.append(url)
                                log(f"      Position {i+1}: {url}")

                        if i < total_images - 1:
                            next_button = page.locator(".mfp-arrow-right")
                            if next_button.count() > 0:
                                next_button.click()
                                time.sleep(0.5)

                    # Deduplicate while preserving order
                    original_count = len(gallery_urls)
                    gallery_urls = list(dict.fromkeys(gallery_urls))
                    if original_count > len(gallery_urls):
                        log(f"    Removed {original_count - len(gallery_urls)} duplicates")
                else:
                    log(f"    No popup-img links found, skipping lightbox extraction")

            except PlaywrightTimeoutError as e:
                log(f"    Lightbox timeout: {e}")

            result["gallery_images"] = gallery_urls

        except Exception as e:
            import traceback
            err_msg = f"Playwright scrape_page error for {product_url}: {e}"
            log(f"    {err_msg}")
            logging.error(err_msg)
            logging.error(traceback.format_exc())

        finally:
            # Close page (always) and browser (only if we created it)
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if playwright_instance:
                try:
                    browser.close()
                    playwright_instance.stop()
                except Exception:
                    pass

        return result

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
