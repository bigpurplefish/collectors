"""
Product index management for Purinamills collector.

Builds and manages a runtime product index from the All Products collection.
"""

import re
import html
from typing import Dict, List, Set, Callable, Any, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote_plus
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import text_only


class ProductIndexer:
    """Manages product index for Purinamills."""

    def __init__(self, config: dict):
        """
        Initialize indexer.

        Args:
            config: Site configuration dict
        """
        self.origin = config.get("origin", "")
        self.all_products_path = config.get("all_products_path", "/collections/all-products")
        self.index_view_all = bool(config.get("index_view_all", True))
        self.index_page_param = str(config.get("index_page_param", "page"))
        self.max_index_pages = int(config.get("max_index_pages", 20))
        self.max_search_candidates = int(config.get("max_search_candidates", 30))

        self._product_index: List[Dict[str, Any]] = []

        # Common stop words
        self._common_stop: Set[str] = {
            "purina", "animal", "nutrition", "mills", "feed", "food", "formula",
            "complete", "original", "with", "and", "for", "high", "fat", "balanced",
            "pellet", "pellets", "crumbles", "textured", "supplement", "block",
            "mineral", "minerals", "all", "life", "stages"
        }

        # Synonyms
        self._syn: Dict[str, str] = {
            "equine": "horse", "bovine": "cattle", "beef": "cattle",
            "hen": "poultry", "chicken": "poultry", "layers": "layer",
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

    def _slug_tokens(self, url: str) -> Set[str]:
        """Extract tokens from URL slug."""
        try:
            path_last = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
        except Exception:
            path_last = ""
        toks = [t for t in re.split(r"[^a-z0-9]+", path_last.lower()) if t]
        out: Set[str] = set()
        for t in toks:
            if t and not t.isdigit():
                out.add(self._syn.get(t, t))
        return {t for t in out if t not in self._common_stop}

    def _entry_kw(self, display_name: str, url: str) -> Set[str]:
        """Get combined keyword set for an entry."""
        return self._keyword_set(display_name or "").union(self._slug_tokens(url))

    def _abs_url(self, href: str) -> str:
        """Convert relative URL to absolute."""
        if not href:
            return ""
        if href.startswith("http"):
            return href
        return f"{self.origin.rstrip('/')}/{href.lstrip('/')}"

    def _add_or_replace_query(self, url: str, key: str, value: str) -> str:
        """Add or replace query parameter in URL."""
        parts = urlsplit(url)
        qs = dict(parse_qsl(parts.query, keep_blank_values=True))
        qs[key] = value
        new_query = urlencode(qs, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    def _next_page_param_url(self, url: str) -> str:
        """Get next page URL by incrementing page parameter."""
        parts = urlsplit(url)
        qs = dict(parse_qsl(parts.query, keep_blank_values=True))
        key = self.index_page_param or "page"
        try:
            current = int(qs.get(key, "1"))
        except ValueError:
            current = 1
        qs[key] = str(current + 1)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(qs, doseq=True), parts.fragment))

    def _find_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Find next page URL from pagination links."""
        ln = soup.find("link", attrs={"rel": re.compile(r"\bnext\b", re.I)})
        if ln and ln.get("href"):
            return ln["href"]
        a_rel = soup.find("a", attrs={"rel": re.compile(r"\bnext\b", re.I)})
        if a_rel and a_rel.get("href"):
            return a_rel["href"]
        a_aria = soup.select_one('a[aria-label="Next"], a[aria-label="next"]')
        if a_aria and a_aria.get("href"):
            return a_aria["href"]
        a_text = soup.find("a", string=re.compile(r"\bnext\b", re.I))
        if a_text and a_text.get("href"):
            return a_text["href"]
        for a in soup.select(".pagination__item--next a, .next a, a.pagination__next"):
            href = a.get("href")
            if href:
                return href
        return None

    def build_index(
        self,
        http_get: Callable[..., Any],
        timeout: float,
        log: Callable[[str], None]
    ) -> None:
        """
        Build product index from All Products collection.

        Args:
            http_get: HTTP GET function
            timeout: Request timeout
            log: Logging function
        """
        if self._product_index:
            return

        base = f"{self.origin}{self.all_products_path}"
        visited_pages: Set[str] = set()
        seen_products: Set[str] = set()
        pages_fetched = 0

        start_urls: List[str] = []
        if self.index_view_all:
            start_urls.append(self._add_or_replace_query(base, "view", "all"))
        start_urls.append(base)

        for start in start_urls:
            url = start
            while url and pages_fetched < self.max_index_pages and url not in visited_pages:
                visited_pages.add(url)
                pages_fetched += 1

                log(f"[PurinaMills] Indexing page {pages_fetched}: {url}")

                try:
                    response = http_get(url, timeout=timeout)
                    html_text = response.text if hasattr(response, 'text') else str(response)
                except Exception as e:
                    log(f"[PurinaMills] Error fetching page: {e}")
                    break

                soup = BeautifulSoup(html_text, "html.parser")
                added_this_page = 0

                for a in soup.find_all("a", href=True):
                    href = (a["href"] or "").strip()
                    if not href or "/products/" not in href:
                        continue
                    full = self._abs_url(href)
                    if full in seen_products:
                        continue

                    name = a.get_text(" ", strip=True)
                    if not name:
                        head = a.find_next(["h1", "h2", "h3"])
                        name = head.get_text(" ", strip=True) if head else ""
                    seen_products.add(full)

                    kw = self._entry_kw(name, full)
                    if not name:
                        name = " ".join(sorted(kw)) or full.rsplit("/", 1)[-1]

                    self._product_index.append({
                        "name": html.unescape(name.replace("\xa0", " ").strip()),
                        "url": full,
                        "kw": kw
                    })
                    added_this_page += 1

                next_href = self._find_next_page_url(soup)
                next_url = self._abs_url(next_href) if next_href else None

                if not next_url and added_this_page > 0 and not self.index_view_all:
                    next_url = self._next_page_param_url(url)

                if not next_url or next_url in visited_pages:
                    break
                url = next_url

            if self.index_view_all and len(self._product_index) > 0:
                break

        if not self._product_index:
            log("[PurinaMills] Product index is empty; no products discovered.")
        else:
            log(f"[PurinaMills] Finished indexing {len(self._product_index)} products across {pages_fetched} page(s).")

    def get_index(self) -> List[Dict[str, Any]]:
        """Get the product index."""
        return self._product_index
