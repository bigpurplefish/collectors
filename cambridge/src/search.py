"""
Search functionality for Cambridge collector.

Matches input products against cached product index using fuzzy matching.
"""

import re
from typing import Dict, List, Any, Callable, Set, Optional
from rapidfuzz import fuzz


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
        log(f"✓ Loaded product index: {total_products} products")

    def find_product_by_title_and_color(
        self,
        title: str,
        color: str,
        log: Callable = print
    ) -> Optional[Dict[str, Any]]:
        """
        Find product in index by title and color.

        Uses fuzzy matching on title, then checks if product has the requested color.

        Args:
            title: Product title to search for
            color: Color variant to find
            log: Logging function

        Returns:
            Product dictionary from index or None if not found
        """
        if not self.index:
            log("❌ Product index not loaded")
            return None

        products = self.index.get("products", [])
        if not products:
            log("❌ Product index is empty")
            return None

        # Strip color family prefix from title for public index search
        # Portal titles have color families like "Sherwood", but public index doesn't
        color_families = ["Sherwood", "Crusader", "Excalibur", "Kingscourt", "Roundtable"]
        search_title = title
        for family in color_families:
            if title.startswith(family + " "):
                search_title = title[len(family) + 1:]  # Remove "Family " prefix
                log(f"Stripped color family '{family}' from title")
                break

        log(f"Searching for: title='{search_title}' (original: '{title}'), color='{color}'")

        # Phase 1: Fuzzy match on title (using search_title without color family prefix)
        best_match = None
        best_score = 0

        for product in products:
            product_title = product.get("title", "")

            # Calculate fuzzy match score
            score = fuzz.token_sort_ratio(search_title.lower(), product_title.lower())

            if score > best_score:
                best_score = score
                best_match = product

        if not best_match or best_score < self.fuzzy_match_threshold:
            log(f"  ✗ No title match found (best score: {best_score})")
            return None

        log(f"  ✓ Title match: '{best_match.get('title')}' (score: {best_score})")

        # Phase 2: Check if product has requested color
        # Note: The index may not include color information
        # We'll return the matched product and let the parser verify colors

        return best_match

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
