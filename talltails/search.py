"""
Search functionality for Talltails collector.

Handles UPC and name-based product search for Magento site.
"""

import re
from typing import Optional, Callable, Any, List, Set
from urllib.parse import quote_plus, urlsplit, urlunsplit
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import normalize_upc


class TalltailsSearcher:
    """Handles product search for Talltails."""

    def __init__(self, config: dict):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
        """
        self.origin = config.get("origin", "")
        self.preferred_host = urlsplit(self.origin).netloc or "www.talltailsdog.com"
        search_config = config.get("search", {})
        self.search_endpoint = search_config.get("endpoint", "/catalogsearch/result/?q={query}")

        # Learning settings
        learning = config.get("learning", {})
        self._UPC_DISABLE_THRESHOLD = int(learning.get("upc_disable_after", 5))
        self._upc_fail_count = 0
        self._upc_disabled = False

    def _force_host(self, url: str) -> str:
        """Force preferred host."""
        try:
            p = list(urlsplit(url if url.startswith("http") else "https://" + url))
            if self.preferred_host:
                p[1] = self.preferred_host
            if not p[0]:
                p[0] = "https"
            return urlunsplit(p)
        except Exception:
            return url

    def _build_search_url(self, query: str) -> str:
        """Build search URL."""
        enc_q = quote_plus(query or "")
        origin_fixed = self._force_host(self.origin).rstrip("/")
        return f"{origin_fixed}{self.search_endpoint.format(query=enc_q)}"

    @staticmethod
    def _score_title(name: str, query_text: str) -> float:
        """Score title match."""
        if not query_text:
            return 0.0
        nt = set(re.findall(r"[a-z0-9]+", name.lower()))
        qt = set(re.findall(r"[a-z0-9]+", query_text.lower()))
        inter = len(nt & qt)
        penalty = 0.10 * max(0, len(nt) - inter)
        return inter - penalty

    def _first_pdp_from_search(
        self,
        html: str,
        query_text: str = "",
        log: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Read the Magento search grid ONLY; ignore header/footer links."""
        s = BeautifulSoup(html, "html.parser")
        grid = s.select_one("div.products.wrapper.grid.products-grid ol.products.list.items.product-items")
        if not grid:
            if log:
                log("[talltailsdog] Search grid not found; trying alternates…")
            grid = (
                s.select_one("ol.products.list.items.product-items")
                or s.select_one("ol.products.products.list.items")
                or s.select_one("div.search.results ol.products.list.items.product-items")
            )
        if not grid:
            if log:
                log("[talltailsdog] No product grid on search results.")
            return None

        candidates: List[Tuple[str, str]] = []
        for li in grid.select("li.item.product.product-item"):
            a = li.select_one("a.product-item-link[href$='.html']")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            name = a.get_text(" ", strip=True)
            if not href:
                continue
            if any(
                bad in href
                for bad in (
                    "/blog",
                    "/catalogsearch",
                    "/customer",
                    "/account",
                    "/cart",
                    "/privacy",
                    "/terms",
                )
            ):
                continue
            candidates.append((href, name))

        if log:
            log(f"[talltailsdog] Search grid candidates: {len(candidates)}")
        if not candidates:
            return None

        if query_text:
            candidates.sort(key=lambda t: self._score_title(t[1], query_text), reverse=True)
            if log:
                top = candidates[0]
                log(f"[talltailsdog] Top tile by title score → name='{top[1]}' url={top[0]}")
        return candidates[0][0]

    @staticmethod
    def _normalize_variants(base: str) -> List[str]:
        """Generate search query variants."""
        if not base:
            return []
        s = base.strip()
        variants = {s}

        # 2IN1 family
        two_pats = [r"\b2\s*[-x×]?\s*in\s*[-x×]?\s*1\b", r"\b2in1\b"]
        two_repls = ["2IN1", "2 IN 1", "2-IN-1", "2in1", "2-in-1", "2 in 1", "2×1", "2 x 1"]
        for pat in two_pats:
            if re.search(pat, s, flags=re.I):
                for rep in two_repls:
                    variants.add(re.sub(pat, rep, s, flags=re.I))

        # Inches
        if '"' in s:
            for t in list(variants):
                variants.add(re.sub(r'(\d+)"', r"\1 in", t))
                variants.add(re.sub(r'(\d+)"', r"\1in", t).replace('"', ""))

        # AxB sizes
        size_pat = re.compile(r"\b(\d+)\s*[xX×/]\s*(\d+)\b")
        for t in list(variants):
            m = size_pat.search(t)
            if m:
                a, b = m.group(1), m.group(2)
                variants.update(
                    {
                        size_pat.sub(f"{a}x{b}", t),
                        size_pat.sub(f"{a} x {b}", t),
                        size_pat.sub(f"{a}×{b}", t),
                        size_pat.sub(f"{a}/{b}", t),
                    }
                )

        # hyphens ↔ spaces
        for t in list(variants):
            variants.add(t.replace("-", " "))

        # GRIZZLE -> GRIZZLY
        for t in list(variants):
            variants.add(re.sub(r"\bgrizzle\b", "grizzly", t, flags=re.I))

        # normalize
        normed, seen = [], set()
        for t in variants:
            t2 = re.sub(r"\s+", " ", t).strip()
            key = t2.lower()
            if key not in seen and t2:
                seen.add(key)
                normed.append(t2)
        normed.sort(key=lambda x: (0 if x.lower() == s.lower() else 1, len(x)))
        return normed[:12]

    def find_product_url(
        self,
        upc: str,
        http_get: Callable[..., Any],
        timeout: int,
        log: Callable[[str], None],
        product_data: Optional[dict] = None
    ) -> Optional[str]:
        """
        Find product page URL for a given UPC.

        Args:
            upc: UPC to search for
            http_get: HTTP GET function
            timeout: Request timeout
            log: Logging function
            product_data: Optional product data for name fallback

        Returns:
            Product URL or None if not found
        """
        if not upc:
            return None

        # Row-specific origin (if present)
        origin = self.origin
        if isinstance(product_data, dict):
            home = (
                product_data.get("manufacturer_homepage_found")
                or product_data.get("manufacturer_homepage")
                or ""
            ).strip()
            if home:
                origin = home
        origin = self._force_host(origin).rstrip("/")

        def is_pdp(ht: str) -> bool:
            return (
                'class="product-info-main"' in (ht or "")
                or 'data-gallery-role="gallery"' in (ht or "")
                or '"@type":"Product"' in (ht or "")
                or "'@type':'Product'" in (ht or "")
            )

        # 1) UPC search (disable after threshold)
        ran_upc = False
        if self._upc_disabled:
            log(
                f"[talltailsdog] Skipping UPC search (disabled after {self._upc_fail_count} misses; "
                f"threshold={self._UPC_DISABLE_THRESHOLD})."
            )
        else:
            ran_upc = True
            try:
                search_url = self._build_search_url(upc)
                log(f"[talltailsdog] UPC search URL: {search_url}")
                r = http_get(search_url, timeout=timeout)
                srch_html = getattr(r, "text", "") or ""
                cand = self._first_pdp_from_search(srch_html, query_text=upc, log=log)
                if cand:
                    log(f"[talltailsdog] Candidate PDP from UPC search: {cand} — validating…")
                    pr = http_get(cand, timeout=timeout)
                    cand_html = getattr(pr, "text", "") or ""
                    if is_pdp(cand_html):
                        log(f"[talltailsdog] Valid PDP (UPC): {cand} — resetting UPC fail counter.")
                        self._upc_fail_count = 0
                        return cand
                    else:
                        self._upc_fail_count += 1
                else:
                    self._upc_fail_count += 1

                if not self._upc_disabled and self._upc_fail_count >= self._UPC_DISABLE_THRESHOLD:
                    self._upc_disabled = True
                    log(f"[talltailsdog] Disabling UPC search (consecutive misses={self._upc_fail_count}).")
            except Exception as e:
                log(f"[talltailsdog] UPC search error: {e}")
                self._upc_fail_count += 1
                if not self._upc_disabled and self._upc_fail_count >= self._UPC_DISABLE_THRESHOLD:
                    self._upc_disabled = True

        # 2) Name search (upcitemdb_title then description_1)
        for key in ("upcitemdb_title", "description_1"):
            q_base = (product_data or {}).get(key, "") or ""
            if not q_base:
                continue
            variants = self._normalize_variants(q_base)
            prefix = "Fallback" if ran_upc or self._upc_disabled else "Primary name search"
            log(f"[talltailsdog] {prefix} by {key}: generated {len(variants)} variants.")
            for qi, q in enumerate(variants, 1):
                try:
                    search_url = self._build_search_url(q)
                    log(f"[talltailsdog]  • Variant {qi}/{len(variants)}: {search_url}")
                    r = http_get(search_url, timeout=timeout)
                    srch_html = getattr(r, "text", "") or ""
                    cand = self._first_pdp_from_search(srch_html, query_text=q, log=log)
                    if not cand:
                        continue
                    log(f"[talltailsdog]    ↳ Candidate: {cand} — validating…")
                    pr = http_get(cand, timeout=timeout)
                    cand_html = getattr(pr, "text", "") or ""
                    if is_pdp(cand_html):
                        log(f"[talltailsdog] Valid PDP ({key} variant): {cand}")
                        return cand
                except Exception as e:
                    log(f"[talltailsdog] {key} variant search error: {e}")

        log(f"[talltailsdog] Exhausted all search methods for UPC {upc}.")
        return None
