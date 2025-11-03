"""
Search functionality for Purinamills collector.

Handles name-based fuzzy product search using the product index.
"""

import re
from typing import Callable, Any, Optional, Dict, Set
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class PurinamillsSearcher:
    """Handles product search for Purinamills."""

    def __init__(self, config: dict, indexer):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
            indexer: ProductIndexer instance
        """
        self.origin = config.get("origin", "")
        self.enable_search_fallback = bool(config.get("enable_search_fallback", True))
        self.max_search_candidates = int(config.get("max_search_candidates", 30))
        self.indexer = indexer

    def _keyword_set(self, s: str) -> Set[str]:
        """Extract keyword set from text."""
        return self.indexer._keyword_set(s)

    def _entry_kw(self, display_name: str, url: str) -> Set[str]:
        """Get combined keyword set for an entry."""
        return self.indexer._entry_kw(display_name, url)

    def _fuzzy_match_score(
        self,
        candidate_kw: Set[str],
        query_kw: Set[str]
    ) -> float:
        """Calculate fuzzy match score."""
        if not query_kw:
            return 0.0
        intersection = len(candidate_kw & query_kw)
        return float(intersection) / max(1, len(query_kw))

    def _search_site(
        self,
        query: str,
        http_get: Callable[..., Any],
        timeout: float,
        log: Callable[[str], None]
    ) -> list:
        """Search site for candidates."""
        try:
            url = f"{self.origin}/search?q={quote_plus(query)}"
            response = http_get(url, timeout=timeout)
            html_text = response.text if hasattr(response, 'text') else str(response)

            soup = BeautifulSoup(html_text, "html.parser")
            out = []
            seen = set()

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "/products/" not in href:
                    continue
                if href.startswith("http"):
                    full = href
                else:
                    full = f"{self.origin.rstrip('/')}/{href.lstrip('/')}"
                if full in seen:
                    continue
                seen.add(full)

                name = a.get_text(" ", strip=True)
                kw = self._entry_kw(name, full)
                if not name:
                    name = " ".join(sorted(kw)) or full.rsplit("/", 1)[-1]
                out.append({"name": name, "url": full, "kw": kw})

                if len(out) >= self.max_search_candidates:
                    break
            return out
        except Exception as e:
            log(f"[PurinaMills] Search fallback failed for '{query}': {e}")
            return []

    def find_product_url(
        self,
        upc: str,
        http_get: Callable[..., Any],
        timeout: float,
        log: Callable[[str], None],
        product_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Find product page URL for a given UPC.

        Uses fuzzy name matching against product index.

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout
            log: Logging function
            product_data: Optional product data for name matching

        Returns:
            Product URL or empty string if not found
        """
        if not upc:
            log("[PurinaMills] No UPC provided.")
            return ""

        # Build index if not already built
        self.indexer.build_index(http_get, timeout, log)
        index = self.indexer.get_index()

        if not index:
            log("[PurinaMills] Product index unavailable or empty.")
            return ""

        # Get query text from product data
        query_text = ""
        if product_data:
            query_text = (
                product_data.get("upcitemdb_title")
                or product_data.get("description_1")
                or ""
            )

        if not query_text:
            log("[PurinaMills] No product name available for fuzzy matching.")
            return ""

        # Extract keywords from query
        query_kw = self._keyword_set(query_text)

        # Find best match
        best_url = ""
        best_score = 0.0

        for entry in index:
            candidate_kw = entry.get("kw", set())
            score = self._fuzzy_match_score(candidate_kw, query_kw)
            if score > best_score:
                best_score = score
                best_url = entry.get("url", "")

        if best_url and best_score >= 0.3:  # Minimum threshold
            log(f"[PurinaMills] Found match for '{query_text}': {best_url} (score={best_score:.2f})")
            return best_url

        # Try site search as fallback
        if self.enable_search_fallback and query_text:
            log(f"[PurinaMills] No good index match; trying site search for '{query_text}'")
            candidates = self._search_site(query_text, http_get, timeout, log)
            if candidates:
                best_cand = candidates[0]  # Take first result
                log(f"[PurinaMills] Site search found: {best_cand.get('url', '')}")
                return best_cand.get("url", "")

        log(f"[PurinaMills] No match found for UPC {upc}")
        return ""
