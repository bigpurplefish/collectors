"""
Parser for Cambridge dealer portal (shop.cambridgepavers.com).

Requires authentication and uses Playwright for JavaScript rendering.

Extracts:
- Product gallery images
- Item weight
- Sales unit (unit of sale)
- Cost (price)
- Vendor SKU (model number)
"""

import re
import time
from typing import Dict, List, Any, Optional, Callable
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup


class CambridgePortalParser:
    """Parser for Cambridge dealer portal (SuiteCommerce JavaScript app)."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize parser.

        Args:
            config: Site configuration dictionary
        """
        self.config = config
        self.portal_origin = config.get("portal_origin", "https://shop.cambridgepavers.com")
        self.username = config.get("portal_username", "")
        self.password = config.get("portal_password", "")

        # Browser state
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._logged_in = False

    def __enter__(self):
        """Context manager entry - start browser."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser."""
        self.close()

    def login(self, log: Callable = print) -> bool:
        """
        Login to dealer portal.

        Args:
            log: Logging function

        Returns:
            True if login successful, False otherwise
        """
        if self._logged_in:
            log("Already logged in to dealer portal")
            return True

        log("Logging in to Cambridge dealer portal...")

        try:
            # Start Playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            context = self._browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            self._page = context.new_page()

            # Navigate to portal
            self._page.goto(self.portal_origin, wait_until="networkidle", timeout=30000)

            # Wait for page to render
            time.sleep(3)

            # Look for login form
            # SuiteCommerce login forms typically have email/password fields
            try:
                # Try to find and fill login form
                email_input = self._page.locator('input[type="email"], input[name="email"], input#login-email')
                if email_input.count() > 0:
                    email_input.fill(self.username)
                    log(f"  ✓ Filled username: {self.username}")

                password_input = self._page.locator('input[type="password"], input[name="password"], input#login-password')
                if password_input.count() > 0:
                    password_input.fill(self.password)
                    log("  ✓ Filled password")

                # Click login button
                login_button = self._page.locator('button[type="submit"], button:has-text("Log In"), button:has-text("Sign In")')
                if login_button.count() > 0:
                    login_button.click()
                    log("  ✓ Clicked login button")

                    # Wait for navigation after login
                    self._page.wait_for_load_state("networkidle", timeout=30000)
                    time.sleep(3)

                    self._logged_in = True
                    log("✓ Successfully logged in to dealer portal")
                    return True

            except Exception as e:
                log(f"  ❌ Login failed: {e}")
                return False

        except Exception as e:
            log(f"❌ Failed to start browser or navigate: {e}")
            return False

        return False

    def fetch_product_page(self, product_url: str, log: Callable = print) -> Optional[str]:
        """
        Fetch product page HTML using Playwright.

        Args:
            product_url: Product URL (relative or absolute)
            log: Logging function

        Returns:
            HTML content or None if failed
        """
        if not self._logged_in:
            if not self.login(log):
                log("❌ Cannot fetch product page: not logged in")
                return None

        try:
            # Construct full URL
            if product_url.startswith("/"):
                full_url = f"{self.portal_origin}{product_url}"
            else:
                full_url = product_url

            log(f"Fetching portal page: {full_url}")

            # Navigate to product page
            self._page.goto(full_url, wait_until="networkidle", timeout=30000)

            # Wait for page to render (SuiteCommerce apps need time to load)
            time.sleep(3)

            # Get page HTML
            html = self._page.content()
            log("  ✓ Page loaded successfully")

            return html

        except PlaywrightTimeoutError:
            log(f"  ❌ Timeout loading page: {product_url}")
            return None
        except Exception as e:
            log(f"  ❌ Error fetching page: {e}")
            return None

    def parse_product_page(self, html: str, log: Callable = print) -> Dict[str, Any]:
        """
        Parse product page HTML from dealer portal.

        Args:
            html: HTML content
            log: Logging function

        Returns:
            Dictionary with extracted data:
            - gallery_images: List of product image URLs
            - weight: Item weight (for cube unit)
            - cost: Product cost/price
            - model_number: Vendor SKU / model number

            Note: sales_unit is no longer extracted from portal - it comes from input file
        """
        soup = BeautifulSoup(html, "lxml")

        result = {
            "gallery_images": self._extract_gallery_images(soup, log),
            "weight": self._extract_weight(soup, log),
            # sales_unit extraction removed - now sourced from input file
            "cost": self._extract_cost(soup, log),
            "model_number": self._extract_model_number(soup, log),
        }

        return result

    def _extract_gallery_images(self, soup: BeautifulSoup, log: Callable) -> List[str]:
        """
        Extract product gallery images using Playwright.

        Only captures images from the product gallery carousel in the order they appear.

        Args:
            soup: BeautifulSoup object (not used, kept for compatibility)
            log: Logging function

        Returns:
            List of image URLs in gallery order
        """
        images = []

        if not self._page:
            log("  ❌ No Playwright page available")
            return images

        try:
            # Wait for gallery to load - specific selector for bxSlider with longer timeout
            has_carousel = False
            try:
                self._page.wait_for_selector(".bx-viewport ul.bxslider li img", timeout=10000)
                has_carousel = True
                # Give extra time for images to load
                time.sleep(0.5)
            except PlaywrightTimeoutError:
                log("  ⚠ Carousel not found, trying fallback image")

            if has_carousel:
                # Extract gallery images from bxSlider carousel
                # Selector: .bx-viewport ul.bxslider li img (excluding clones)
                gallery_images = self._page.query_selector_all(".bx-viewport ul.bxslider li:not(.bx-clone) img")

                if gallery_images:
                    # Extract src attributes in order
                    for img in gallery_images:
                        src = img.get_attribute("src")
                        if src:
                            # Skip thumbnails (resizeid=4), we want full images (resizeid=5)
                            if "resizeid=4" in src:
                                continue

                            # Skip UI elements
                            if any(skip in src.lower() for skip in ["icon", "logo", "button", "sprite"]):
                                continue

                            # Normalize URL and remove query params
                            full_url = self._normalize_url(src)
                            # Strip resize params to get base URL
                            base_url = full_url.split("?")[0]

                            if base_url and base_url not in images:
                                images.append(base_url)

                    if images:
                        log(f"  Found {len(images)} gallery images from carousel")
                        return images

            # Fallback: Try to get the main product image when no carousel found
            try:
                main_img = self._page.query_selector(".product-details-image-gallery-detailed-image img.center-block")
                if main_img:
                    src = main_img.get_attribute("src")
                    if src:
                        # Skip UI elements
                        if not any(skip in src.lower() for skip in ["icon", "logo", "button", "sprite"]):
                            # Normalize URL and remove query params
                            full_url = self._normalize_url(src)
                            # Strip resize params to get base URL
                            base_url = full_url.split("?")[0]

                            if base_url:
                                images.append(base_url)
                                log(f"  Found 1 main product image (fallback)")
                                return images

                log("  ⚠ Gallery images not found")
                return images

            except Exception as e:
                log(f"  ⚠ No main product image found: {e}")
                return images

        except Exception as e:
            log(f"  ⚠ Error extracting gallery images: {e}")
            return images

    def _extract_weight(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract item weight from custom PDP fields using Playwright.

        Args:
            soup: BeautifulSoup object (not used, kept for compatibility)
            log: Logging function

        Returns:
            Weight string or empty string
        """
        if not self._page:
            log("  ❌ No Playwright page available")
            return ""

        try:
            # Wait for custom fields to load with longer timeout
            self._page.wait_for_selector("span.custom-pdp-fields-label", timeout=10000)

            # Give extra time for JavaScript to render
            time.sleep(0.5)

            # Get all custom field labels
            field_labels = self._page.query_selector_all("span.custom-pdp-fields-label")

            if not field_labels:
                log("  ⚠ No custom PDP fields found")
                return ""

            for label in field_labels:
                text = label.text_content().strip()
                if "ITEM WEIGHT:" in text.upper():
                    # Extract the weight value after the label
                    # Format: "ITEM WEIGHT: 3078 lb" or "ITEM WEIGHT: 2400 lb"
                    match = re.search(r"ITEM WEIGHT:\s*(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kgs|oz)", text, re.IGNORECASE)
                    if match:
                        weight = f"{match.group(1)} {match.group(2)}"
                        log(f"  Found weight: {weight}")
                        return weight

            log("  ⚠ Weight field exists but value not found")
            return ""

        except PlaywrightTimeoutError:
            log("  ⚠ Weight not found: timeout waiting for custom fields")
            return ""
        except Exception as e:
            log(f"  ⚠ Weight not found: {e}")
            return ""

    def _extract_sales_unit(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract sales unit / unit of sale from custom PDP fields.

        Args:
            soup: BeautifulSoup object
            log: Logging function

        Returns:
            Sales unit string or empty string
        """
        # Look for "SALE UNIT:" in custom PDP fields
        # Format: <span class="custom-pdp-fields-label">SALE UNIT: Cube</span>
        for span in soup.find_all("span", class_="custom-pdp-fields-label"):
            text = span.get_text(strip=True)
            if "SALE UNIT:" in text.upper():
                # Extract the value after the label
                # Format: "SALE UNIT: Cube"
                match = re.search(r"SALE UNIT:\s*(.+)", text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        log(f"  Found sales unit: {value}")
                        return value

        log("  ⚠ Sales unit not found")
        return ""

    def _extract_cost(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract product cost/price using Playwright.

        Args:
            soup: BeautifulSoup object (not used, kept for compatibility)
            log: Logging function

        Returns:
            Cost string or empty string
        """
        if not self._page:
            log("  ❌ No Playwright page available")
            return ""

        try:
            # Wait for price element to load with longer timeout
            # Format: <span class="product-views-price-lead" itemprop="price" data-rate="448.6"> $448.60 </span>
            self._page.wait_for_selector("span.product-views-price-lead[itemprop='price']", timeout=10000)

            # Give extra time for JavaScript to render
            time.sleep(0.5)

            # Get price element
            price_element = self._page.query_selector("span.product-views-price-lead[itemprop='price']")
            if price_element:
                # Try data-rate attribute first (most reliable)
                data_rate = price_element.get_attribute("data-rate")
                if data_rate:
                    try:
                        cost = f"${float(data_rate):.2f}"
                        log(f"  Found cost from data-rate: {cost}")
                        return cost
                    except (ValueError, TypeError):
                        pass

                # Fallback: Get text content and clean it
                text = price_element.text_content().strip()
                # Extract just the numeric value with dollar sign
                # Format: "$448.60" or "$448.60  " (with trailing spaces)
                match = re.search(r"\$\s*(\d+(?:\.\d{2})?)", text)
                if match:
                    cost = f"${match.group(1)}"
                    log(f"  Found cost from text: {cost}")
                    return cost

            log("  ⚠ Price element exists but value not found")
            return ""

        except PlaywrightTimeoutError:
            log("  ⚠ Cost not found: timeout waiting for price element")
            return ""
        except Exception as e:
            log(f"  ⚠ Cost not found: {e}")
            return ""

    def _extract_model_number(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract vendor SKU / model number using Playwright.

        Args:
            soup: BeautifulSoup object (not used, kept for compatibility)
            log: Logging function

        Returns:
            Model number string or empty string
        """
        if not self._page:
            log("  ❌ No Playwright page available")
            return ""

        try:
            # Wait for SKU element to load with longer timeout
            self._page.wait_for_selector("span.product-line-sku-value", timeout=10000)

            # Give extra time for JavaScript to render
            time.sleep(0.5)

            # Get SKU element
            # Format: <span class="product-line-sku-value" itemprop="sku"> 11003310 </span>
            # Or: <span class="product-line-sku-value" itemprop="sku"> 24001070CBS </span>
            sku_element = self._page.query_selector("span.product-line-sku-value")
            if sku_element:
                value = sku_element.text_content().strip()
                if value:
                    log(f"  Found model number: {value}")
                    return value

            log("  ⚠ SKU element exists but value is empty")
            return ""

        except PlaywrightTimeoutError:
            log("  ⚠ Model number not found: timeout waiting for SKU element")
            return ""
        except Exception as e:
            log(f"  ⚠ Model number not found: {e}")
            return ""

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to absolute HTTPS URL.

        Args:
            url: Raw URL

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
            url = f"{self.portal_origin}{url}"

        # Ensure HTTPS
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        return url

    def close(self):
        """Close browser and cleanup."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None
        self._logged_in = False
