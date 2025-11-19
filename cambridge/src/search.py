"""
Search functionality for Cambridge collector.

Matches input products against cached product index using fuzzy matching.
"""

import re
import sys
import os
from typing import Dict, List, Any, Callable, Set, Optional
from rapidfuzz import fuzz

# Add parent directories to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.utils.logging_utils import log_success, log_error, log_and_status


class CambridgeSearcher:
    """Handles product search using cached product index."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
        """
        self.origin = config.get("public_origin", "https://www.cambridgepavers.com")
        self.fuzzy_match_threshold = float(config.get("fuzzy_match_threshold", 60.0))

        # Product index (loaded from cache)
        self.index: Optional[Dict[str, Any]] = None

        # Common stop words for fuzzy matching
        self._common_stop: Set[str] = {
            "cambridge", "pavers", "pavingstones", "collection", "design",
            "kit", "pc", "piece", "with", "and", "for", "the"
        }

    def load_index(self, index: Dict[str, Any], log: Callable = print):
        """
        Load product index into searcher.

        Args:
            index: Product index dictionary
            log: Logging function
        """
        self.index = index
        total_products = len(index.get("products", []))
        log_success(
            log,
            f"Loaded product index: {total_products} products",
            details=f"Index contains {total_products} products from public website"
        )

    def find_product_by_title_and_color(
        self,
        title: str,
        color: str,
        log: Callable = print
    ) -> Optional[Dict[str, Any]]:
        """
        Find product in index by exact match on public_title.

        The public index contains products with title field matching public_title from input file.
        This method performs exact matching.

        Args:
            title: Public title to search for (from public_title field)
            color: Color variant (not used for matching, kept for signature compatibility)
            log: Logging function

        Returns:
            Product dictionary from index or None if not found
        """
        if not self.index:
            log_error(log, "Product index not loaded", details="Index must be loaded before searching")
            return None

        products = self.index.get("products", [])
        if not products:
            log_error(log, "Product index is empty", details="No products available for matching")
            return None

        log_and_status(
            log,
            f"Searching public index for exact match: '{title}'",
            ui_msg=f"Searching: {title}"
        )

        # Find exact match on title
        for product in products:
            product_title = product.get("title", "").strip()

            if product_title == title:
                log_success(
                    log,
                    f"Public site exact match: '{product_title}'",
                    details=f"Matched '{title}' exactly"
                )
                return product

        # No exact match found
        log_and_status(
            log,
            f"No public site product found for exact match: '{title}'",
            ui_msg=f"No match found for: {title}"
        )
        return None

    def find_product_url(
        self,
        title: str,
        color: str,
        log: Callable = print
    ) -> str:
        """
        Find product URL for given title and color.

        Args:
            title: Product title to search for
            color: Color variant
            log: Logging function

        Returns:
            Product URL or empty string if not found
        """
        product = self.find_product_by_title_and_color(title, color, log)

        if not product:
            return ""

        # Construct full URL
        product_url = product.get("url", "")
        if product_url.startswith("/"):
            return f"{self.origin}{product_url}"

        return product_url

    def _keyword_set(self, s: str) -> Set[str]:
        """
        Extract and normalize keyword set from text.

        Args:
            s: Input string

        Returns:
            Set of normalized keywords
        """
        toks = [t for t in re.split(r"\W+", s.lower()) if t]
        out: Set[str] = set()

        for t in toks:
            if t.isdigit() or len(t) < 2:
                continue
            if t in self._common_stop:
                continue
            out.add(t)

        return out

    def _fuzzy_match_score(
        self,
        candidate_kw: Set[str],
        query_kw: Set[str]
    ) -> float:
        """
        Calculate fuzzy match score based on keyword overlap.

        Args:
            candidate_kw: Candidate keywords
            query_kw: Query keywords

        Returns:
            Match score (0.0 to 1.0)
        """
        if not query_kw:
            return 0.0
        intersection = len(candidate_kw & query_kw)
        return float(intersection) / max(1, len(query_kw))
