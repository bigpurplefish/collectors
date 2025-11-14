#!/usr/bin/env python3
"""
Cambridge Product Collector

Main orchestration module that coordinates:
- Product index building/caching
- Product search and matching
- Public website parsing
- Dealer portal data collection
- Variant grouping
- Shopify product generation
"""

import os
import sys
from typing import Dict, List, Any, Callable
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add parent directories to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.index_builder import (
    CambridgeIndexBuilder,
    load_index_from_cache,
    save_index_to_cache,
    is_index_stale
)
from src.search import CambridgeSearcher
from src.public_parser import CambridgePublicParser
from src.portal_parser import CambridgePortalParser
from src.portal_index_builder import CambridgePortalIndexBuilder
from src.portal_search import CambridgePortalSearcher
from src.config import INDEX_CACHE_FILE, PORTAL_INDEX_CACHE_FILE


# Site Configuration
SITE_CONFIG = {
    "public_origin": "https://www.cambridgepavers.com",
    "portal_origin": "https://shop.cambridgepavers.com",
    "fuzzy_match_threshold": 60.0,
    "timeout": 30,
}


class CambridgeCollector:
    """Cambridge product data collector."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize collector.

        Args:
            config: Optional configuration dictionary (defaults to SITE_CONFIG + user config)
        """
        # Merge site config with user config
        self.config = SITE_CONFIG.copy()
        if config:
            self.config.update(config)

        # Initialize components
        self.index_builder = CambridgeIndexBuilder(self.config)
        self.searcher = CambridgeSearcher(self.config)
        self.public_parser = CambridgePublicParser(self.config)
        self.portal_index_builder = CambridgePortalIndexBuilder(self.config)
        self.portal_searcher = CambridgePortalSearcher(self.config)

        # HTTP session with retries
        self.session = self._create_http_session()

    def _create_http_session(self) -> requests.Session:
        """
        Create HTTP session with retry logic.

        Returns:
            Configured requests Session
        """
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

        return session

    def ensure_index_loaded(self, force_rebuild: bool = False, log: Callable = print) -> bool:
        """
        Ensure product index is loaded and fresh.

        Args:
            force_rebuild: Force rebuild even if cache is fresh
            log: Logging function

        Returns:
            True if index loaded successfully
        """
        # Try to load from cache
        if not force_rebuild:
            cached_index = load_index_from_cache(INDEX_CACHE_FILE, log)

            if cached_index:
                # Check if stale
                max_age_days = self.config.get("index_max_age_days", 7)
                if is_index_stale(cached_index, max_age_days):
                    log(f"⚠ Product index is stale (>{max_age_days} days old)")
                    log("Rebuilding index...")
                else:
                    # Use cached index
                    self.searcher.load_index(cached_index, log)
                    return True

        # Build new index
        log("")
        log("Building product index (this may take a few minutes)...")

        try:
            index = self.index_builder.build_index(
                http_get=self.session.get,
                timeout=self.config.get("timeout", 30),
                log=log
            )

            # Save to cache
            save_index_to_cache(index, INDEX_CACHE_FILE, log)

            # Load into searcher
            self.searcher.load_index(index, log)

            return True

        except Exception as e:
            log(f"❌ Failed to build product index: {e}")
            return False

    def ensure_portal_index_loaded(self, force_rebuild: bool = False, log: Callable = print) -> bool:
        """
        Ensure portal product index is loaded and fresh.

        Args:
            force_rebuild: Force rebuild even if cache is fresh
            log: Logging function

        Returns:
            True if index loaded successfully
        """
        # Try to load from cache
        if not force_rebuild:
            cached_index = load_index_from_cache(PORTAL_INDEX_CACHE_FILE, log)

            if cached_index:
                # Check if stale
                max_age_days = self.config.get("index_max_age_days", 7)
                if is_index_stale(cached_index, max_age_days):
                    log(f"⚠ Portal index is stale (>{max_age_days} days old)")
                    log("Rebuilding portal index...")
                else:
                    # Use cached index
                    self.portal_searcher.load_index(cached_index, log)
                    return True

        # Build new portal index
        log("")
        log("Building portal product index (this may take several minutes)...")

        try:
            index = self.portal_index_builder.build_index(log)

            # Save to cache
            save_index_to_cache(index, PORTAL_INDEX_CACHE_FILE, log)

            # Load into searcher
            self.portal_searcher.load_index(index, log)

            return True

        except Exception as e:
            log(f"❌ Failed to build portal index: {e}")
            return False

    def find_product_url(
        self,
        title: str,
        color: str,
        log: Callable = print
    ) -> str:
        """
        Find product URL for given title and color.

        Args:
            title: Product title
            color: Color variant
            log: Logging function

        Returns:
            Product URL or empty string if not found
        """
        return self.searcher.find_product_url(title, color, log)

    def collect_public_data(
        self,
        product_url: str,
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Collect data from public website.

        Args:
            product_url: Product URL
            log: Logging function

        Returns:
            Dictionary with public website data
        """
        try:
            log(f"Fetching public page: {product_url}")

            response = self.session.get(product_url, timeout=self.config.get("timeout", 30))
            response.raise_for_status()

            # Parse page
            data = self.public_parser.parse_page(response.text)

            # Extract ALL gallery images using Playwright (opens lightbox)
            # This gets all 20 images instead of just the 10 in the HTML
            log(f"  Extracting gallery images via Playwright lightbox...")
            gallery_playwright = self.public_parser.extract_gallery_images_with_playwright(
                product_url,
                log
            )

            # Use Playwright images if available, otherwise fall back to HTML parsing
            if gallery_playwright:
                data["gallery_images"] = gallery_playwright
                log(f"  ✓ Extracted {len(gallery_playwright)} images from lightbox")
            else:
                log(f"  ⚠ Playwright gallery extraction failed, no gallery detected ({len(data.get('gallery_images', []))} images)")

            # Log what was captured
            hero = data.get("hero_image", "")
            gallery = data.get("gallery_images", [])
            desc = data.get("description", "")
            specs = data.get("specifications", "")
            title = data.get("title", "")
            collection = data.get("collection", "")
            colors = data.get("colors", [])

            log(f"  ✓ Public data collected:")
            log(f"    - Title: {title if title else 'NOT FOUND'}")
            log(f"    - Collection: {collection if collection else 'NOT FOUND'}")
            log(f"    - Hero image: {'YES' if hero else 'NOT FOUND'}")
            log(f"    - Gallery images: {len(gallery)} images")
            log(f"    - Description: {len(desc)} characters" if desc else "    - Description: NOT FOUND")
            log(f"    - Specifications: {len(specs)} characters" if specs else "    - Specifications: NOT FOUND")
            log(f"    - Colors: {len(colors)} color options" if colors else "    - Colors: NOT FOUND")

            return data

        except Exception as e:
            log(f"  ❌ Failed to collect public data: {e}")
            return {}

    def collect_portal_data(
        self,
        title: str,
        color: str,
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Collect data from dealer portal.

        Args:
            title: Product title to search for
            color: Color variant (portal URLs don't include color)
            log: Logging function

        Returns:
            Dictionary with portal data
        """
        try:
            # Search portal index for product URL
            product = self.portal_searcher.find_product_by_title_and_color(title, color, log)

            if not product:
                log("  ❌ Product not found in portal index")
                return {}

            product_url = product.get("url", "")
            if not product_url:
                log("  ❌ No URL found for product")
                return {}

            # Initialize portal parser with credentials
            portal_config = self.config.copy()
            portal_parser = CambridgePortalParser(portal_config)

            with portal_parser:
                # Login
                if not portal_parser.login(log):
                    log("  ❌ Failed to login to dealer portal")
                    return {}

                # Fetch and parse product page
                html = portal_parser.fetch_product_page(product_url, log)

                if not html:
                    log("  ❌ Failed to fetch portal page")
                    return {}

                data = portal_parser.parse_product_page(html, log)
                log("  ✓ Portal data collected")

                return data

        except Exception as e:
            log(f"  ❌ Failed to collect portal data: {e}")
            return {}

    def close(self):
        """Close HTTP session and cleanup."""
        if self.session:
            self.session.close()
