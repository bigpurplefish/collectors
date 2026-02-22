"""
Portal Index Builder for Cambridge Dealer Portal

Builds a searchable index of products from the dealer portal (shop.cambridgepavers.com).

Two-stage authenticated approach:
1. Uses navigation API to get category URLs (no auth required)
2. Navigates to each category page with Playwright and scrapes product cards from the rendered DOM

The portal uses SEO-friendly URLs like:
/pavers/sherwood/driftwood_6
"""

import requests
import re
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

# Add parent directories to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.utils.logging_utils import (
    log_section_header,
    log_success,
    log_error,
    log_warning,
    log_and_status,
    log_progress
)

from src.config import PORTAL_INDEX_CACHE_FILE
from src.index_builder import load_index_from_cache


class CambridgePortalIndexBuilder:
    """Builds product index from Cambridge dealer portal."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize builder.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.portal_origin = config.get("portal_origin", "https://shop.cambridgepavers.com")
        self.username = config.get("portal_username", "")
        self.password = config.get("portal_password", "")

        # Navigation API endpoint (no auth required)
        self.nav_api_url = (
            f"{self.portal_origin}/api/navigation/v1/categorynavitems/tree"
            "?c=827395&country=US&currency=USD&exclude_empty=false&language=en"
            "&max_level=6&menu_fields=internalid,name,sequencenumber,displayinsite"
            "&n=2&pcv_all_items=undefined&site_id=2&use_pcv=T"
        )

        # Browser state
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._logged_in = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser."""
        self.close()

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

    def login(self, log: Callable = print) -> bool:
        """
        Login to dealer portal using Playwright.

        Args:
            log: Logging function

        Returns:
            True if login successful, False otherwise
        """
        if self._logged_in:
            log_and_status(log, "Already logged in to dealer portal", ui_msg="Already logged in")
            return True

        log_and_status(log, "Logging in to Cambridge dealer portal...", ui_msg="Logging in...")

        try:
            # Start Playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            # Anti-detection: Configure browser context to appear more human
            context = self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self._page = context.new_page()

            # Navigate to portal
            self._page.goto(self.portal_origin, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Fill login form
            email_input = self._page.locator('input[type="email"], input[name="email"], input#login-email')
            if email_input.count() > 0:
                email_input.fill(self.username)
                log_and_status(log, f"Filled username: {self.username}", ui_msg="Filled username")

            password_input = self._page.locator('input[type="password"], input[name="password"], input#login-password')
            if password_input.count() > 0:
                password_input.fill(self.password)
                log_and_status(log, "Filled password", ui_msg="Filled password")

            # Click login button
            login_button = self._page.locator('button[type="submit"], button:has-text("Log In"), button:has-text("Sign In")')
            if login_button.count() > 0:
                login_button.click()
                log_and_status(log, "Clicked login button", ui_msg="Clicked login")

                # Wait for navigation after login
                self._page.wait_for_load_state("networkidle", timeout=30000)
                time.sleep(3)

                # Verify login succeeded — check we're not still on login page
                url = self._page.url.lower()
                still_on_login = "login" in url or "signin" in url
                if not still_on_login:
                    try:
                        still_on_login = self._page.locator('input#login-email').count() > 0
                    except Exception:
                        pass
                if still_on_login:
                    log_error(log, "Login verification failed - still on login page")
                    return False

                self._logged_in = True
                log_success(log, "Successfully logged in to dealer portal")
                return True

        except Exception as e:
            log_error(log, "Login failed", exc=e)
            return False

        return False

    def build_index(
        self,
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Build product index using two-stage approach.

        Stage 1: Navigation API - Get category URLs (no auth)
        Stage 2: Playwright PLP scraping - Navigate to each category and extract product cards

        Args:
            log: Logging function

        Returns:
            Dictionary with:
            - last_updated: ISO timestamp
            - total_products: Count of individual products
            - products: List of product dictionaries with:
                - title: Product name (e.g., "Sherwood Ledgestone 3-Pc. Design Kit Bluestone Blend")
                - url: Product URL (e.g., "/Bluestone-Blend")
                - category: Category URL
                - sku: Product SKU
                - price: Product price
                - stock: Stock quantity
                - images: List of image URLs
        """
        log_section_header(log, "BUILDING PORTAL PRODUCT INDEX (NAV API + PLP SCRAPING)")
        log_and_status(log, f"Portal: {self.portal_origin}", ui_msg=f"Portal: {self.portal_origin}")

        all_products = []

        try:
            # Stage 1: Get category URLs from navigation API (no auth required)
            log_and_status(
                log,
                "Stage 1: Fetching category URLs from navigation API...",
                ui_msg="Stage 1: Fetching categories"
            )
            response = requests.get(self.nav_api_url, timeout=30)
            response.raise_for_status()

            data = response.json()
            log_success(log, "Successfully fetched navigation API")

            # Extract category URLs from hierarchy
            if "data" in data:
                category_urls = self._extract_category_urls_recursive(data["data"], log)
                log_success(log, f"Found {len(category_urls)} category URLs")
            else:
                log_warning(log, "No data field in API response")
                category_urls = []

            # Stage 2: Login and scrape product cards from category pages
            log_and_status(
                log,
                "Stage 2: Logging in and scraping product cards from category pages...",
                ui_msg="Stage 2: Scraping products"
            )

            if not self.login(log):
                log_error(log, "Failed to login - cannot scrape product pages")
                return self._create_index(all_products)

            # Scrape products from each category with early bail-out
            PROBE_COUNT = 5
            probe_failures = 0

            for i, category_url in enumerate(category_urls, 1):
                log_progress(
                    log,
                    i,
                    len(category_urls),
                    category_url,
                    details=f"Category: {category_url}"
                )

                is_probing = i <= PROBE_COUNT and len(all_products) == 0
                try:
                    products = self._scrape_products_from_category(category_url, log, probe=is_probing)
                    all_products.extend(products)
                    if products:
                        log_success(log, f"Found {len(products)} products from {category_url}")
                    else:
                        if is_probing:
                            probe_failures += 1
                except Exception as e:
                    log_warning(log, f"Error scraping products from {category_url}", details=str(e))
                    if is_probing:
                        probe_failures += 1
                    continue

                # Early bail-out: if first N categories all returned 0 products, page loads likely blocked
                if i == PROBE_COUNT and probe_failures == PROBE_COUNT and len(all_products) == 0:
                    log_warning(
                        log,
                        f"First {PROBE_COUNT} categories all failed - pages likely blocked by bot detection",
                        details=f"Skipping remaining {len(category_urls) - PROBE_COUNT} categories"
                    )
                    break

            log_section_header(log, f"INDEX BUILD COMPLETE: {len(all_products)} products")

            # Fallback to cached index if fresh build returned 0 products (likely bot detection)
            if len(all_products) == 0:
                log_warning(
                    log,
                    "Fresh build returned 0 products - likely bot detection",
                    details="Falling back to cached index"
                )
                cached_index = load_index_from_cache(PORTAL_INDEX_CACHE_FILE, log)
                if cached_index and cached_index.get("products"):
                    log_success(
                        log,
                        f"Using cached index with {len(cached_index['products'])} products"
                    )
                    return cached_index
                else:
                    log_error(log, "No cached index available - cannot proceed")
                    return {"products": [], "total_products": 0, "last_updated": None}

            return self._create_index(all_products)

        except Exception as e:
            log_error(log, "Error building portal index", exc=e)
            return self._create_index(all_products)
        finally:
            # Always close browser
            self.close()

    def _extract_category_urls_recursive(
        self,
        categories: List[Dict],
        log: Callable,
        category_urls: List[str] = None
    ) -> List[str]:
        """
        Recursively extract category URLs from navigation tree.

        Category pages contain product grids that we'll scrape via Playwright.

        Args:
            categories: List of category dictionaries from API
            log: Logging function
            category_urls: Accumulated URL list (internal)

        Returns:
            List of category URLs (e.g., "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit")
        """
        if category_urls is None:
            category_urls = []

        for category in categories:
            # Extract fields
            fullurl = category.get("fullurl", "")
            level = int(category.get("level", "1"))

            # Product category pages are level >= 2 and have a fullurl with at least 2 slashes
            # Level 2: /wall-plus/edgestone-plus (2 slashes)
            # Level 3: /pavers/sherwood/sherwood-ledgestone-3-pc-design-kit (3+ slashes)
            is_product_category = level >= 2 and fullurl and fullurl.count("/") >= 2

            # Skip /accessories category if configured
            skip_accessories = self.config.get("skip_accessories_category", True)
            if skip_accessories and fullurl.startswith("/accessories"):
                continue

            if is_product_category and fullurl not in category_urls:
                category_urls.append(fullurl)

            # Recurse into subcategories
            if "categories" in category:
                self._extract_category_urls_recursive(
                    category["categories"],
                    log,
                    category_urls
                )

        return category_urls

    def _scrape_products_from_category(
        self,
        category_url: str,
        log: Callable,
        probe: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scrape product cards from a category page using Playwright.

        Navigates to the category PLP, waits for SuiteCommerce SPA to render,
        loads all products via pagination, then extracts data from DOM.

        Args:
            category_url: Category URL (e.g., "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit")
            log: Logging function
            probe: If True, use shorter timeouts for fast failure detection

        Returns:
            List of product dictionaries
        """
        if not self._logged_in or not self._page:
            log_warning(log, "Not logged in, skipping category", details=f"Category: {category_url}")
            return []

        try:
            # Rate limiting: delay between page navigations
            time.sleep(2.5)

            nav_timeout = 15000 if probe else 30000
            self._page.goto(
                f"{self.portal_origin}{category_url}",
                wait_until="networkidle",
                timeout=nav_timeout
            )
            # Wait for SuiteCommerce SPA rendering
            time.sleep(3)

            # Load all products on the page (handle pagination)
            self._load_all_products_on_page(log)

            # Extract product data from rendered cards
            return self._extract_product_cards(category_url, log)

        except PlaywrightTimeoutError:
            log_warning(log, f"Page load timeout for {category_url}")
            return []
        except Exception as e:
            log_warning(
                log,
                f"Error scraping products from {category_url}",
                details=str(e)
            )
            return []

    def _load_all_products_on_page(self, log: Callable):
        """
        Handle SuiteCommerce infinite scroll pagination.

        Clicks the "Show More" / infinite scroll button repeatedly until all
        products are loaded. Safety cap at 10 clicks.
        """
        MAX_PAGINATION_CLICKS = 10

        for click_num in range(MAX_PAGINATION_CLICKS):
            # SuiteCommerce uses an infinite scroll button
            show_more = self._page.locator(
                ".global-views-pagination a, "
                "button:has-text('Show More'), "
                "a:has-text('Show More'), "
                "[data-action='pushable'] .infinite-scroll-load-more"
            )

            if show_more.count() == 0:
                break

            # Check if the button is actually visible/clickable
            try:
                first_visible = None
                for idx in range(show_more.count()):
                    if show_more.nth(idx).is_visible():
                        first_visible = show_more.nth(idx)
                        break

                if first_visible is None:
                    break

                first_visible.click(timeout=5000)
                # Wait for new items to load
                self._page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(1)
            except Exception:
                break

    def _extract_product_cards(
        self,
        category_url: str,
        log: Callable
    ) -> List[Dict[str, Any]]:
        """
        Extract product data from all rendered product cards on the page.

        Uses SuiteCommerce DOM selectors discovered via recon:
        - Card: .facets-item-cell-grid with data-item-id, data-sku
        - Title: .facets-item-cell-grid-title a span[itemprop="name"]
        - URL: .facets-item-cell-grid-title href
        - Price: [data-rate] on .product-views-price-lead
        - Image: .facets-item-cell-grid-image src

        Args:
            category_url: The category URL for metadata
            log: Logging function

        Returns:
            List of product dictionaries
        """
        card_data = self._page.evaluate("""(categoryUrl) => {
            const cards = document.querySelectorAll('.facets-item-cell-grid');
            return Array.from(cards).map(card => {
                // Title from the title link's span or link text
                const titleLink = card.querySelector('.facets-item-cell-grid-title');
                const titleSpan = card.querySelector('.facets-item-cell-grid-title span[itemprop="name"]');
                const title = titleSpan
                    ? titleSpan.textContent.trim()
                    : (titleLink ? titleLink.textContent.trim() : '');

                // URL from the title link href
                const url = titleLink ? titleLink.getAttribute('href') : '';

                // SKU from data-sku attribute on card
                const sku = card.getAttribute('data-sku') || '';

                // Price from data-rate attribute
                const priceEl = card.querySelector('[data-rate]');
                const price = priceEl ? priceEl.getAttribute('data-rate') : '';

                // Image URL
                const img = card.querySelector('.facets-item-cell-grid-image');
                const imgSrc = img ? img.getAttribute('src') : '';

                // Stock from text content (parse "Qty Available: N")
                const allText = card.textContent || '';
                const stockMatch = allText.match(/Qty Available:\\s*(\\d+)/);
                const stock = stockMatch ? parseInt(stockMatch[1]) : 0;

                return {
                    title: title,
                    url: url,
                    category: categoryUrl,
                    sku: sku,
                    price: price,
                    stock: stock,
                    images: imgSrc ? [imgSrc] : []
                };
            });
        }""", category_url)

        # Filter out cards with no title (e.g., mini-cart items picked up by mistake)
        products = [p for p in card_data if p.get("title")]
        return products

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
