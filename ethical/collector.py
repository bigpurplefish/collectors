#!/usr/bin/env python3
"""
Ethical Products (SPOT) Product Collector

Collects product data from https://www.ethicalpet.com.
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
    "site_key": "ethical",
    "display_name": "Ethical Products (SPOT)",
    "homepage": "https://www.ethicalpet.com",
    "origin": "https://www.ethicalpet.com",
    "referer": "https://www.ethicalpet.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "search": {
        "templates": [
            "https://www.ethicalpet.com/?s={q}"
        ],
        "max_candidates": 8,
        "pause_sec": [
            0.8,
            1.6
        ],
        "manufacturer_aliases": [
            "Ethical Products",
            "Ethical Product",
            "Ethical Pets",
            "Ethical Pet",
            "Ethical",
            "SPOT",
            "Spot"
        ],
        "verify_min_token_hits": 2,
        "brand_weight": 2,
        "debug": true,
        "prime_homepage": true,
        "send_browser_headers": true
    },
    "product_url_allow": [
        "/product/"
    ],
    "disallow": [
        "/cart",
        "/account",
        "/wp-admin",
        "/wp-login.php"
    ],
    "timeouts": {
        "connect": 15,
        "read": 45
    },
    "retry": {
        "tries": 3,
        "backoff": 1.8
    },
    "parsing": {
        "use_selenium": true,
        "desc_selectors": [
            ".woocommerce-product-details__short-description",
            ".summary .woocommerce-product-details__short-description",
            "article .entry-content",
            ".entry-content"
        ],
        "gallery_selectors": {
            "carousel_images": "div.elastislide-carousel ul.elastislide-list li img[data-largeimg]"
        },
        "strict_carousel_only": true
    },
    "selenium": {
        "enabled": true,
        "browser": "chrome",
        "headless": true,
        "driver_path": null,
        "binary_path": null,
        "page_load_timeout_sec": 40,
        "implicit_wait_sec": 0,
        "wait_selector_timeout_sec": 25,
        "extra_args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1400,1800"
        ],
        "lang": "en-US,en",
        "simulate_click_from_search": true
    },
    "images": {
        "download": true,
        "base_dir": "images/ethical",
        "validate_http_200": true,
        "strip_query": true,
        "dedupe_by": [
            "normalized_url",
            "sha256"
        ],
        "allowed_hosts": [
            "ethicalpet.com",
            "www.ethicalpet.com"
        ]
    },
    "output": {
        "brand": "Ethical Products",
        "manufacturer_key": "manufacturer",
        "plain_text_descriptions": true,
        "variant_gallery_only": true
    }
}

# strategies/ethical.py
# Ethical Products — sliding-scale, size-aware matching + resilient max-size gallery
#
# Backward-compatible parse_page(html) keys used by your GUI:
#   - title (str)
#   - brand_hint (str)        -> "Ethical Products"
#   - description (plain text)
#   - gallery_images (list[str], absolute, queryless, deduped, max-sized)
#   - gallery_summary (str)   -> optional
#   - log_lines (list[str])   -> optional
#   - manufacturer (dict)     -> richer block (safe to ignore)
#
from __future__ import annotations
import html as _html
import re
import time
from typing import Any, Dict, List, Optional, Callable, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from .base import SiteStrategy

# --- Optional Selenium (used only as a last resort) ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

SITE_KEY = "ethical"
HttpGet = Callable[[str, float, Optional[Dict[str, str]]], Any]

# ---------------------- tiny utils ----------------------
_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")
_URL_Q = re.compile(r"[?#].*$")
_SIZE_SUFFIX = re.compile(r"-(\d{2,4}x\d{2,4})(?=\.[a-z]{3,4}$)", re.I)

def _strip_query(u: str) -> str: return _URL_Q.sub("", u or "")
def _abs(base: str, maybe: str) -> str:
    if not maybe: return ""
    if maybe.startswith(("http://","https://")): return maybe
    if maybe.startswith("//"): return "https:" + maybe
    return urljoin(base.rstrip("/") + "/", maybe.lstrip("/"))
def _norm_spaces(s: str) -> str: return _WS.sub(" ", (s or "").strip())
def _unique(seq: List[str]) -> List[str]:
    seen=set(); out=[]
    for x in seq:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out
def _plain(html: Optional[str]) -> str:
    if not html: return ""
    txt = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r"\s*\n\s*", "\n", txt)
    return txt.strip()
def _tokens(s: str) -> List[str]: return [t for t in (s or "").split() if t]
def _norm_base(n: str) -> str:
    n = (n or "").replace("″", '"').replace("’","'").replace("”",'"').replace("“",'"')
    n = re.sub(r"[^A-Za-z0-9\- ]+", " ", n)
    return _norm_spaces(n)

# ---------------------- flavor / line / form ----------------------
_FLAVOR_CANON = {
    "PEANUT BUTTER": {"PEANUT","PEANUTBUTTER","PB","PEANUT-BUTTER","PEANUT_BUTTER"},
    "BACON": {"BACON"},
    "APPLE": {"APPLE"},
    "GINGERBREAD": {"GINGERBREAD"},
}
_LINE_CANON = {
    "PLAY STRONG": {"PLAYSTRONG","PLAY-STRONG","FOAMZ","SCENT-SATION","SCENTSATION"},
    "BARRETT": {"BARRETT"},
    "BAMBONE": {"BAMBONE","BAM-BONE","BAM BONE"},
    "SKINNEEEZ": {"SKINNEEEZ","SKINEEZ","SKINNEEZ"},
}
_FORM_TOKENS = {
    "BALL","BONE","TRIPOD","X-BONE","XBONE","WISHBONE","DINO","RING",
    "DISH","BOWL","FEEDER","BRIDGE","CHEW","TUG","STICK",
}
_CAT_HINT = re.compile(r"\b(?:CAT|KITTY|KITTEN|LITTER)\b", re.I)
_DOG_HINT = re.compile(r"\b(?:DOG|PUP|PUPPY|CANINE)\b", re.I)
_DISH_HINT = re.compile(r"\b(?:BOWL|DISH|FEEDER|STONEWARE|CERAMIC)\b", re.I)
_NUM_IN = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:\"|IN|INCH|INCHES)\b", re.I)
_NUM_ONLY = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\b")
_MFR_WORDS = re.compile(r"\b(?:ETHICAL(?:\s+PRODUCTS?)?|SPOT)\b", re.I)
_QTY_WORDS = re.compile(r"\b(?:COUNT|CT|PACK|PK|BULK|ASSTD|ASST|ASSORTED|EACH|EA|SET|BX|BOX|PDQ|DISPLAY|CASE)\b", re.I)
_SIZE_WORDS = re.compile(r"\b(?:OZ|OUNCES?|LB|LBS?|POUNDS?|G|GRAMS?|KG|MLS?|ML|L|LITERS?|QT|QTS?|QUARTS?|GALS?|GAL|IN|INCH(?:ES)?)\b", re.I)

def _spacify(s: str) -> str: return _WS.sub(" ", (s or "").strip())
def _singularize_simple(tok: str) -> str:
    if tok.endswith("IES") and len(tok)>3: return tok[:-3]+"Y"
    if tok.endswith("S") and not tok.endswith("SS"): return tok[:-1]
    return tok
def _normalize_name(raw: str) -> str:
    s = _spacify(raw)
    s = _MFR_WORDS.sub(" ", s)
    s = s.replace("-", "")
    s = _QTY_WORDS.sub(" ", s)
    s = _SIZE_WORDS.sub(" ", s)
    s = re.sub(r'\b(?:WITH|W/|W|AND|&|THE|FOR|OF|TO|PLUS|EXTRA|NEW|OR)\b', " ", s, flags=re.I)
    s = re.sub(r'[/"“”‘’()+,]', " ", s)
    s = _WS.sub(" ", s).strip().upper()
    parts = s.split()
    if parts: parts[0] = _singularize_simple(parts[0])
    return " ".join(parts)
def _canon_flavors(text: str) -> set:
    u = (text or "").upper().replace("-", " ").replace("_", " ")
    toks = set(_NON_ALNUM.split(u))
    out=set()
    for canon, alts in _FLAVOR_CANON.items():
        if canon in u or alts.intersection(toks): out.add(canon)
    return out
def _canon_line(text: str) -> set:
    u = (text or "").upper().replace("-", "")
    toks = set(_tokens(u))
    out=set()
    for canon, alts in _LINE_CANON.items():
        if canon in u or alts.intersection(toks): out.add(canon)
    return out
def _form_tokens(text: str) -> set:
    toks = set(_tokens(text or ""))
    if "XBONE" in toks: toks.add("X-BONE")
    return {t for t in toks if t in _FORM_TOKENS}

# -------- taxonomy expectation (helper that was missing in your run) --------
def _expected_taxo_from_text(raw: str) -> str:
    txt = (raw or "")
    if _DISH_HINT.search(txt): return "dish"
    if _CAT_HINT.search(txt):  return "cat"
    if _DOG_HINT.search(txt):  return "dog"
    # brand-ish clues:
    if re.search(r"\bSKINNEEEZ|SKINEEZ|SILVER\s*VINE|KITTY|CATNIP|TEASER|LITTER|FEATHER|FELT\b", txt, re.I): return "cat"
    if re.search(r"\bPLAY\s*STRONG|BAMBONE|BARRETT\b", txt, re.I): return "dog"
    return ""

# ---------------- size extraction & comparison ----------------
_UNIT_FAMILY_MAP = {
    "IN": ("IN", 1.0),
    "OZ": ("OZ", 1.0), "OUNCE": ("OZ", 1.0), "OUNCES": ("OZ", 1.0),
    "LB": ("OZ", 16.0), "LBS": ("OZ", 16.0), "POUND": ("OZ", 16.0), "POUNDS": ("OZ", 16.0),
    "G": ("G", 1.0), "GRAM": ("G", 1.0), "GRAMS": ("G", 1.0), "KG": ("G", 1000.0),
    "ML": ("ML", 1.0), "MLS": ("ML", 1.0), "L": ("ML", 1000.0), "LITER": ("ML", 1000.0), "LITERS": ("ML", 1000.0),
    "QT": ("QT", 1.0), "QTS": ("QT", 1.0), "QUART": ("QT", 1.0), "QUARTS": ("QT", 1.0),
    "GAL": ("QT", 4.0), "GALS": ("QT", 4.0), "GALLON": ("QT", 4.0), "GALLONS": ("QT", 4.0),
}
def _extract_sizes_all(text: str) -> Dict[str, List[float]]:
    fam: Dict[str, List[float]] = {}
    if not text: return fam
    s = " " + text.upper().replace("”", '"').replace("“", '"') + " "
    for m in re.finditer(r'(?<!\d)(\d+(?:\.\d+)?)\s*(?:\"|INCH(?:ES)?|IN)\b', s, re.I):
        fam.setdefault("IN", []).append(float(m.group(1)))
    for m in re.finditer(r'(?<!\d)(\d+(?:\.\d+)?)\s*([A-Z]+)\b', s):
        val = float(m.group(1)); unit = m.group(2).upper()
        if unit in _UNIT_FAMILY_MAP:
            base, mult = _UNIT_FAMILY_MAP[unit]
            fam.setdefault(base, []).append(val * mult)
    return fam
def _sizes_match(q: Dict[str, List[float]], p: Dict[str, List[float]], tol_ratio=0.08) -> bool:
    for fam, pvals in p.items():
        if not pvals: continue
        qvals = q.get(fam, [])
        if not qvals: continue
        ok=False
        for pv in pvals:
            for qv in qvals:
                if pv and abs(pv - qv)/pv <= tol_ratio:
                    ok=True; break
            if ok: break
        if not ok: return False
    return True

# ============================ STRATEGY ============================
class EthicalStrategy(SiteStrategy):
    def __init__(self, profile: Dict[str, Any]):
        super().__init__(profile)
        self._session=None
        self._last_product_url: Optional[str] = None
        self._last_search_url: Optional[str] = None
        self._primed=False

        self.origin  = (profile.get("origin") or profile.get("homepage") or "").rstrip("/")
        self.referer = profile.get("referer") or (self.origin + "/")
        self.ua      = profile.get("user_agent") or "Mozilla/5.0"

        s = profile.get("search") or {}
        self.tpls: List[str] = s.get("templates") or ["https://www.ethicalpet.com/?s={q}"]
        self.max_candidates = int(s.get("max_candidates", 8))
        self.aliases: List[str] = s.get("manufacturer_aliases") or []
        self.min_hits = int(s.get("verify_min_token_hits", 2))
        self.brand_weight = int(s.get("brand_weight", 2))
        self.debug = bool(s.get("debug", False))
        self.prime_home = bool(s.get("prime_homepage", True))
        self.send_browser_headers = bool(s.get("send_browser_headers", True))
        self.allow: List[str] = profile.get("product_url_allow") or ["/product/"]

        p = profile.get("parsing") or {}
        self.use_selenium = bool(p.get("use_selenium", True))
        self.desc_selectors = p.get("desc_selectors") or [
            ".woocommerce-product-details__short-description",
            ".summary .woocommerce-product-details__short-description",
            "article .entry-content",
            ".entry-content",
        ]
        gsel = (p.get("gallery_selectors") or {})
        self.carousel_selector = gsel.get("carousel_images","div.elastislide-carousel ul.elastislide-list li img[data-largeimg]")
        self.carousel_alternates = ["#demo2carousel img[data-largeimg]", ".elastislide-carousel .elastislide-list img[data-largeimg]"]
        self.strict_carousel_only = bool(p.get("strict_carousel_only", True))

        t = profile.get("timeouts") or {}
        self.t_connect = float(t.get("connect", 15))
        self.t_read    = float(t.get("read", 45))

        sel = profile.get("selenium") or {}
        self.sel_enabled = bool(sel.get("enabled", True))
        self.sel_browser = (sel.get("browser") or "chrome").lower()
        self.sel_headless = bool(sel.get("headless", True))
        self.sel_driver_path = sel.get("driver_path")
        self.sel_binary_path = sel.get("binary_path")
        self.sel_page_load_timeout = int(sel.get("page_load_timeout_sec", 40))
        self.sel_implicit_wait = int(sel.get("implicit_wait_sec", 0))
        self.sel_wait_selector_timeout = int(sel.get("wait_selector_timeout_sec", 25))
        self.sel_extra_args = sel.get("extra_args") or ["--no-sandbox","--disable-dev-shm-usage","--window-size=1400,1800"]
        self.sel_lang = sel.get("lang") or "en-US,en"
        self.sel_simulate_click = bool(sel.get("simulate_click_from_search", True))

    # ---- GUI hook ----
    def attach_session(self, session): self._session=session
    def set_auth(self, *a, **k): pass
    def set_catalog_path(self, *a, **k): pass

    # ---- http helpers ----
    def _headers(self, origin: str) -> Dict[str,str]:
        return {
            "User-Agent": self.ua,
            "Referer": self.referer or origin,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }
    def _prime_session(self, http_get: HttpGet, timeout: float):
        if self._primed or not self.prime_home: return
        try: http_get(self.origin + "/", timeout, headers=self._headers(self.origin))
        except Exception: pass
        self._primed=True
    def _search_page(self, q: str, http_get: HttpGet, timeout: float) -> Optional[BeautifulSoup]:
        self._prime_session(http_get, timeout)
        for tpl in self.tpls:
            url = tpl.format(q=q)
            r=None
            try: r = http_get(url, timeout, headers=self._headers(self.origin))
            except Exception: r=None
            if r and getattr(r, "status_code", 0) == 200:
                self._last_search_url = url
                return BeautifulSoup(r.text or "", "html.parser")
        return None

    # ---------------- discovery (sliding-scale, size-aware) ----------------
    def find_product_page_url_for_upc(
        self, upc: str, http_get: HttpGet, timeout: float, log, product_data: Optional[Dict[str,Any]]=None, **kwargs
    ) -> Optional[str]:
        base = self.origin
        upc = (upc or "").strip()
        row = product_data or {}
        desc = (row.get("description_1") or "").strip()
        traw = (row.get("upcitemdb_title") or "").strip()

        expect_taxo = _expected_taxo_from_text(desc)
        q_flavors = _canon_flavors(desc) or _canon_flavors(traw)
        q_lines   = _canon_line(desc)   or _canon_line(traw)
        q_forms   = _form_tokens(_normalize_name(desc or traw))
        q_sizes   = _extract_sizes_all(desc or traw)

        def search_site(q: str) -> List[str]:
            url = urljoin(base, f"/?s={q}")
            try:
                r = http_get(url, timeout, headers=self._headers(base))
                html = r.text if getattr(r,"status_code",0) == 200 else ""
            except Exception:
                html = ""
            cands=[]
            for m in re.finditer(r'href="([^"]+/product/[^"#?]+/)"', html, re.I): cands.append(urljoin(base, m.group(1)))
            for m in re.finditer(r'href="/product/([^"]+?)/"', html, re.I):      cands.append(urljoin(base, f"/product/{m.group(1)}/"))
            out, seen=[], set()
            for u in cands:
                if u not in seen: seen.add(u); out.append(u)
            return out[:12]

        def _pdp_title(html: str) -> str:
            for patt in (r'<div[^>]+class="summary[^"]*"[^>]*>.*?<h4[^>]*>(.*?)</h4>', r'<h1[^>]*class="product_title[^"]*"[^>]*>(.*?)</h1>', r'<h1[^>]*class="entry-title[^"]*"[^>]*>(.*?)</h1>'):
                m = re.search(patt, html, re.I|re.S)
                if m: return _spacify(_strip_html(m.group(1)))
            m = re.search(r'<meta[^>]+itemprop="name"[^>]+content="([^"]+)"', html, re.I)
            if m: return m.group(1).strip()
            m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
            return m.group(1).strip() if m else ""

        def _pdp_taxonomy(html: str) -> set:
            out=set(); root = re.search(r'<div[^>]+class="product-details[^"]*"[^>]*>', html, re.I)
            if not root: return out
            classes = re.findall(r'class="([^"]+)"', root.group(0), re.I)
            cls=" ".join(classes)
            for slug in re.findall(r'product_cat-([a-z0-9\-]+)', cls, re.I):
                s=slug.lower(); out.add(s)
                if "cat" in s: out.add("cat")
                if "dog" in s: out.add("dog")
                if any(k in s for k in ("dish","bowl","tableware","stoneware")): out.add("dish")
            return out

        def _pdp_flavors(html: str) -> set:
            title=_pdp_title(html).upper(); text=title+" "+(html or "").upper()
            found=set()
            for canon, alts in _FLAVOR_CANON.items():
                if canon in text or any(a in text for a in alts): found.add(canon)
            return found
        def _pdp_line(title_norm: str) -> set: return _canon_line(title_norm)
        def _title_tokens(title: str) -> List[str]: return _tokens(_normalize_name(title))

        def fetch_and_verify(pdp_url: str, q_norm: str) -> Tuple[float, Dict[str, Any], bool]:
            try:
                r = http_get(pdp_url, timeout, headers=self._headers(base))
                html = r.text if getattr(r,"status_code",0) == 200 else ""
            except Exception:
                html = ""

            title = _pdp_title(html)
            title_norm = _normalize_name(title)
            title_toks = _title_tokens(title)
            slug = urlparse(pdp_url).path.strip("/").split("/")[-1]
            taxo = _pdp_taxonomy(html)
            p_flavors = _pdp_flavors(html)
            p_lines   = _pdp_line(title_norm)
            p_forms   = _form_tokens(title_norm)
            p_sizes   = _extract_sizes_all(title)

            # HARD GUARDS
            if expect_taxo == "cat" and ("dog" in taxo or _DOG_HINT.search(title)): return 0.0, {"reason":"reject: dog vs cat"}, False
            if expect_taxo == "dog" and ("cat" in taxo or _CAT_HINT.search(title)): return 0.0, {"reason":"reject: cat vs dog"}, False
            if q_flavors and not (q_flavors & p_flavors): return 0.0, {"reason":"reject: flavor mismatch"}, False
            if q_lines   and not (q_lines   & p_lines):   return 0.0, {"reason":"reject: line mismatch"},   False
            if not _sizes_match(q_sizes, p_sizes, tol_ratio=0.08): return 0.0, {"reason":"reject: size mismatch"}, False

            # SLIDING-SCALE COVERAGE
            q_toks = _tokens(q_norm)
            tset   = set(title_toks + _tokens(slug.upper()))
            matches = sum(1 for t in q_toks if t in tset)
            n_title = max(1, len(title_toks))
            coverage = matches / n_title
            q_cov    = matches / max(1, len(q_toks))
            min_cov  = 0.75 if n_title <= 4 else 0.60
            if matches < 2 or coverage < min_cov or q_cov < 0.50:
                return 0.0, {"reason":"below coverage", "cov":round(coverage,2), "q_cov":round(q_cov,2), "title_len":n_title}, False

            # soft score (for tie-breaks)
            score = 1.2 * matches
            if q_forms:
                fh = len(q_forms & p_forms)
                score += 1.5*fh if fh else -0.8
            slug_hits = sum(1 for tok in q_toks if tok and tok in slug.upper())
            if slug_hits >= 2: score += 0.6
            return score, {"title": title, "taxonomy": taxo, "cov": coverage}, True

        def choose_best(cands: List[str], q_norm: str) -> Optional[str]:
            ranked=[]
            for u in cands[:10]:
                sc, meta, ok = fetch_and_verify(u, q_norm)
                if ok: ranked.append((sc,u,meta))
                elif self.debug: log(f"[ethical][debug] reject: {u} :: {meta.get('reason','')}")
            ranked.sort(key=lambda x: x[0], reverse=True)
            if self.debug:
                log(f"[ethical][debug] cand-ranking for q='{q_norm}':")
                for sc,u,meta in ranked[:5]:
                    log(f"[ethical][debug]  - score={sc:.2f} cov={meta.get('cov',0):.2f} title='{meta.get('title','')}' url={u}")
            if not ranked: return None
            best_sc,best_url,_ = ranked[0]
            self._last_product_url = best_url
            log(f"[ethical] match via name: q='{q_norm}' -> {best_url} (score={best_sc:.2f})")
            return best_url

        # UPC one-shot
        upc_digits = re.sub(r"\D","", upc or "")
        if upc_digits:
            for q in (upc_digits, f"%2B{upc_digits}"):
                cands = search_site(q)
                hit = choose_best(cands, q)
                if hit: return hit

        # description_1 first
        if desc:
            q_norm = _normalize_name(desc)
            cands = search_site(_WS.sub("+", q_norm))
            hit = choose_best(cands, q_norm)
            if hit: return hit

        # upcitemdb_title next
        if traw:
            q_norm = _normalize_name(traw)
            cands = search_site(_WS.sub("+", q_norm))
            hit = choose_best(cands, q_norm)
            if hit: return hit

        return None

    # ---------------- PDP helpers (static HTML) ----------------
    def _pdp_title(self, html: str) -> str:
        for patt in (
            r'<div[^>]+class="summary[^"]*"[^>]*>.*?<h4[^>]*>(.*?)</h4>',
            r'<h1[^>]*class="product_title[^"]*"[^>]*>(.*?)</h1>',
            r'<h1[^>]*class="entry-title[^"]*"[^>]*>(.*?)</h1>',
        ):
            m = re.search(patt, html, re.I|re.S)
            if m: return _spacify(_strip_html(m.group(1)))
        m = re.search(r'<meta[^>]+itemprop="name"[^>]+content="([^"]+)"', html, re.I)
        if m: return m.group(1).strip()
        m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
        return m.group(1).strip() if m else ""

    def _pdp_description(self, html: str) -> str:
        for patt in (
            r'<div[^>]+class="woocommerce-product-details__short-description"[^>]*>(.*?)</div>',
            r'<div[^>]+class="description"[^>]*>.*?<p[^>]*>(.*?)</p>',
        ):
            m = re.search(patt, html, re.I|re.S)
            if m: return _spacify(_strip_html(m.group(1)))
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, re.I)
        return m.group(1).strip() if m else ""

    def _pdp_hires_map(self, soup: BeautifulSoup) -> Dict[str,str]:
        out={}
        for a in soup.select(".hires a[href]"):
            href=_strip_query(a.get("href") or "")
            if not href: continue
            name = href.rsplit("/",1)[-1]
            stem,ext = self._split_name_ext(name)
            stem_root = self._root_stem(stem)
            out[stem_root]=href
        return out
    @staticmethod
    def _split_name_ext(name: str) -> Tuple[str,str]:
        i=name.rfind(".")
        return (name, "") if i==-1 else (name[:i], name[i:])
    @staticmethod
    def _root_stem(stem: str) -> str:
        s = _SIZE_SUFFIX.sub("", stem)
        s = re.sub(r"-scaled$", "", s, flags=re.I)
        return s
    def _upsize_wp(self, url: str, hires_map: Dict[str,str]) -> str:
        u=_strip_query(url)
        name = u.rsplit("/",1)[-1]
        stem,ext = self._split_name_ext(name)
        stem_root = self._root_stem(stem)
        hi = hires_map.get(stem_root)
        if hi: return _abs(self.origin, hi)
        new_name = self._root_stem(stem) + ext
        if new_name != name:
            return u.rsplit("/",1)[0] + "/" + new_name
        return u

    # ---------------- Selenium (optional last resort) ----------------
    def _make_driver(self):
        if not SELENIUM_AVAILABLE: raise RuntimeError("Selenium not available.")
        if self.sel_browser != "chrome": raise RuntimeError(f"Only 'chrome' supported (got '{self.sel_browser}').")
        opts = ChromeOptions()
        if self.sel_headless: opts.add_argument("--headless=new")
        for arg in self.sel_extra_args: opts.add_argument(arg)
        if self.sel_lang:
            opts.add_argument(f"--lang={self.sel_lang.split(',')[0]}")
            opts.add_experimental_option("prefs", {"intl.accept_languages": self.sel_lang})
        if self.ua: opts.add_argument(f"--user-agent={self.ua}")
        if self.sel_binary_path: opts.binary_location = self.sel_binary_path
        service = ChromeService(executable_path=self.sel_driver_path) if self.sel_driver_path else ChromeService()
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(self.sel_page_load_timeout)
        if self.sel_implicit_wait>0: driver.implicitly_wait(self.sel_implicit_wait)
        return driver
    def _dismiss_cookie_banner(self, driver):
        for sel in ["button#cn-accept-cookie","button[aria-label*='Accept']", ".cky-btn-accept", ".cm-btn_accept"]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    driver.execute_script("arguments[0].click();", els[0]); time.sleep(0.1); return
            except Exception: pass
    def _selenium_extract(self, url: str) -> Tuple[str,str,List[str]]:
        if not (self.sel_enabled and self.use_selenium and SELENIUM_AVAILABLE): return "", "", []
        title, desc_html, imgs = "", "", []
        driver=None
        try:
            driver = self._make_driver()
            driver.get(url)
            WebDriverWait(driver, self.sel_wait_selector_timeout).until(EC.presence_of_element_located((By.TAG_NAME,"body")))
            self._dismiss_cookie_banner(driver)

            for sel in ["div.summary h4","h1.product_title","h1.entry-title"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    title = el.text.strip()
                    if title: break
                except Exception: pass

            for sel in self.desc_selectors:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    desc_html = (el.get_attribute("innerHTML") or el.text or "").strip()
                    if desc_html: break
                except Exception: pass

            try:
                cont = driver.find_element(By.CSS_SELECTOR, "div.elastislide-carousel")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cont)
                time.sleep(0.25)
            except Exception: pass

            thumbs = driver.find_elements(By.CSS_SELECTOR, self.carousel_selector)
            if not thumbs:
                for alt in self.carousel_alternates:
                    thumbs = driver.find_elements(By.CSS_SELECTOR, alt)
                    if thumbs: break
            for t in thumbs:
                big = t.get_attribute("data-largeimg")
                if big: imgs.append(_strip_query(_abs(self.origin, big.strip())))
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
        return title, desc_html, _unique(imgs)

    # ---------------- parse_page (static-first; Selenium fallback) ----------------
    def parse_page(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html or "", "html.parser")

        title = self._pdp_title(html)
        desc  = self._pdp_description(html)

        hires_map = self._pdp_hires_map(soup)
        images: List[str] = []

        # Elastislide first
        if soup.select_one("div.elastislide-carousel"):
            for im in soup.select(self.carousel_selector):
                u = im.get("data-largeimg")
                if u: images.append(_strip_query(_abs(self.origin, u.strip())))
            if not images:
                for alt in self.carousel_alternates:
                    for im in soup.select(alt):
                        u = im.get("data-largeimg")
                        if u: images.append(_strip_query(_abs(self.origin, u.strip())))
        # Fallbacks
        if not images:
            for im in soup.select(".image-preload img[src]"):
                images.append(_strip_query(_abs(self.origin, im.get("src","").strip())))
        if not images:
            h = soup.select_one(".photos .demowrap img[src]")
            if h and h.get("src"): images.append(_strip_query(_abs(self.origin, h.get("src").strip())))
        if not images:
            for a in soup.select(".woocommerce-product-gallery__image a[href]"):
                images.append(_strip_query(_abs(self.origin, a.get("href","").strip())))
            for im in soup.select(".woocommerce-product-gallery__image img[src]"):
                images.append(_strip_query(_abs(self.origin, im.get("src","").strip())))
        if not images:
            og = soup.find("meta", property="og:image")
            if og and og.get("content"): images.append(_strip_query(_abs(self.origin, og.get("content").strip())))
        if not images:
            m = re.search(r"bigImageSrc\s*:\s*[\'\"]([^\'\"]+)", html, re.I)
            if m: images.append(_strip_query(_abs(self.origin, m.group(1).strip())))

        # Max-size normalization
        images = _unique([self._upsize_wp(u, hires_map) for u in images])

        # Selenium as last resort
        if (not images or not title or not desc) and self.use_selenium and self.sel_enabled and self._last_product_url:
            st_title, st_desc_html, st_imgs = self._selenium_extract(self._last_product_url)
            if st_title and not title: title = st_title
            if st_desc_html and not desc: desc = _plain(st_desc_html)
            if st_imgs and not images:
                images = _unique([self._upsize_wp(u, hires_map) for u in st_imgs])

        gallery_summary = f"found {len(images)} images" + (f"; first={images[0]}" if images else "")
        return {
            "title": title or "",
            "brand_hint": "Ethical Products",
            "description": desc or "",
            "gallery_images": images,
            "gallery_summary": gallery_summary,
            "log_lines": [f"[ethical] Gallery: {gallery_summary}"],
            "manufacturer": {
                "site_key": SITE_KEY,
                "brand": "Ethical Products",
                "name": title or "",
                "product_name": title or "",
                "description": desc or "",
                "images": images,
                "product_url": self._last_product_url or "",
                "_gallery_summary": gallery_summary,
                "_selenium_headless": getattr(self, "sel_headless", True),
            },
        }

# ---------------- helpers ----------------
def _strip_html(s: str) -> str:
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return _html.unescape(s).strip()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Ethical Products (SPOT) Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
