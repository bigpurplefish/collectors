"""
Portal Index Builder for Cambridge Dealer Portal

Builds a searchable index of products from the dealer portal (shop.cambridgepavers.com).
Uses Playwright to navigate JavaScript-rendered pages and extract product URLs.

The portal uses SEO-friendly URLs like:
/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit
"""

import json
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError


class CambridgePortalIndexBuilder:
    """Builds product index from Cambridge dealer portal."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize builder.

        Args:
            config: Configuration dictionary with portal_username, portal_password, etc.
        """
        self.config = config
        self.portal_origin = config.get("portal_origin", "https://shop.cambridgepavers.com")
        self.username = config.get("portal_username", "")
        self.password = config.get("portal_password", "")

        # Categories to crawl (based on public site structure)
        self.categories = [
            "/pavers",
            "/pavers/sherwood",
            "/pavers/roundtable",
            "/pavers/kingscourt",
            "/pavers/excalibur",
            "/pavers/crusader",
            "/pavers/maytrx",
            "/walls",
            "/edging",
        ]

    def build_index(
        self,
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Build product index by crawling portal.

        Args:
            log: Logging function

        Returns:
            Dictionary with:
            - last_updated: ISO timestamp
            - total_products: Count of products
            - products: List of product dictionaries with title, url, category
        """
        log("")
        log("=" * 80)
        log("BUILDING PORTAL PRODUCT INDEX")
        log("=" * 80)
        log("")
        log(f"Portal: {self.portal_origin}")
        log(f"Username: {self.username}")
        log("")

        products = []

        try:
            # Start Playwright
            log("Starting browser...")
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Login
            if not self._login(page, log):
                log("❌ Failed to login to portal")
                browser.close()
                playwright.stop()
                return self._create_index(products)

            # Crawl each category
            for category_url in self.categories:
                log(f"\nCrawling category: {category_url}")
                category_products = self._crawl_category(page, category_url, log)
                products.extend(category_products)
                log(f"  ✓ Found {len(category_products)} products")

            # Close browser
            browser.close()
            playwright.stop()

            log("")
            log("=" * 80)
            log(f"INDEX BUILD COMPLETE: {len(products)} products")
            log("=" * 80)

            return self._create_index(products)

        except Exception as e:
            log(f"❌ Error building portal index: {e}")
            return self._create_index(products)

    def _login(self, page: Page, log: Callable) -> bool:
        """
        Login to dealer portal.

        Args:
            page: Playwright Page object
            log: Logging function

        Returns:
            True if login successful
        """
        try:
            log("Logging in to dealer portal...")

            # Navigate to portal home
            page.goto(self.portal_origin, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Look for login form
            email_input = page.locator('input[type="email"], input[name="email"], input#login-email')
            if email_input.count() > 0:
                email_input.fill(self.username)
                log(f"  ✓ Filled username: {self.username}")

            password_input = page.locator('input[type="password"], input[name="password"]')
            if password_input.count() > 0:
                password_input.fill(self.password)
                log("  ✓ Filled password")

            # Click login button
            login_button = page.locator('button[type="submit"], button:has-text("Log In"), button:has-text("Sign In")')
            if login_button.count() > 0:
                login_button.click()
                log("  ✓ Clicked login button")
                page.wait_for_load_state("networkidle", timeout=30000)
                time.sleep(3)

            log("✓ Successfully logged in")
            return True

        except Exception as e:
            log(f"❌ Login failed: {e}")
            return False

    def _crawl_category(
        self,
        page: Page,
        category_url: str,
        log: Callable
    ) -> List[Dict[str, Any]]:
        """
        Crawl a category page and extract product URLs.

        Args:
            page: Playwright Page object
            category_url: Category URL (e.g., "/pavers/sherwood")
            log: Logging function

        Returns:
            List of product dictionaries
        """
        products = []

        try:
            # Navigate to category
            full_url = f"{self.portal_origin}{category_url}"
            log(f"  Navigating to: {full_url}")
            page.goto(full_url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Extract all product links
            # Look for links that match product patterns
            links = page.locator('a[href*="/pavers/"], a[href*="/walls/"], a[href*="/edging/"]').all()

            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue

                    # Skip if it's just a category link
                    if href == category_url or href.count("/") <= 2:
                        continue

                    # Extract product title from link text or nearby element
                    title = link.inner_text().strip()
                    if not title:
                        continue

                    # Check if this is a product URL (not a category)
                    # Product URLs typically have 3+ path segments
                    if href.count("/") >= 3:
                        products.append({
                            "title": title,
                            "url": href,
                            "category": category_url
                        })

                except Exception as e:
                    log(f"    ⚠ Error extracting link: {e}")
                    continue

        except Exception as e:
            log(f"  ❌ Error crawling category {category_url}: {e}")

        # Deduplicate products by URL
        seen_urls = set()
        unique_products = []
        for product in products:
            if product["url"] not in seen_urls:
                seen_urls.add(product["url"])
                unique_products.append(product)

        return unique_products

    def _create_index(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create index dictionary.

        Args:
            products: List of product dictionaries

        Returns:
            Index dictionary
        """
        return {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "total_products": len(products),
            "products": products
        }
