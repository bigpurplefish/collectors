"""
Product search for Ethical Products collector.

Handles intelligent product discovery with sliding-scale matching.
"""

import re
from typing import Optional, Dict, Any, List, Tuple, Callable
from urllib.parse import urljoin, urlparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import normalize_upc
text_matching import (
    normalize_name,
    extract_canonical_flavors,
    extract_canonical_line,
    extract_form_tokens,
    infer_taxonomy,
)
size_matching import extract_sizes, sizes_match


class EthicalSearcher:
    """Handles intelligent product search for Ethical Products."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize searcher.

        Args:
            config: Site configuration
        """
        self.origin = config.get("origin", "")
        search_config = config.get("search", {})
        self.templates = search_config.get("templates", [])
        self.debug = search_config.get("debug", False)

    def search_site(
        self,
        query: str,
        http_get: Callable,
        timeout: int
    ) -> List[str]:
        """
        Search site for product candidates.

        Args:
            query: Search query
            http_get: HTTP GET function
            timeout: Request timeout

        Returns:
            List of candidate product URLs
        """
        url = urljoin(self.origin, f"/?s={query}")
        try:
            response = http_get(url, timeout, headers={})
            html = response.text if getattr(response, "status_code", 0) == 200 else ""
        except Exception:
            html = ""

        candidates = []
        # Find product URLs
        for match in re.finditer(r'href="([^"]+/product/[^"#?]+/)"', html, re.I):
            candidates.append(urljoin(self.origin, match.group(1)))
        for match in re.finditer(r'href="/product/([^"]+?)/"', html, re.I):
            candidates.append(urljoin(self.origin, f"/product/{match.group(1)}/"))

        # Deduplicate
        seen = set()
        result = []
        for url in candidates:
            if url not in seen:
                seen.add(url)
                result.append(url)

        return result[:12]

    def verify_product(
        self,
        pdp_url: str,
        query_norm: str,
        query_metadata: Dict[str, Any],
        http_get: Callable,
        timeout: int,
        log: Callable
    ) -> Tuple[float, Dict[str, Any], bool]:
        """
        Fetch and verify if product matches query.

        Args:
            pdp_url: Product page URL
            query_norm: Normalized query string
            query_metadata: Query metadata (taxonomy, flavors, sizes, etc.)
            http_get: HTTP GET function
            timeout: Request timeout
            log: Logging function

        Returns:
            Tuple of (score, metadata, is_match)
        """
        try:
            response = http_get(pdp_url, timeout, headers={})
            html = response.text if getattr(response, "status_code", 0) == 200 else ""
        except Exception:
            html = ""

        # Extract product title
        title = self._extract_title(html)
        title_norm = normalize_name(title)
        title_toks = title_norm.split()
        slug = urlparse(pdp_url).path.strip("/").split("/")[-1]

        # Extract product metadata
        taxo = self._extract_taxonomy(html)
        p_flavors = extract_canonical_flavors(html.upper())
        p_lines = extract_canonical_line(title_norm)
        p_forms = extract_form_tokens(title_norm)
        p_sizes = extract_sizes(title)

        # HARD GUARDS - reject mismatches
        expect_taxo = query_metadata.get("taxonomy", "")
        if expect_taxo == "cat" and ("dog" in taxo or re.search(r"\bdog\b", title, re.I)):
            return 0.0, {"reason": "reject: dog vs cat"}, False
        if expect_taxo == "dog" and ("cat" in taxo or re.search(r"\bcat\b", title, re.I)):
            return 0.0, {"reason": "reject: cat vs dog"}, False

        q_flavors = query_metadata.get("flavors", set())
        if q_flavors and not (q_flavors & p_flavors):
            return 0.0, {"reason": "reject: flavor mismatch"}, False

        q_lines = query_metadata.get("lines", set())
        if q_lines and not (q_lines & p_lines):
            return 0.0, {"reason": "reject: line mismatch"}, False

        q_sizes = query_metadata.get("sizes", {})
        if not sizes_match(q_sizes, p_sizes):
            return 0.0, {"reason": "reject: size mismatch"}, False

        # SLIDING-SCALE COVERAGE
        q_toks = query_norm.split()
        tset = set(title_toks + slug.upper().split("-"))
        matches = sum(1 for t in q_toks if t in tset)
        n_title = max(1, len(title_toks))
        coverage = matches / n_title
        q_cov = matches / max(1, len(q_toks))

        min_cov = 0.75 if n_title <= 4 else 0.60
        if matches < 2 or coverage < min_cov or q_cov < 0.50:
            return 0.0, {
                "reason": "below coverage",
                "cov": round(coverage, 2),
                "q_cov": round(q_cov, 2),
                "title_len": n_title
            }, False

        # Calculate score for ranking
        score = 1.2 * matches
        q_forms = query_metadata.get("forms", set())
        if q_forms:
            form_hits = len(q_forms & p_forms)
            score += 1.5 * form_hits if form_hits else -0.8

        slug_hits = sum(1 for tok in q_toks if tok and tok in slug.upper())
        if slug_hits >= 2:
            score += 0.6

        return score, {"title": title, "taxonomy": taxo, "cov": coverage}, True

    def find_best_match(
        self,
        candidates: List[str],
        query_norm: str,
        query_metadata: Dict[str, Any],
        http_get: Callable,
        timeout: int,
        log: Callable
    ) -> Optional[str]:
        """
        Find best matching product from candidates.

        Args:
            candidates: List of candidate URLs
            query_norm: Normalized query
            query_metadata: Query metadata
            http_get: HTTP GET function
            timeout: Request timeout
            log: Logging function

        Returns:
            Best matching URL or None
        """
        ranked = []
        for url in candidates[:10]:
            score, meta, ok = self.verify_product(
                url, query_norm, query_metadata, http_get, timeout, log
            )
            if ok:
                ranked.append((score, url, meta))
            elif self.debug:
                log(f"[ethical][debug] reject: {url} :: {meta.get('reason', '')}")

        ranked.sort(key=lambda x: x[0], reverse=True)

        if self.debug:
            log(f"[ethical][debug] cand-ranking for q='{query_norm}':")
            for score, url, meta in ranked[:5]:
                log(f"[ethical][debug]  - score={score:.2f} cov={meta.get('cov', 0):.2f} title='{meta.get('title', '')}' url={url}")

        if not ranked:
            return None

        best_score, best_url, _ = ranked[0]
        log(f"[ethical] match via name: q='{query_norm}' -> {best_url} (score={best_score:.2f})")
        return best_url

    def find_product_url(
        self,
        upc: str,
        http_get: Callable,
        timeout: int,
        log: Callable,
        product_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Find product URL for given UPC.

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout
            log: Logging function
            product_data: Optional product metadata

        Returns:
            Product URL or None
        """
        upc_digits = normalize_upc(upc)
        row = product_data or {}
        desc = (row.get("description_1") or "").strip()
        title = (row.get("upcitemdb_title") or "").strip()

        # Build query metadata
        taxonomy = infer_taxonomy(desc)
        q_flavors = extract_canonical_flavors(desc) or extract_canonical_flavors(title)
        q_lines = extract_canonical_line(desc) or extract_canonical_line(title)
        q_forms = extract_form_tokens(normalize_name(desc or title))
        q_sizes = extract_sizes(desc or title)

        metadata = {
            "taxonomy": taxonomy,
            "flavors": q_flavors,
            "lines": q_lines,
            "forms": q_forms,
            "sizes": q_sizes
        }

        # Try UPC search
        if upc_digits:
            for query in (upc_digits, f"%2B{upc_digits}"):
                candidates = self.search_site(query, http_get, timeout)
                hit = self.find_best_match(
                    candidates, query, metadata, http_get, timeout, log
                )
                if hit:
                    return hit

        # Try description search
        if desc:
            q_norm = normalize_name(desc)
            candidates = self.search_site(re.sub(r"\s+", "+", q_norm), http_get, timeout)
            hit = self.find_best_match(
                candidates, q_norm, metadata, http_get, timeout, log
            )
            if hit:
                return hit

        # Try title search
        if title:
            q_norm = normalize_name(title)
            candidates = self.search_site(re.sub(r"\s+", "+", q_norm), http_get, timeout)
            hit = self.find_best_match(
                candidates, q_norm, metadata, http_get, timeout, log
            )
            if hit:
                return hit

        return None

    @staticmethod
    def _extract_title(html: str) -> str:
        """Extract product title from HTML."""
        from shared.src import text_only

        patterns = [
            r'<div[^>]+class="summary[^"]*"[^>]*>.*?<h4[^>]*>(.*?)</h4>',
            r'<h1[^>]*class="product_title[^"]*"[^>]*>(.*?)</h1>',
            r'<h1[^>]*class="entry-title[^"]*"[^>]*>(.*?)</h1>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.I | re.DOTALL)
            if match:
                return text_only(match.group(1))

        match = re.search(r'<meta[^>]+itemprop="name"[^>]+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1).strip()

        match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_taxonomy(html: str) -> set:
        """Extract product taxonomy from HTML classes."""
        taxonomy = set()
        match = re.search(r'<div[^>]+class="product-details[^"]*"[^>]*>', html, re.I)
        if not match:
            return taxonomy

        classes = re.findall(r'class="([^"]+)"', match.group(0), re.I)
        cls = " ".join(classes)

        for slug in re.findall(r'product_cat-([a-z0-9\-]+)', cls, re.I):
            s = slug.lower()
            taxonomy.add(s)
            if "cat" in s:
                taxonomy.add("cat")
            if "dog" in s:
                taxonomy.add("dog")
            if any(k in s for k in ("dish", "bowl", "tableware", "stoneware")):
                taxonomy.add("dish")

        return taxonomy
