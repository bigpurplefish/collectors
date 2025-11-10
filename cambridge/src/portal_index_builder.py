"""
Portal Index Builder for Cambridge Dealer Portal

Builds a searchable index of products from the dealer portal (shop.cambridgepavers.com).
Uses the navigation API to fetch complete product hierarchy.

The portal uses SEO-friendly URLs like:
/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit
"""

import requests
from datetime import datetime
from typing import Dict, List, Any, Callable


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

        # Navigation API endpoint
        self.api_url = (
            f"{self.portal_origin}/api/navigation/v1/categorynavitems/tree"
            "?c=827395&country=US&currency=USD&exclude_empty=false&language=en"
            "&max_level=6&menu_fields=internalid,name,sequencenumber,displayinsite"
            "&n=2&pcv_all_items=undefined&site_id=2&use_pcv=T"
        )

    def build_index(
        self,
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Build product index using navigation API.

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
        log("Fetching product data from navigation API...")
        log("")

        products = []

        try:
            # Fetch navigation API
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()

            data = response.json()
            log("✓ Successfully fetched navigation API")

            # Extract products from hierarchy
            if "data" in data:
                products = self._extract_products_recursive(data["data"], log)
            else:
                log("⚠ No data field in API response")

            log("")
            log("=" * 80)
            log(f"INDEX BUILD COMPLETE: {len(products)} products")
            log("=" * 80)

            return self._create_index(products)

        except Exception as e:
            log(f"❌ Error building portal index: {e}")
            return self._create_index(products)

    def _extract_products_recursive(
        self,
        categories: List[Dict],
        log: Callable,
        products: List[Dict] = None,
        parent_path: str = ""
    ) -> List[Dict]:
        """
        Recursively extract products from category tree.

        Args:
            categories: List of category dictionaries from API
            log: Logging function
            products: Accumulated product list (internal)
            parent_path: Parent category path (internal)

        Returns:
            List of product dictionaries with title, url, category
        """
        if products is None:
            products = []

        for category in categories:
            # Extract fields
            name = category.get("name", "")
            fullurl = category.get("fullurl", "")
            level = int(category.get("level", "1"))

            # Determine if this is a product or category
            # Products typically have level >= 3 and have a fullurl
            # Categories are level 1-2
            is_product = level >= 3 and fullurl and fullurl.count("/") >= 3

            if is_product:
                # This is a product
                products.append({
                    "title": name,
                    "url": fullurl,
                    "category": parent_path
                })
            else:
                # This is a category - update parent path for subcategories
                if fullurl:
                    parent_path = fullurl

            # Recurse into subcategories
            if "categories" in category:
                self._extract_products_recursive(
                    category["categories"],
                    log,
                    products,
                    parent_path
                )

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
