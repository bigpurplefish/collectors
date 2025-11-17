"""
Portal Product Search for Cambridge Dealer Portal

Searches the portal product index using fuzzy matching to find products.
"""

import sys
import os
from typing import Dict, List, Any, Optional, Callable
from rapidfuzz import fuzz

# Add parent directories to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.utils.logging_utils import log_success, log_error, log_and_status


class CambridgePortalSearcher:
    """Search portal product index using fuzzy matching."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize searcher.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.threshold = config.get("fuzzy_match_threshold", 60.0)
        self.index = None

    def load_index(self, index: Dict[str, Any], log: Callable = print):
        """
        Load product index.

        Args:
            index: Product index dictionary
            log: Logging function
        """
        self.index = index
        total_products = index.get('total_products', 0)
        log_success(
            log,
            f"Loaded portal product index: {total_products} products",
            details=f"Portal index contains {total_products} authenticated products with SKUs, prices, and stock"
        )

    def find_product_by_title(
        self,
        title: str,
        log: Callable = print
    ) -> Optional[Dict[str, Any]]:
        """
        Find product URL by title using fuzzy matching.

        Args:
            title: Product title to search for
            log: Logging function

        Returns:
            Product dictionary or None if not found
        """
        if not self.index:
            log_error(log, "Portal index not loaded", details="Portal index must be loaded before searching")
            return None

        products = self.index.get("products", [])
        if not products:
            log_error(log, "Portal index is empty", details="No portal products available for matching")
            return None

        # Find best match using fuzzy matching
        best_match = None
        best_score = 0.0

        for product in products:
            product_title = product.get("title", "")

            # Use token_sort_ratio for better matching
            score = fuzz.token_sort_ratio(title.lower(), product_title.lower())

            if score > best_score:
                best_score = score
                best_match = product

        # Check if best match exceeds threshold
        if best_match and best_score >= self.threshold:
            log_success(
                log,
                f"Portal product match: '{best_match['title']}'",
                details=f"Match score: {best_score}, threshold: {self.threshold}"
            )
            return best_match

        log_and_status(
            log,
            f"No portal product match found (best score: {best_score}, threshold: {self.threshold})",
            ui_msg=f"No portal match (score: {best_score})"
        )
        return None

    def find_product_by_title_and_color(
        self,
        title: str,
        color: str,
        log: Callable = print
    ) -> Optional[Dict[str, Any]]:
        """
        Find product URL by title and color.

        Portal has color-specific variants in the index (e.g., "Sherwood Ledgestone 3-Pc. Design Kit Onyx Natural").
        Match on both title and color for better accuracy.

        Args:
            title: Product title to search for
            color: Color variant to match
            log: Logging function

        Returns:
            Product dictionary or None if not found
        """
        # URL overrides for specific products with incorrect portal index URLs
        # These products were matched to category pages instead of product pages
        # Check overrides FIRST, before checking index status
        url_overrides = {
            ("Sherwood Ledgestone 3-Pc. Design Kit", "Platinum"): "/product/20784",
            ("Sherwood Ledgestone 3-Pc. Design Kit Smooth", "Platinum"): "/product/20785",
        }

        # Check if this product has a URL override
        override_key = (title, color)
        if override_key in url_overrides:
            override_url = url_overrides[override_key]
            log_success(
                log,
                f"Portal product match: '{title} {color}' (URL override)",
                details=f"Using hardcoded URL override: {override_url}"
            )
            return {
                "title": f"{title} {color}",
                "url": override_url,
                "category": "",
                "is_override": True
            }

        # If no override, check portal index
        if not self.index:
            log_error(log, "Portal index not loaded", details="Portal index must be loaded before searching")
            return None

        products = self.index.get("products", [])
        if not products:
            log_error(log, "Portal index is empty", details="No portal products available for matching")
            return None

        # Normalize color for matching (replace "/" with space, handle variations)
        normalized_color = color.replace("/", " ").strip()

        # Find best match using fuzzy matching on title + color combined
        best_match = None
        best_score = 0.0

        for product in products:
            product_title = product.get("title", "")

            # Try matching with color included in the search
            search_text = f"{title} {normalized_color}"
            score = fuzz.token_sort_ratio(search_text.lower(), product_title.lower())

            if score > best_score:
                best_score = score
                best_match = product

        # Check if best match exceeds threshold
        if best_match and best_score >= self.threshold:
            log_success(
                log,
                f"Portal product match: '{best_match['title']}'",
                details=f"Matched '{title}' + '{color}' with score: {best_score}, threshold: {self.threshold}"
            )
            return best_match

        log_and_status(
            log,
            f"No portal product match found for '{title}' + '{color}' (best score: {best_score}, threshold: {self.threshold})",
            ui_msg=f"No portal match (score: {best_score})"
        )
        return None
