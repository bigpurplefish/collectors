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
            playwright = sync_playwright().start()
            self._browser = playwright.chromium.launch(headless=True)
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
            - weight: Item weight
            - sales_unit: Sales unit / unit of sale
            - cost: Product cost/price
            - model_number: Vendor SKU / model number
        """
        soup = BeautifulSoup(html, "lxml")

        result = {
            "gallery_images": self._extract_gallery_images(soup, log),
            "weight": self._extract_weight(soup, log),
            "sales_unit": self._extract_sales_unit(soup, log),
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
            # Wait for gallery to load (adjust selector as needed for SuiteCommerce)
            # Common SuiteCommerce gallery selectors:
            # - .product-detail-images
            # - .product-views-image-carousel
            # - .bx-viewport img
            try:
                self._page.wait_for_selector("img", timeout=5000)
            except:
                log("  ⚠ Gallery images not found")
                return images

            # Extract gallery images using Playwright
            # Try multiple selector patterns for SuiteCommerce galleries
            gallery_selectors = [
                ".product-detail-images img",
                ".product-views-image-carousel img",
                ".bx-viewport img",
                ".product-image-gallery img"
            ]

            gallery_images = []
            for selector in gallery_selectors:
                elements = self._page.query_selector_all(selector)
                if elements:
                    gallery_images = elements
                    break

            if not gallery_images:
                # Fallback: get all product images
                gallery_images = self._page.query_selector_all("img")

            # Extract src attributes in order
            for img in gallery_images:
                src = img.get_attribute("src")
                if src:
                    # Skip thumbnails, icons, UI elements
                    if any(skip in src.lower() for skip in ["thumb", "icon", "logo", "button", "sprite"]):
                        continue

                    # Normalize URL
                    full_url = self._normalize_url(src)
                    if full_url and full_url not in images:
                        images.append(full_url)

            log(f"  Found {len(images)} gallery images")
            return images

        except Exception as e:
            log(f"  ⚠ Error extracting gallery images: {e}")
            return images

    def _extract_weight(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract item weight.

        Args:
            soup: BeautifulSoup object
            log: Logging function

        Returns:
            Weight string or empty string
        """
        # Look for weight in product details
        # Common patterns: "Weight:", "Item Weight:", etc.
        for label in ["Weight:", "Item Weight:", "Shipping Weight:"]:
            tag = soup.find(string=re.compile(label, re.IGNORECASE))
            if tag:
                parent = tag.find_parent()
                if parent:
                    text = parent.get_text(strip=True)
                    # Extract weight value
                    match = re.search(r"(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kgs|oz)", text, re.IGNORECASE)
                    if match:
                        weight = f"{match.group(1)} {match.group(2)}"
                        log(f"  Found weight: {weight}")
                        return weight

        log("  ⚠ Weight not found")
        return ""

    def _extract_sales_unit(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract sales unit / unit of sale.

        Args:
            soup: BeautifulSoup object
            log: Logging function

        Returns:
            Sales unit string or empty string
        """
        # Look for sales unit in product details
        for label in ["Sales Unit:", "Unit of Sale:", "Sold By:"]:
            tag = soup.find(string=re.compile(label, re.IGNORECASE))
            if tag:
                parent = tag.find_parent()
                if parent:
                    text = parent.get_text(strip=True)
                    # Remove label and get value
                    value = re.sub(r"^[^:]+:\s*", "", text).strip()
                    if value:
                        log(f"  Found sales unit: {value}")
                        return value

        log("  ⚠ Sales unit not found")
        return ""

    def _extract_cost(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract product cost/price.

        Args:
            soup: BeautifulSoup object
            log: Logging function

        Returns:
            Cost string or empty string
        """
        # Look for price in product details
        # SuiteCommerce typically has price in a specific element
        for pattern in [r"\$\d+(?:\.\d{2})?", r"Price:\s*\$\d+(?:\.\d{2})?"]:
            match = re.search(pattern, soup.get_text())
            if match:
                cost = match.group(0)
                # Clean up
                cost = re.sub(r"^Price:\s*", "", cost)
                log(f"  Found cost: {cost}")
                return cost

        log("  ⚠ Cost not found")
        return ""

    def _extract_model_number(self, soup: BeautifulSoup, log: Callable) -> str:
        """
        Extract vendor SKU / model number.

        Args:
            soup: BeautifulSoup object
            log: Logging function

        Returns:
            Model number string or empty string
        """
        # Look for SKU/model number in product details
        for label in ["SKU:", "Model:", "Model Number:", "Vendor SKU:", "Item #:"]:
            tag = soup.find(string=re.compile(label, re.IGNORECASE))
            if tag:
                parent = tag.find_parent()
                if parent:
                    text = parent.get_text(strip=True)
                    # Remove label and get value
                    value = re.sub(r"^[^:]+:\s*", "", text).strip()
                    if value:
                        log(f"  Found model number: {value}")
                        return value

        log("  ⚠ Model number not found")
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
        self._page = None
        self._logged_in = False
