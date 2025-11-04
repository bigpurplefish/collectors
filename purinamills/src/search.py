"""
Search functionality for Purinamills collector.

Handles direct site search across shop.purinamills.com and www.purinamills.com.
Uses a 3-tier fallback strategy:
1. Exact match on description_1 (shop site)
2. Fuzzy match on description_1/upcitemdb_title (shop site)
3. Fallback to www.purinamills.com
"""

import re
from typing import Callable, Any, Optional, Dict, Set, List
from urllib.parse import quote_plus, urlsplit
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class PurinamillsSearcher:
    """Handles product search for Purinamills across both shop and www sites."""

    def __init__(self, config: dict):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
        """
        self.shop_origin = config.get("shop_origin", "https://shop.purinamills.com")
        self.www_origin = config.get("www_origin", "https://www.purinamills.com")
        self.shop_search_path = config.get("shop_search_path", "/search")
        self.www_search_path = config.get("www_search_path", "/search")
        self.shop_search_param = config.get("shop_search_param", "q")
        self.www_search_param = config.get("www_search_param", "q")
        self.max_search_candidates = int(config.get("max_search_candidates", 10))
        self.fuzzy_match_threshold = float(config.get("fuzzy_match_threshold", 0.3))

        # Common stop words for fuzzy matching
        self._common_stop: Set[str] = {
            "purina", "mills", "feed", "food", "formula", "complete", "original",
            "with", "and", "for", "high", "fat", "balanced", "supplement",
            "horse", "equine", "active", "senior", "animal", "nutrition"
        }

        # Synonyms for normalization
        self._syn: Dict[str, str] = {
            "equine": "horse",
            "hen": "poultry",
            "chicken": "poultry",
        }

    def _keyword_set(self, s: str) -> Set[str]:
        """Extract and normalize keyword set from text."""
        toks = [t for t in re.split(r"\W+", s.lower()) if t]
        out: Set[str] = set()
        for t in toks:
            if t.isdigit() or len(t) < 2:
                continue
            canon = self._syn.get(t, t)
            if canon in self._common_stop:
                continue
            out.add(canon)
        return out

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

    def _abs_url(self, href: str, origin: str) -> str:
        """Convert relative URL to absolute."""
        if not href:
            return ""
        href = href.strip()
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"{origin.rstrip('/')}{href}"
        return f"{origin.rstrip('/')}/{href}"

    def _search_shop_site(
        self,
        query: str,
        http_get: Callable[..., Any],
        timeout: float,
        log: Callable[[str], None]
    ) -> List[Dict[str, Any]]:
        """
        Search shop.purinamills.com for products.

        Returns:
            List of product candidates with name, url, and keywords
        """
        try:
            url = f"{self.shop_origin}{self.shop_search_path}?{self.shop_search_param}={quote_plus(query)}"
            log(f"[PurinaMills]   → Searching shop.purinamills.com: '{query}'")

            response = http_get(url, timeout=timeout)
            html_text = response.text if hasattr(response, 'text') else str(response)

            soup = BeautifulSoup(html_text, "html.parser")
            candidates = []
            seen = set()

            # Look for product links in search results
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "/products/" not in href:
                    continue

                # Extract clean URL (remove query params like _pos, _sid, _ss)
                full_url = self._abs_url(href, self.shop_origin)
                clean_url = urlsplit(full_url)._replace(query="", fragment="").geturl()

                if clean_url in seen:
                    continue
                seen.add(clean_url)

                # Extract product name
                name = a.get_text(" ", strip=True)
                if not name:
                    # Try to find nearby heading
                    parent = a.parent
                    if parent:
                        heading = parent.find(["h1", "h2", "h3", "h4"])
                        if heading:
                            name = heading.get_text(" ", strip=True)

                if name:
                    kw = self._keyword_set(name)
                    candidates.append({
                        "name": name,
                        "url": clean_url,
                        "kw": kw,
                        "source": "shop"
                    })

                if len(candidates) >= self.max_search_candidates:
                    break

            log(f"[PurinaMills]   → Found {len(candidates)} candidate(s) on shop site")
            return candidates

        except Exception as e:
            log(f"[PurinaMills]   ✗ Shop site search failed: {e}")
            return []

    def _search_www_site(
        self,
        query: str,
        http_get: Callable[..., Any],
        timeout: float,
        log: Callable[[str], None]
    ) -> List[Dict[str, Any]]:
        """
        Search www.purinamills.com for products.

        Returns:
            List of product candidates with name, url, and keywords
        """
        try:
            url = f"{self.www_origin}{self.www_search_path}?{self.www_search_param}={quote_plus(query)}"
            log(f"[PurinaMills]   → Searching www.purinamills.com: '{query}'")

            response = http_get(url, timeout=timeout)
            html_text = response.text if hasattr(response, 'text') else str(response)

            soup = BeautifulSoup(html_text, "html.parser")
            candidates = []
            seen = set()

            # Look for product detail links
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "/products/detail/" not in href and "/product/" not in href:
                    continue

                full_url = self._abs_url(href, self.www_origin)
                clean_url = urlsplit(full_url)._replace(query="", fragment="").geturl()

                if clean_url in seen:
                    continue
                seen.add(clean_url)

                # Extract product name
                name = a.get_text(" ", strip=True)
                if not name:
                    parent = a.parent
                    if parent:
                        heading = parent.find(["h1", "h2", "h3", "h4"])
                        if heading:
                            name = heading.get_text(" ", strip=True)

                if name:
                    kw = self._keyword_set(name)
                    candidates.append({
                        "name": name,
                        "url": clean_url,
                        "kw": kw,
                        "source": "www"
                    })

                if len(candidates) >= self.max_search_candidates:
                    break

            log(f"[PurinaMills]   → Found {len(candidates)} candidate(s) on www site")
            return candidates

        except Exception as e:
            log(f"[PurinaMills]   ✗ WWW site search failed: {e}")
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

        3-tier search strategy:
        1. Exact match using description_1 on shop site
        2. Fuzzy match using description_1/upcitemdb_title on shop site
        3. Fallback to www site

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

        if not product_data:
            log("[PurinaMills] No product data provided for matching.")
            return ""

        # Get search queries in priority order
        description_1 = (product_data.get("description_1") or "").strip()
        upcitemdb_title = (product_data.get("upcitemdb_title") or "").strip()

        if not description_1 and not upcitemdb_title:
            log("[PurinaMills] No product name available for search.")
            return ""

        # === Strategy 1: Exact match on description_1 (shop site) ===
        log(f"[PurinaMills] Strategy 1: Searching for exact match with description_1 on shop site")
        if description_1:
            candidates = self._search_shop_site(description_1, http_get, timeout, log)

            # Look for exact match (case-insensitive)
            description_1_lower = description_1.lower()
            for candidate in candidates:
                if description_1_lower in candidate["name"].lower() or \
                   candidate["name"].lower() in description_1_lower:
                    log(f"[PurinaMills] ✓ Exact match found on shop site: {candidate['url']}")
                    return candidate["url"]

        # === Strategy 2: Fuzzy match on description_1 (shop site) ===
        log(f"[PurinaMills] Strategy 2: Trying fuzzy match with description_1 on shop site")
        if description_1 and candidates:
            query_kw = self._keyword_set(description_1)
            best_score = 0.0
            best_url = ""

            for candidate in candidates:
                score = self._fuzzy_match_score(candidate["kw"], query_kw)
                if score > best_score:
                    best_score = score
                    best_url = candidate["url"]

            if best_score >= self.fuzzy_match_threshold:
                log(f"[PurinaMills] ✓ Fuzzy match found on shop site (score={best_score:.2f}): {best_url}")
                return best_url
            else:
                log(f"[PurinaMills] No fuzzy match above threshold (best score: {best_score:.2f}, threshold: {self.fuzzy_match_threshold})")

        # === Strategy 3: Try upcitemdb_title on shop site ===
        if upcitemdb_title and upcitemdb_title != description_1:
            log(f"[PurinaMills] Strategy 3: Trying fuzzy match with upcitemdb_title on shop site")
            candidates = self._search_shop_site(upcitemdb_title, http_get, timeout, log)

            if candidates:
                query_kw = self._keyword_set(upcitemdb_title)
                best_score = 0.0
                best_url = ""

                for candidate in candidates:
                    score = self._fuzzy_match_score(candidate["kw"], query_kw)
                    if score > best_score:
                        best_score = score
                        best_url = candidate["url"]

                if best_score >= self.fuzzy_match_threshold:
                    log(f"[PurinaMills] ✓ Match found on shop site using upcitemdb_title (score={best_score:.2f}): {best_url}")
                    return best_url
                else:
                    log(f"[PurinaMills] No match with upcitemdb_title (best score: {best_score:.2f})")

        # === Strategy 4: Fallback to www site ===
        log("[PurinaMills] Strategy 4: Falling back to www site")
        www_candidates = []

        if description_1:
            www_candidates = self._search_www_site(description_1, http_get, timeout, log)

        if not www_candidates and upcitemdb_title:
            www_candidates = self._search_www_site(upcitemdb_title, http_get, timeout, log)

        if www_candidates:
            # Take best fuzzy match from www site
            query_kw = self._keyword_set(description_1 or upcitemdb_title)
            best_score = 0.0
            best_url = ""

            for candidate in www_candidates:
                score = self._fuzzy_match_score(candidate["kw"], query_kw)
                if score > best_score:
                    best_score = score
                    best_url = candidate["url"]

            if best_score >= self.fuzzy_match_threshold:
                log(f"[PurinaMills] ✓ Match found on www site (score={best_score:.2f}): {best_url}")
                return best_url
            else:
                log(f"[PurinaMills] No match on www site above threshold (best score: {best_score:.2f})")

        log(f"[PurinaMills] ✗ No match found for UPC {upc} on either site")
        return ""
