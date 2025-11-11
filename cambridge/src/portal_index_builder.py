"""
Portal Index Builder for Cambridge Dealer Portal

Builds a searchable index of products from the dealer portal (shop.cambridgepavers.com).

Two-stage authenticated approach:
1. Uses navigation API to get category URLs (no auth required)
2. Uses authenticated search API to get individual product variants with SKUs, prices, stock, images

The portal uses SEO-friendly URLs like:
/pavers/sherwood/driftwood_6
"""

import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from playwright.sync_api import sync_playwright, Browser, Page


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

        # Search API endpoint (requires auth)
        self.search_api_url = f"{self.portal_origin}/scs/searchApi.ssp"

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
            time.sleep(3)

            # Fill login form
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
            log(f"❌ Login failed: {e}")
            return False

        return False

    def build_index(
        self,
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Build product index using two-stage authenticated approach.

        Stage 1: Navigation API - Get category URLs (no auth)
        Stage 2: Search API - Get individual product variants (requires auth)

        Args:
            log: Logging function

        Returns:
            Dictionary with:
            - last_updated: ISO timestamp
            - total_products: Count of individual products
            - products: List of product dictionaries with:
                - title: Product name with color family prefix (e.g., "Sherwood Ledgestone 3-Pc. Design Kit")
                - url: Product URL
                - category: Category URL
                - sku: Product SKU
                - price: Product price
                - stock: Stock quantity
                - images: List of image URLs
        """
        log("")
        log("=" * 80)
        log("BUILDING PORTAL PRODUCT INDEX (TWO-STAGE AUTHENTICATED)")
        log("=" * 80)
        log("")
        log(f"Portal: {self.portal_origin}")
        log("")

        all_products = []

        try:
            # Stage 1: Get category URLs from navigation API (no auth required)
            log("Stage 1: Fetching category URLs from navigation API...")
            response = requests.get(self.nav_api_url, timeout=30)
            response.raise_for_status()

            data = response.json()
            log("✓ Successfully fetched navigation API")

            # Extract category URLs from hierarchy
            if "data" in data:
                category_urls = self._extract_category_urls_recursive(data["data"], log)
                log(f"✓ Found {len(category_urls)} category URLs")
            else:
                log("⚠ No data field in API response")
                category_urls = []

            log("")

            # Stage 2: Login and get product variants from search API
            log("Stage 2: Logging in and fetching product variants from search API...")
            log("")

            if not self.login(log):
                log("❌ Failed to login - cannot fetch product details")
                return self._create_index(all_products)

            log("")

            # Fetch products from each category
            for i, category_url in enumerate(category_urls, 1):
                log(f"  [{i}/{len(category_urls)}] Fetching products from {category_url}")

                try:
                    products = self._fetch_products_from_category(category_url, log)
                    all_products.extend(products)
                    log(f"    ✓ Found {len(products)} products")
                except Exception as e:
                    log(f"    ⚠ Error: {e}")
                    continue

            log("")
            log("=" * 80)
            log(f"INDEX BUILD COMPLETE: {len(all_products)} products")
            log("=" * 80)

            return self._create_index(all_products)

        except Exception as e:
            log(f"❌ Error building portal index: {e}")
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

        Category pages contain product grids that we'll query via search API.

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

            # Product category pages are level >= 3 and have a fullurl
            is_product_category = level >= 3 and fullurl and fullurl.count("/") >= 3

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

    def _fetch_products_from_category(
        self,
        category_url: str,
        log: Callable
    ) -> List[Dict[str, Any]]:
        """
        Fetch individual product variants from a category using authenticated search API.

        Args:
            category_url: Category URL (e.g., "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit")
            log: Logging function

        Returns:
            List of product dictionaries with title (including color family prefix),
            url, category, sku, price, stock, images
        """
        if not self._logged_in or not self._page:
            log(f"      ⚠ Not logged in, skipping category")
            return []

        # Build search API URL with parameters
        search_url = (
            f"{self.search_api_url}"
            f"?c=827395&country=US&currency=USD&language=en"
            f"&limit=100&n=2&offset=0&pricelevel=5&site_id=2"
            f"&sort=relevance:desc&commercecategoryurl={category_url}"
            f"&use_pcv=T&include=facets&fieldset=search"
        )

        try:
            # Use Playwright to fetch search API (authenticated)
            response = self._page.request.get(search_url, timeout=30000)

            if response.status != 200:
                log(f"      ⚠ Search API returned status {response.status}")
                return []

            data = response.json()

            # Extract products from search results
            products = []
            items = data.get("items", [])

            for item in items:
                # Extract product data
                display_name = item.get("displayname", "")
                url_component = item.get("urlcomponent", "")
                item_id = item.get("itemid", "")
                price = item.get("onlinecustomerprice", "")
                stock = item.get("quantityavailable", 0)

                # Extract images
                images = []
                image_detail = item.get("itemimages_detail", {})
                if image_detail:
                    urls = image_detail.get("urls", [])
                    for img in urls:
                        if isinstance(img, dict):
                            img_url = img.get("url", "")
                            if img_url:
                                images.append(img_url)

                # Build full product URL
                # Portal URLs use just the LAST component of urlcomponent, not the full path
                # API returns: /accessories/alliance-cleaners/.../Alliance-Gator-Clean-Sealer-Stripper-1-Gal.
                # We need: /Alliance-Gator-Clean-Sealer-Stripper-1-Gal.
                # Example: /Sherwood-Ledgestone-3-Pc.-Design-Kit-Onyx-Natural
                if url_component:
                    # Extract last component (split by / and take last part)
                    last_component = url_component.strip("/").split("/")[-1]
                    product_url = f"/{last_component}"
                else:
                    product_url = category_url

                # Extract color family from category URL and prepend to title if not already present
                # Category URL format: /pavers/sherwood/...
                # We want to extract "Sherwood" and prepend it to the displayname IF IT'S NOT ALREADY THERE
                color_family = ""
                category_parts = category_url.strip("/").split("/")
                if len(category_parts) >= 2:
                    # category_parts[0] is "pavers" or "walls"
                    # category_parts[1] is the color family (e.g., "sherwood", "crusader")
                    color_family = category_parts[1].replace("-", " ").title()

                # Build full title with color family prefix (only if not already in displayname)
                if color_family and not display_name.lower().startswith(color_family.lower()):
                    full_title = f"{color_family} {display_name}"
                else:
                    full_title = display_name

                products.append({
                    "title": full_title,
                    "url": product_url,
                    "category": category_url,
                    "sku": item_id,
                    "price": str(price) if price else "",
                    "stock": int(stock) if stock else 0,
                    "images": images
                })

            return products

        except Exception as e:
            # Log error but don't fail the entire build
            log(f"      ⚠ Error fetching products: {e}")
            return []

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
