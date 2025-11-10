"""
Portal Product Search for Cambridge Dealer Portal

Searches the portal product index using fuzzy matching to find products.
"""

from typing import Dict, List, Any, Optional, Callable
from rapidfuzz import fuzz


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
        log(f"Loaded portal product index: {index.get('total_products', 0)} products")

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
            log("  ❌ Portal index not loaded")
            return None

        products = self.index.get("products", [])
        if not products:
            log("  ❌ Portal index is empty")
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
            log(f"  ✓ Portal product match: '{best_match['title']}' (score: {best_score})")
            return best_match

        log(f"  ✗ No portal product match found (best score: {best_score})")
        return None

    def find_product_by_title_and_color(
        self,
        title: str,
        color: str,
        log: Callable = print
    ) -> Optional[Dict[str, Any]]:
        """
        Find product URL by title and color.

        Note: Portal URLs don't include color variants in the path,
        so we just match on title and assume the product page
        has a color selector.

        Args:
            title: Product title to search for
            color: Color variant (not used for portal search)
            log: Logging function

        Returns:
            Product dictionary or None if not found
        """
        # Portal URLs are per-product, not per-color
        # Just match on title
        return self.find_product_by_title(title, log)
