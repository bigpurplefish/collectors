#!/usr/bin/env python3
"""
Purinamills Product Collector

Collects product data from https://shop.purinamills.com.
"""

import os
import re
import json
import html
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

# Site Configuration (embedded from profile)
SITE_CONFIG = {
    "site_key": "purinamills",
    "origin": "https://shop.purinamills.com",
    "referer": "https://shop.purinamills.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "fetch_jitter_min_ms": 200,
    "fetch_jitter_max_ms": 700,
    "candidate_cap": 8,
    "hl": "en",
    "gl": "us",
    "bv_auth_required": false,
    "bv_base_url": "",
    "bv_common_params": {},
    "requires_catalog": false,
    "all_products_path": "/collections/all-products",
    "name_index_json": "/mnt/data/key=PURINA_part=001_count=146.json",
    "requires_name_index": true
}

# strategies/purinamills.py
from __future__ import annotations

import os
import re
import json
import html
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from urllib.parse import (
    urlparse, urlunparse, urlsplit, urlunsplit, parse_qsl, urlencode, quote_plus
)

from bs4 import BeautifulSoup

from .base import SiteStrategy, abs_url


class PurinaMillsStrategy(SiteStrategy):
    """
    Purina Animal Nutrition (shop.purinamills.com) strategy.

    Discovery
    ---------
    - Purina Mills PDPs do NOT expose UPCs; discovery is fuzzy by product name.
    - Build a runtime product index from the All Products collection (with pagination).
    - Fuzzy-match the current record’s name (best of upcitemdb_title / description_1).
    - If weak → server-side `/search?q=` fallback. If still weak → Google CSE by UPC (creds ONLY via .env).

    Parsing (key points)
    --------------------
    - Brand + product name:
        • brand_hint = token(s) BEFORE the first "®" (e.g., "Purina")
        • title      = everything AFTER the first "®" (trim a single leading space)
    - Description: <div class="product__description ..."> (desktop + mobile supported)
    - Benefits: strict pairing of <p><strong>Title</strong></p> → next <p>Description</p>
    - Gallery images: **ONLY** images inside recognized gallery containers; variant/size aware
    - Nutrition:
        • nutrition_text: stacked-card-list HTML (<ul><li>) converted from the “Nutrients”/Guaranteed Analysis table
          (desktop tabs and mobile accordion supported)
    - Directions:
        • directions_for_use: Shopify-compatible HTML (<ul><li>…</li></ul> + optional <p><strong>Caution:</strong> …</p>)
          (desktop tabs and mobile accordion supported)

    Variant awareness
    -----------------
    - Extract normalized size token (e.g., "10 LB", "32 OZ") from the input record/title or PDP “Size” selector.
    - Prefer gallery images associated with the target variant id or with filenames that hint the size.
    """

    # ------------------------------ lifecycle / config ------------------------------
    def __init__(self, profile: Optional[Dict[str, Any]] = None):
        super().__init__(profile)
        self._session = None
        self._auth: Optional[Dict[str, Any]] = None

        self._all_products_path: str = (self.profile.get("all_products_path")
                                        or "/collections/all-products").strip()

        self._index_view_all: bool = bool(self.profile.get("index_view_all", True))
        self._index_page_param: str = str(self.profile.get("index_page_param", "page"))
        self._max_index_pages: int = int(self.profile.get("max_index_pages", 20))

        self._enable_search_fallback: bool = bool(self.profile.get("enable_search_fallback", True))
        self._max_search_candidates: int = int(self.profile.get("max_search_candidates", 30))

        # Google CSE fallback — CREDS ONLY VIA .ENV
        self._enable_google_cse: bool = bool(self.profile.get("enable_google_cse", True))
        self._cse_key: Optional[str] = os.getenv("GOOGLE_CSE_API_KEY") or None
        self._cse_cx:  Optional[str] = os.getenv("GOOGLE_CSE_ID") or None
        self._cse_num: int = int(self.profile.get("cse_num", 10))

        self._product_index: List[Dict[str, Any]] = []

        self._common_stop: Set[str] = {
            "purina", "animal", "nutrition", "mills",
            "feed", "food", "formula", "complete", "original",
            "with", "and", "for", "high", "fat", "balanced",
            "pellet", "pellets", "crumbles", "textured",
            "supplement", "block", "mineral", "minerals",
            "all", "life", "stages"
        }
        self._syn: Dict[str, str] = {
            "equine": "horse",
            "bovine": "cattle",
            "beef": "cattle",
            "hen": "poultry",
            "chicken": "poultry",
            "layers": "layer",
        }

        # Per-record desired size (normalized "NN UNIT", e.g., "50 LB")
        self._desired_size_norm: Optional[str] = None

    # ------------------------------ optional integration hooks ------------------------------
    def attach_session(self, session) -> None:
        self._session = session

    def set_auth(self, auth: Dict[str, Any] | None) -> None:
        self._auth = auth or None

    # ------------------------------ HTTP helpers ------------------------------
    def _http_get_text(self, url: str, http_get, timeout: float, log: Callable[[str], None]) -> str:
        try:
            resp = http_get(url, timeout=timeout, headers={"User-Agent": self.ua, "Referer": self.referer})
            if not resp:
                return ""
            return getattr(resp, "text", resp) or ""
        except Exception as e:
            log(f"[PurinaMills] GET failed {url} : {e}")
            return ""

    def _http_get_json(self, url: str, http_get, timeout: float, log: Callable[[str], None]) -> Optional[dict]:
        try:
            resp = http_get(url, timeout=timeout, headers={
                "User-Agent": self.ua, "Referer": self.referer, "Accept": "application/json"
            })
            if not resp:
                return None
            if hasattr(resp, "json"):
                return resp.json()
            text = getattr(resp, "text", "") or ""
            return json.loads(text) if text else None
        except Exception as e:
            log(f"[PurinaMills] JSON GET failed {url} : {e}")
            return None

    # ------------------------------ pagination helpers ------------------------------
    def _add_or_replace_query(self, url: str, key: str, value: str) -> str:
        parts = urlsplit(url)
        qs = dict(parse_qsl(parts.query, keep_blank_values=True))
        qs[key] = value
        new_query = urlencode(qs, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    def _next_page_param_url(self, url: str) -> str:
        parts = urlsplit(url)
        qs = dict(parse_qsl(parts.query, keep_blank_values=True))
        key = self._index_page_param or "page"
        try:
            current = int(qs.get(key, "1"))
        except ValueError:
            current = 1
        qs[key] = str(current + 1)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(qs, doseq=True), parts.fragment))

    def _find_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        ln = soup.find("link", attrs={"rel": re.compile(r"\bnext\b", re.I)})
        if ln and ln.get("href"): return ln["href"]
        a_rel = soup.find("a", attrs={"rel": re.compile(r"\bnext\b", re.I)})
        if a_rel and a_rel.get("href"): return a_rel["href"]
        a_aria = soup.select_one('a[aria-label="Next"], a[aria-label="next"]')
        if a_aria and a_aria.get("href"): return a_aria["href"]
        a_text = soup.find("a", string=re.compile(r"\bnext\b", re.I))
        if a_text and a_text.get("href"): return a_text["href"]
        for a in soup.select(".pagination__item--next a, .next a, a.pagination__next"):
            href = a.get("href")
            if href: return href
        return None

    # ------------------------------ tokenization helpers ------------------------------
    def _expand_abbrev(self, s: str) -> str:
        if not s: return ""
        s = s.replace("&", " and ")
        repl = {
            "supp": "supplement", "supp.": "supplement", "suppl": "supplement",
            "bal": "balancer", "bal.": "balancer",
            "pel": "pellet", "pel.": "pellet", "plts": "pellets", "plt": "pellet",
            "crmb": "crumbles", "crmb.": "crumbles", "crmble": "crumbles",
            "txt": "textured", "txt.": "textured",
            "blk": "block", "blk.": "block",
            "min": "mineral", "mins": "minerals",
            "chk": "chicken", "chkn": "chicken",
            "turk": "turkey", "trky": "turkey",
            "sal": "salmon", "salm": "salmon",
            "swt": "sweet", "brn": "brown", "rc": "rice",
            "w/": "with", "w\\": "with", "ls": "low starch", "l/s": "low starch", "als": "all life stages",
        }
        s = re.sub(r"[\/_,()\-]+", " ", s)
        tokens = [t for t in re.split(r"\s+", s) if t]
        out = []
        for t in tokens:
            key = t.lower().strip(".")
            out.append(repl.get(key, t))
        return " ".join(out)

    def _clean_name(self, name: str) -> str:
        if not name: return ""
        s = self._expand_abbrev(name)
        s = re.sub(r"\b\d+(?:\.\d+)?\s*(?:lb|lbs|pound|pounds|oz|ounce|ounces|gal|gallon|kg|g|gram|grams)\b", "", s, flags=re.I)
        s = re.sub(r"\b\d+(?:\.\d+)?\s*(?:lb|lbs|oz|gal|kg)\s*(?:bag|bags)\b", "", s, flags=re.I)
        return re.sub(r"\s+", " ", s).strip()

    def _keyword_set(self, s: str) -> Set[str]:
        toks = [t for t in re.split(r"\W+", s.lower()) if t]
        out: Set[str] = set()
        for t in toks:
            if t.isdigit() or len(t) < 2: continue
            canon = self._syn.get(t, t)
            if canon in self._common_stop: continue
            out.add(canon)
        return out

    def _slug_tokens(self, url: str) -> Set[str]:
        try:
            path_last = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        except Exception:
            path_last = ""
        toks = [t for t in re.split(r"[^a-z0-9]+", path_last.lower()) if t]
        out: Set[str] = set()
        for t in toks:
            if t and not t.isdigit():
                out.add(self._syn.get(t, t))
        return {t for t in out if t not in self._common_stop}

    def _entry_kw(self, display_name: str, url: str) -> Set[str]:
        return self._keyword_set(self._clean_name(display_name or "")).union(self._slug_tokens(url))

    # ------------------------------ size parsing helpers ------------------------------
    _SIZE_RE = re.compile(r"\b(\d{1,2})\s*([oO][zZ]|[lL][bB][sS]?|[gG][aA][lL]|[kK][gG]|[gG]|[qQ][tT]|[pP][tT])\b")

    @staticmethod
    def _norm_size_unit(unit: str) -> str:
        u = unit.strip().lower()
        return {"lb": "LB", "lbs": "LB", "oz": "OZ", "gal": "GAL",
                "kg": "KG", "g": "G", "qt": "QT", "pt": "PT"}.get(u, u.upper())

    @classmethod
    def _norm_size_token(cls, s: str) -> Optional[str]:
        if not s: return None
        m = cls._SIZE_RE.search(s)
        if not m: return None
        return f"{m.group(1)} {cls._norm_size_unit(m.group(2))}"

    # ------------------------------ indexing + pagination ------------------------------
    def _build_product_index(self, http_get, timeout: float, log: Callable[[str], None]) -> None:
        if self._product_index:
            return

        base = f"{self.origin}{self._all_products_path}"
        visited_pages: set[str] = set()
        seen_products: set[str] = set()
        pages_fetched = 0

        start_urls: List[str] = []
        if self._index_view_all:
            start_urls.append(self._add_or_replace_query(base, "view", "all"))
        start_urls.append(base)

        for start in start_urls:
            url = start
            while url and pages_fetched < self._max_index_pages and url not in visited_pages:
                visited_pages.add(url)
                pages_fetched += 1

                log(f"[PurinaMills] Indexing page {pages_fetched}: {url}")
                html_text = self._http_get_text(url, http_get, timeout, log)
                if not html_text:
                    break

                soup = BeautifulSoup(html_text, "html.parser")
                added_this_page = 0

                for a in soup.find_all("a", href=True):
                    href = (a["href"] or "").strip()
                    if not href or "/products/" not in href:
                        continue
                    full = abs_url(self.origin, href)
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

                    self._product_index.append({"name": html.unescape(name.replace("\xa0", " ").strip()),
                                                "url": full,
                                                "kw": kw})
                    added_this_page += 1

                next_href = self._find_next_page_url(soup)
                next_url = abs_url(self.origin, next_href) if next_href else None

                if not next_url and added_this_page > 0 and not self._index_view_all:
                    next_url = self._next_page_param_url(url)

                if not next_url or next_url in visited_pages:
                    break
                url = next_url

            if self._index_view_all and len(self._product_index) > 0:
                break

        if not self._product_index:
            log("[PurinaMills] Product index is empty; no products discovered.")
        else:
            log(f"[PurinaMills] Finished indexing {len(self._product_index)} products across {pages_fetched} page(s).")

    # ------------------------------ site search fallback ------------------------------
    def _search_candidates(self, http_get, timeout: float, log: Callable[[str], None], query: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.origin}/search?q={quote_plus(query)}"
            html_text = self._http_get_text(url, http_get, timeout, log)
            if not html_text:
                return []
            soup = BeautifulSoup(html_text, "html.parser")
            out: List[Dict[str, Any]] = []
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "/products/" not in href:
                    continue
                full = abs_url(self.origin, href)
                if full in seen:
                    continue
                seen.add(full)
                name = a.get_text(" ", strip=True)
                kw = self._entry_kw(name, full)
                if not name:
                    name = " ".join(sorted(kw)) or full.rsplit("/", 1)[-1]
                out.append({"name": name, "url": full, "kw": kw})
                if len(out) >= self._max_search_candidates:
                    break
            return out
        except Exception as e:
            log(f"[PurinaMills] Search fallback failed for '{query}': {e}")
            return []

    # ------------------------------ Google CSE fallback (env-only creds) ------------------------------
    def _cse_best_name_from_upc(self, http_get, timeout: float, log: Callable[[str], None], upc: str) -> str:
        if not self._enable_google_cse or not self._cse_key or not self._cse_cx:
            return ""
        try:
            q = quote_plus(upc)
            url = (f"https://www.googleapis.com/customsearch/v1?"
                   f"key={self._cse_key}&cx={self._cse_cx}&num={self._cse_num}&q={q}")
            data = self._http_get_json(url, http_get, timeout, log) or {}
            items = data.get("items") or []
            best_clean = ""
            best_kw_len = -1

            for it in items:
                link = str(it.get("link") or "")
                if "shop.purinamills.com" in link:
                    continue
                title = str(it.get("title") or "")
                clean = self._clean_name(title)
                kw = self._keyword_set(clean)
                if len(kw) > best_kw_len:
                    best_kw_len = len(kw)
                    best_clean = clean
            return best_clean
        except Exception as e:
            log(f"[PurinaMills] Google CSE lookup failed for UPC {upc}: {e}")
            return ""

    # ------------------------------ discovery ------------------------------

    def find_product_page_url_for_upc(
        self,
        upc: str,
        http_get: Callable[..., Any],
        timeout: float,
        log: Callable[[str], None],
        product_data: Optional[Dict[str, Any]] = None,  # optional convenience; callers need not pass
    ) -> str:
        """
        Locate a PDP URL for a given UPC on shop.purinamills.com.
        Returns a string URL when found, or "" if not found (aligns with SiteStrategy contract).
        """
        if not upc:
            log("[PurinaMills] No UPC provided.")
            return ""

        try:
            # Build or reuse a name/UPC → URL index (implementation assumed elsewhere in this class)
            self._build_product_index(http_get, timeout, log)
            if not getattr(self, "_product_index", None):
                log("[PurinaMills] Product index unavailable or empty.")
                return ""

            # Normalize UPC to 12 digits (leading zeros allowed) if needed
            norm_upc = upc.strip()
            if norm_upc.isdigit() and len(norm_upc) < 12:
                norm_upc = norm_upc.zfill(12)

            # Direct hit
            url = self._product_index.get(norm_upc) or self._product_index.get(upc)
            if not url:
                log(f"[PurinaMills] No match in index for UPC {upc} (normalized {norm_upc}).")
                return ""

            # Ensure absolute URL
            abs_url = self.abs_url(url, base=self.profile.get("origin", "https://shop.purinamills.com"))
            log(f"[PurinaMills] Found PDP for UPC {upc}: {abs_url}")
            return abs_url or ""
        except Exception as e:
            log(f"[PurinaMills] Error resolving UPC {upc}: {e}")
            return ""

    # ------------------------------ parsing helpers ------------------------------
    @staticmethod
    def _strip_queries(u: str) -> str:
        try:
            p = urlparse(u)
            return urlunparse((p.scheme or "https", p.netloc, p.path, "", "", ""))
        except Exception:
            return u.split("?", 1)[0].split("#", 1)[0]

    @staticmethod
    def _norm_text(s: str) -> str:
        if not s: return ""
        s = s.replace("\xa0", " ").replace("&nbsp;", " ")
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    # ----- brand + product name parsing -----
    @staticmethod
    def _extract_brand_and_product_name_from_title(raw_title_html: str) -> Tuple[str, str]:
        if not raw_title_html:
            return "", ""
        s = html.unescape(re.sub(r"\s+", " ", raw_title_html)).strip()
        m = re.search(r"®", s)
        if not m:
            parts = s.split(" ", 1)
            return (parts[0], parts[1] if len(parts) > 1 else "")
        brand = s[:m.start()].strip()
        name = s[m.end():].lstrip()
        return (brand, name)

    def _title_brand_from_dom(self, soup: BeautifulSoup) -> Tuple[str, str]:
        title_node = None
        wrap = soup.select_one(".product__title.show_on_desktop") or soup.select_one(".product__title")
        if wrap:
            title_node = wrap.find(["h1", "h2"]) or wrap.select_one("a.product__title h1, a.product__title h2")
        if not title_node:
            title_node = soup.find(["h1", "h2"])
        raw = title_node.get_text(" ", strip=True) if title_node else ""
        return self._extract_brand_and_product_name_from_title(raw)

    # ----- features & benefits -----
    def _parse_features_benefits_pairs(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        def collect_from_container(container) -> List[Dict[str, str]]:
            results: List[Dict[str, str]] = []
            seen_titles: Set[str] = set()
            if not container: return results
            ps = [p for p in container.find_all("p", recursive=True)]
            i = 0
            while i < len(ps):
                p = ps[i]
                strong = p.find("strong")
                if strong:
                    title = self._norm_text(strong.get_text(" ", strip=True))
                    desc = ""
                    if i + 1 < len(ps) and not ps[i + 1].find("strong"):
                        desc = self._norm_text(ps[i + 1].get_text(" ", strip=True))
                        i += 1
                    key = title.lower()
                    if title and key not in seen_titles:
                        seen_titles.add(key)
                        results.append({"title": title, "description": desc})
                i += 1
            return results

        panel = soup.find(id=re.compile(r"tab[-_]?one[-_]?panel", re.I)) \
                or soup.find("div", class_=re.compile(r"metafield[-_]rich_text_field", re.I)) \
                or soup.find("section", attrs={"aria-labelledby": re.compile(r"features.*benefits", re.I)})

        benefits = collect_from_container(panel)

        if not benefits:
            head = soup.find(lambda tag: tag.name and re.search(r"features\s*&?\s*benefits", tag.get_text(" ", strip=True), re.I))
            container = head.find_next(lambda t: t.name in ("div", "section", "article") and t.get_text(strip=True)) if head else None
            benefits = collect_from_container(container) if container else []

        if not benefits:
            benefits = collect_from_container(soup)

        out: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for b in benefits:
            key = (b.get("title", "") + "||" + b.get("description", "")).strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(b)
        return out

    # ----- variant & gallery helpers -----
    def _parse_size_options_and_variants(self, soup: BeautifulSoup) -> Tuple[Dict[str, str], Optional[str]]:
        """
        Returns (size_norm -> variant_id, default_selected_size_norm)
        """
        size_to_vid: Dict[str, str] = {}
        selected_norm: Optional[str] = None

        select = soup.select_one('select[name="options[Size]"]') or soup.select_one('select.variant_select_dropdown')
        if select:
            for opt in select.find_all("option"):
                label = self._norm_text(opt.get_text(" ", strip=True))
                norm = self._norm_size_token(label) or (label.upper() if label else None)
                vid = (opt.get("data-vid") or "").strip()
                if norm and vid:
                    size_to_vid.setdefault(norm, vid)
                if opt.has_attr("selected") and norm:
                    selected_norm = norm

        vs_script = None
        for sc in soup.find_all("script", {"type": "application/json"}):
            txt = sc.get_text(strip=True) or ""
            if '"option1"' in txt and '"id"' in txt and '"sku"' in txt:
                vs_script = sc
                break
        if vs_script:
            try:
                variants = json.loads(vs_script.get_text() or "[]")
                if isinstance(variants, list):
                    for v in variants:
                        o1 = self._norm_size_token(str(v.get("option1") or "")) or None
                        vid = str(v.get("id") or "").strip()
                        if o1 and vid:
                            size_to_vid.setdefault(o1, vid)
            except Exception:
                pass

        return size_to_vid, selected_norm

    def _gallery_image_urls(self, soup: BeautifulSoup, prefer_vid: Optional[str], prefer_size_norm: Optional[str]) -> List[str]:
        """
        Return image URLs ONLY from likely product gallery containers.
        Prioritize images associated with the target variant id or that hint the size in filename/alt.
        """
        gallery_selectors = [
            ".product__media", ".product__media-list", ".product__gallery", ".product-gallery",
            ".product__slideshow", ".product__images", ".product-media", ".product__main-photos",
            "#ProductMediaGallery", "#product-media-gallery", "[data-product-gallery]",
            ".gallery", ".product-gallery__media", ".product__slides"
        ]
        containers: List[BeautifulSoup] = []
        for sel in gallery_selectors:
            containers.extend(soup.select(sel))
        if not containers:
            near_title = soup.select_one(".product, .product-single, article.product")
            if near_title:
                maybe = near_title.select_one(".media, .gallery, .images, .product__media")
                if maybe:
                    containers = [maybe]

        def pick_from_srcset(srcset: str) -> str:
            try:
                parts = [p.strip() for p in srcset.split(",") if p.strip()]
                if not parts:
                    return ""
                last = parts[-1].split()[0]
                return last
            except Exception:
                return ""

        size_hints: List[str] = []
        if prefer_size_norm:
            try:
                n, u = prefer_size_norm.split()
                u = u.lower()
                size_hints = [f"{n}{u}", f"{n}-{u}", f"{n}_{u}", f"{n}%20{u}", f"{n}%2B{u}"]
            except Exception:
                pass

        seen = set()
        all_gallery: List[str] = []
        by_vid: List[str] = []
        by_size_hint: List[str] = []

        def consider_url(url: str, node) -> None:
            if not url:
                return
            full = abs_url(self.origin, url)
            full = self._strip_queries(full.replace("http://", "https://", 1))
            if full in seen:
                return
            seen.add(full)

            matched_vid = False
            if prefer_vid:
                try:
                    for anc in node.parents:
                        for k, v in (anc.attrs or {}).items():
                            val = " ".join(v) if isinstance(v, list) else str(v)
                            if prefer_vid and prefer_vid in val:
                                matched_vid = True
                                break
                        if matched_vid:
                            break
                except Exception:
                    pass

            url_l = full.lower()
            alt_l = (node.get("alt") or "").lower()
            matched_size = any(h in url_l or h in alt_l for h in size_hints) if size_hints else False

            if matched_vid:
                by_vid.append(full)
            elif matched_size:
                by_size_hint.append(full)
            else:
                all_gallery.append(full)

        for c in containers:
            for img in c.find_all("img"):
                src = (img.get("data-src") or img.get("data-original") or img.get("src") or "").strip()
                if not src and img.get("srcset"):
                    src = pick_from_srcset(img.get("srcset") or "")
                if not src:
                    continue
                alt = (img.get("alt") or "").strip().lower()
                if re.search(r"(logo|icon|cart|retailer|find a retailer)", alt, re.I):
                    continue
                consider_url(src, img)
            for source in c.find_all("source"):
                srcset = (source.get("data-srcset") or source.get("srcset") or "").strip()
                if not srcset:
                    continue
                best = pick_from_srcset(srcset)
                if best:
                    consider_url(best, source)

        out = by_vid or by_size_hint or all_gallery
        return out

    # ----- description / nutrition / directions -----
    def _parse_description(self, soup: BeautifulSoup) -> str:
        node = soup.select_one(".product__description.rte.quick-add-hidden.show_on_desktop") \
            or soup.select_one(".product__description.rte") \
            or soup.select_one(".product__description")
        if not node:
            return ""
        txt = node.get_text(" ", strip=True)
        return self._norm_text(html.unescape(txt))

    # Nutrition container finders (desktop tab + mobile accordion + fallbacks)
    def _find_nutrition_container(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        # Desktop tab is typically #tab-two-panel
        panel = soup.find(id=re.compile(r"tab[-_]?two[-_]?panel", re.I))
        if panel and panel.find("table"):
            return panel

        # Mobile accordion under product-information
        for item in soup.select(".product-information .accordion .accordion-item"):
            btn = item.select_one(".accordion-header .accordion-button")
            if btn and re.search(r"\b(nutrients?|guaranteed\s+analysis)\b", btn.get_text(" ", strip=True), re.I):
                body = item.select_one(".accordion-body")
                if body and body.find("table"):
                    return body

        # Any figure.table after a heading/label mentioning nutrients
        label = soup.find(lambda tag: tag.name in ("label", "h2", "h3", "p", "strong")
                          and re.search(r"\b(nutrients?|guaranteed\s+analysis)\b", tag.get_text(" ", strip=True), re.I))
        if label:
            cont = label.find_next(lambda t: t.name in ("div", "section", "article") and t.find("table"))
            if cont:
                return cont

        return soup.select_one("figure.table:has(table)")

    def _parse_nutrition_rows(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        cont = self._find_nutrition_container(soup)
        if not cont:
            return []
        table = cont.find("table")
        if not table:
            return []
        rows = []
        for tr in table.find_all("tr"):
            cells = [self._norm_text(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if len(cells) >= 3:
                rows.append({"Nutrients": cells[0], "Min / Max": cells[1], "Amount": cells[2]})
        if rows and re.search(r"\bnutrients?\b", rows[0]["Nutrients"], re.I):
            rows = rows[1:]
        return rows

    def _stacked_cards_from_rows(self, rows: List[Dict[str, str]]) -> str:
        if not rows:
            return ""
        li_parts = []
        for r in rows:
            li_parts.append(
                f'<li style="padding:.75rem;border:1px solid #ddd;border-radius:.5rem;">'
                f'<strong>Nutrients:</strong> {html.escape(r["Nutrients"])}<br>'
                f'<strong>Min / Max:</strong> {html.escape(r["Min / Max"])}<br>'
                f'<strong>Amount:</strong> {html.escape(r["Amount"])}'
                f'</li>'
            )
        return (
            '<ul style="list-style:none;margin:0;padding:0;display:grid;gap:.75rem;">'
            + "".join(li_parts) +
            "</ul>"
        )

    def _parse_nutrition_stacked_html(self, soup: BeautifulSoup) -> str:
        rows = self._parse_nutrition_rows(soup)
        return self._stacked_cards_from_rows(rows)

    # Directions container finders (desktop tab + mobile accordion + fallbacks)
    def _find_directions_container(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        # Desktop tab often #tab-three-panel
        panel = soup.find(id=re.compile(r"tab[-_]?three[-_]?panel", re.I))
        if panel and (panel.find("ul") or panel.find("p")):
            return panel

        # Mobile accordion item with "Feeding Directions" / "Directions"
        for item in soup.select(".product-information .accordion .accordion-item"):
            btn = item.select_one(".accordion-header .accordion-button")
            if btn and re.search(r"\b(feeding\s+directions?|directions\s+for\s+use)\b", btn.get_text(" ", strip=True), re.I):
                body = item.select_one(".accordion-body")
                if body and (body.find("ul") or body.find("p")):
                    return body

        # Fallback: heading text
        head = soup.find(lambda tag: tag.name in ("h1", "h2", "h3", "h4", "p", "strong")
                         and re.search(r"\b(feeding\s+directions?|directions\s+for\s+use)\b", tag.get_text(" ", strip=True), re.I))
        if head:
            parent = head.find_parent()
            if parent and (parent.find("ul") or parent.find("p")):
                return parent
        return None

    def _parse_directions_for_use_html(self, soup: BeautifulSoup) -> str:
        cont = self._find_directions_container(soup)
        if not cont:
            return ""
        out_parts: List[str] = []

        # Normalize any primary bullet list
        ul = cont.find("ul")
        if ul:
            items = []
            for li in ul.find_all("li"):
                txt = self._norm_text(li.get_text(" ", strip=True))
                if txt:
                    items.append(f"<li>{html.escape(txt)}</li>")
            if items:
                out_parts.append("<ul>" + "".join(items) + "</ul>")

        # Capture Caution paragraph (keep strong label)
        caution_node = cont.find(string=re.compile(r"\bCaution:", re.I))
        if caution_node:
            p = caution_node.find_parent("p") or cont.find("p")
            if p:
                txt = self._norm_text(p.get_text(" ", strip=True))
                if txt:
                    txt = re.sub(r"^Caution:\s*", "<strong>Caution:</strong> ", txt, flags=re.I)
                    out_parts.append(f"<p>{txt}</p>")

        # If no UL and we have paragraphs, keep them (Shopify-safe <p>)
        if not out_parts:
            ps = [self._norm_text(p.get_text(" ", strip=True)) for p in cont.find_all("p")]
            ps = [t for t in ps if t]
            if ps:
                out_parts.append("".join(f"<p>{html.escape(t)}</p>" for t in ps))

        return "".join(out_parts)

    # ------------------------------ parsing (main) ------------------------------

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Parse a Purina Mills PDP HTML document and return a dict with EXACT keys required by CollectionApp:
        {
            "model_product": None or dict,
            "title": str,
            "brand_hint": str,
            "benefits": list[{"title": str, "description": str}],
            "description": str,
            "gallery_images": list[str],
            # Optional but used by your master app:
            "nutrition_text": str,
            "directions_for_use": str
        }
        Notes:
        - Prefers JSON-LD Product blocks; graceful DOM fallbacks.
        - Image URLs are cleaned (querystring stripped) and made absolute via self.abs_url().
        - Benefits: extracts bullet lists under headings like "Benefits", "Features", "Why it works".
        """
        def _clean_url(u: str) -> str:
            if not u:
                return ""
            u = u.strip().strip('"').strip("'")
            # Remove typical image proxy/query artifacts
            qpos = u.find("?")
            if qpos != -1:
                u = u[:qpos]
            return self.abs_url(u, base=self.profile.get("origin", "https://shop.purinamills.com")) or ""

        def _clean_urls(urls: List[str]) -> List[str]:
            seen, out = set(), []
            for u in urls:
                cu = _clean_url(u)
                if cu and cu not in seen:
                    seen.add(cu)
                    out.append(cu)
            return out

        def _text(s: str) -> str:
            if not s:
                return ""
            # Shopify normalizer expectations: plain text, no inline styles/classes
            s = unescape(s)
            # Strip HTML tags quickly (lightweight)
            s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
            s = re.sub(r"<[^>]+>", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            return s

        def _json_search(pattern: str) -> Any:
            m = re.search(pattern, html_text, flags=re.S | re.I)
            if not m:
                return None
            blob = m.group(1).strip()
            # Try to locate JSON object/array boundaries
            # Handles cases like: var modelProduct = {...}; or "modelProduct": {...}
            # Heuristic: find the first '{' and match until balanced.
            start = blob.find("{")
            if start == -1:
                return None
            # Balance braces
            depth = 0
            end = start
            while end < len(blob):
                ch = blob[end]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end += 1
                        break
                end += 1
            if depth != 0:
                return None
            try:
                return json.loads(blob[start:end])
            except Exception:
                return None

        # -------- 1) JSON-LD Product extraction --------
        title = ""
        brand_hint = "Purina"
        description = ""
        gallery_images: List[str] = []
        nutrition_text = ""
        directions_for_use = ""
        model_product = None

        # Collect all JSON-LD <script type="application/ld+json"> blocks
        for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_text,
            flags=re.S | re.I,
        ):
            script = m.group(1).strip()
            # Some sites embed multiple JSON objects or arrays in a single script tag
            candidates: List[Any] = []
            try:
                data = json.loads(script)
                candidates.append(data)
            except Exception:
                # Try to recover by wrapping into array brackets if it looks like multiple roots
                script_fixed = script
                try:
                    data = json.loads(script_fixed)
                    candidates.append(data)
                except Exception:
                    pass

            for c in candidates:
                # Normalize into a list of dicts
                items = c if isinstance(c, list) else [c]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    t = item.get("@type") or item.get("type")
                    if isinstance(t, list):
                        is_product = "Product" in t
                    else:
                        is_product = (t == "Product")
                    if not is_product:
                        continue

                    if not title:
                        title = _text(item.get("name", "")) or title
                    # brand can be string or object
                    b = item.get("brand")
                    if isinstance(b, dict):
                        brand_hint = _text(b.get("name", "")) or brand_hint
                    elif isinstance(b, str):
                        brand_hint = _text(b) or brand_hint

                    if not description:
                        description = _text(item.get("description", "")) or description

                    imgs = item.get("image")
                    if isinstance(imgs, list):
                        gallery_images.extend([str(x) for x in imgs if isinstance(x, (str,))])
                    elif isinstance(imgs, str):
                        gallery_images.append(imgs)

        # -------- 2) Model Product (embedded JSON) --------
        # Common patterns: window.__PRODUCT_JSON__ = {...}; or "modelProduct": {...}
        model_product = (
            _json_search(r'modelProduct\s*[:=]\s*({.*?})')
            or _json_search(r'window\.__PRODUCT_JSON__\s*=\s*({.*?})')
            or _json_search(r'var\s+modelProduct\s*=\s*({.*?})')
        )

        # If model_product has images/variants, prefer variant/gallery lists
        if isinstance(model_product, dict):
            # Try common keys
            mp_images = []
            # Look for flattened images
            if isinstance(model_product.get("ProductImage"), str):
                mp_images.append(model_product["ProductImage"])
            # Lifestyle images array
            if isinstance(model_product.get("LifestyleImages"), list):
                mp_images.extend([x for x in model_product["LifestyleImages"] if isinstance(x, str)])
            # Generic 'images' key
            if isinstance(model_product.get("images"), list):
                mp_images.extend([x.get("src", x) if isinstance(x, dict) else x for x in model_product["images"]])

            gallery_images = mp_images + gallery_images

            # Use title/description if missing
            if not title:
                title = _text(model_product.get("Title") or model_product.get("title") or "")
            if not description:
                description = _text(model_product.get("Description") or model_product.get("description") or "")

            # Nutrition / Directions (if present in model JSON)
            nutrition_text = _text(model_product.get("Nutrition") or nutrition_text)
            directions_for_use = _text(model_product.get("Directions") or directions_for_use)

        # -------- 3) Fallbacks from DOM (title, description, images) --------
        if not title:
            m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.S | re.I)
            if m:
                title = _text(m.group(1))
        if not description:
            # Try meta description or a PDP description container
            m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html_text, flags=re.I)
            if m:
                description = _text(m.group(1))
            else:
                m = re.search(r'<div[^>]+class=["\'][^"\']*(?:product-description|pdp-description)[^"\']*["\'][^>]*>(.*?)</div>', html_text, flags=re.S | re.I)
                if m:
                    description = _text(m.group(1))

        if not gallery_images:
            # og:image + any <img> inside product gallery containers
            ogs = re.findall(r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']', html_text, flags=re.I)
            gallery_images.extend(ogs)
            gallery_imgs = re.findall(
                r'<img[^>]+(?:data-src|src)=["\'](.*?)["\'][^>]*>',
                html_text,
                flags=re.I,
            )
            gallery_images.extend(gallery_imgs)

        # -------- 4) Benefits extraction (bullets under "Benefits"/"Features") --------
        benefits: List[Dict[str, str]] = []
        # Capture sections starting at headings containing target words, then the following <ul>...</ul>
        for sec in re.finditer(
            r'(<h[1-6][^>]*>\s*(?:Benefits?|Features?|Why\s+it\s+Works)[^<]*</h[1-6]>\s*(?:</?div[^>]*>\s*){0,3}\s*<ul[^>]*>.*?</ul>)',
            html_text,
            flags=re.S | re.I,
        ):
            ul = re.search(r"<ul[^>]*>(.*?)</ul>", sec.group(1), flags=re.S | re.I)
            if not ul:
                continue
            for li in re.findall(r"<li[^>]*>(.*?)</li>", ul.group(1), flags=re.S | re.I):
                item = _text(li)
                if item:
                    # Per your convention: store text in "description"; title left empty
                    benefits.append({"title": "", "description": item})
            if benefits:
                break  # first matching section is enough

        # -------- 5) Final normalization --------
        title = title or ""
        brand_hint = brand_hint or "Purina"
        description = description or ""
        nutrition_text = nutrition_text or ""
        directions_for_use = directions_for_use or ""
        gallery_images = _clean_urls(gallery_images)

        return {
            "model_product": model_product if isinstance(model_product, dict) else None,
            "title": title,
            "brand_hint": brand_hint,
            "benefits": benefits,
            "description": description,
            "gallery_images": gallery_images,
            # Optional fields honored by your master app:
            "nutrition_text": nutrition_text,
            "directions_for_use": directions_for_use,
        }

    # ----- simple section collector (used for Ingredients) -----
    def _collect_section_after_heading(self, root: BeautifulSoup, head_regex: str) -> str:
        """
        Find a heading-like node that matches head_regex and collect following text until next major heading.
        Returns plain text joined by newlines.
        """
        stop_heads = re.compile(r"^(features|benefits|nutrients?|guaranteed|analysis|feeding|directions?|instructions?|warranty|caution)\b", re.I)
        head = root.find(lambda tag: tag.name in ("h1", "h2", "h3", "h4", "h5", "p", "strong", "div")
                                   and re.search(head_regex, tag.get_text(" ", strip=True), re.I))
        if not head:
            return ""

        texts: List[str] = []
        node = head
        seen_head = False
        if node.name == "p" and node.find("strong") and re.search(head_regex, node.get_text(" ", strip=True), re.I):
            seen_head = True

        while True:
            node = node.find_next()
            if not node:
                break
            if getattr(node, "name", None) in ("script", "style"):
                continue
            if node.name and re.match(r"h\d", node.name):
                if stop_heads.search(node.get_text(" ", strip=True)):
                    break
            if node.name in ("p", "div"):
                strong = node.find("strong")
                if strong and re.search(stop_heads, strong.get_text(" ", strip=True)):
                    break

            if node.name in ("p", "li"):
                txt = self._norm_text(node.get_text(" ", strip=True))
                if txt:
                    if not seen_head and re.search(head_regex, txt, re.I):
                        seen_head = True
                        continue
                    texts.append(txt)
            if node.name in ("ul", "ol"):
                for li in node.find_all("li"):
                    txt = self._norm_text(li.get_text(" ", strip=True))
                    if txt:
                        texts.append(txt)

        out_lines: List[str] = []
        seen = set()
        for t in texts:
            key = t.lower()
            if key not in seen:
                seen.add(key)
                out_lines.append(t)
        return "\n".join(out_lines).strip()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Purinamills Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
