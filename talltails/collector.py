#!/usr/bin/env python3
"""Tall Tails Dog Product Collector"""

import json

# Site Configuration (embedded from profile)
SITE_CONFIG = {
    "site_key": "talltailsdog",
    "origin": "https://www.talltailsdog.com",
    "referer": "https://www.talltailsdog.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "search": {
        "type": "onsite",
        "endpoint": "/catalogsearch/result/?q={query}",
        "method": "GET",
        "qparam": "q",
        "expects_html_grid": true
    },
    "catalog_required": false,
    "selectors": {
        "title": "h1",
        "feature_bullets": ".product-info-main ul li",
        "description_root": ".product.attribute.description .value",
        "materials_root": "[id*='materials'] .value, .product.attribute .value",
        "gallery_hint": "mage/gallery/gallery"
    },
    "notes": [
        "Magento/Adobe Commerce site.",
        "Benefits are bullets-only \u2192 store as benefits_text[].description (empty title) in enrichment.",
        "Materials (if present) should map to ingredients_text at merge stage.",
        "Gallery is read from mage/gallery/gallery JSON (full image set; videos available if needed).",
        "Search uses /catalogsearch/result/?q={query} with UPC first; name fallbacks handled by orchestrator."
    ]
}

# strategies/talltailsdog.py
# Tall Tails (talltailsdog.com) — site-specific strategy
#
# What this version does:
#   • Robust onsite search (host forcing, URL-encoded q, grid-scoped results, learning: auto-disable UPC after 5 misses)
#   • **Variant/child mapping (gallery-only)**:
#       - Parse Magento swatch-renderer (text/x-magento-init) to build:
#           • child -> labels (e.g., Style: Highland Cow / Gorilla / Grizzly / Yeti / Black Bear)
#           • child -> gallery media (from mediaGallery or jsonConfig.images)
#           • style optionId -> children & label
#       - Choose the correct **style** by fuzzy-matching the visible swatch labels against the record’s name
#       - Pick the corresponding **child** and return **only that child’s gallery** (images/videos)
#       - If product has no variants (or no child media found), fall back to the single **Fotorama gallery** (still gallery-only)
#   • **Descriptions are plain text only** (human readable; easy to convert to Shopify-limited HTML later)
#   • **Materials/Care**: extract from Materials tab:
#       model_product["ingredients_text"]      <- paragraph under “Material:”
#       model_product["directions_for_use"]    <- paragraph under “Care:”
#   • **Verbose logs** across discovery and parsing (search URLs, grid counts, chosen style/child, gallery path, image/video counts)
#
from __future__ import annotations

import json
import re
from typing import List, Tuple, Dict, Optional, Any, Set
from urllib.parse import urlsplit, urlunsplit, quote_plus

try:
    # CollectionApp base base
    from .base import SiteStrategy
except Exception:
    class SiteStrategy:  # type: ignore
        def __init__(self, profile: dict | None = None) -> None:
            self.profile = profile or {}

from bs4 import BeautifulSoup


# -----------------------------
# URL / text helpers
# -----------------------------
def _https_no_query(u: str) -> str:
    """Force https and strip query/fragment."""
    try:
        p = list(urlsplit(u))
        p[0] = "https"
        p[3] = ""
        p[4] = ""
        return urlunsplit(p)
    except Exception:
        return u

def _force_host(url: str, preferred_host: str) -> str:
    """Force preferred host (e.g., 'www.talltailsdog.com')."""
    try:
        p = list(urlsplit(url if url.startswith("http") else "https://" + url))
        if preferred_host:
            p[1] = preferred_host
        if not p[0]:
            p[0] = "https"
        return urlunsplit(p)
    except Exception:
        return url

def _collapse_ws(s: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", (s or "")).strip()

def _norm_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


# -----------------------------
# Plain-text description only
# -----------------------------
def _to_plain_text(html: str) -> str:
    """
    Convert arbitrary PDP HTML to plain text only, human-readable:
      • Paragraphs → lines with single blank line between paragraphs.
      • <li> → lines starting with "- ".
      • All tags removed.
    """
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for li in soup.find_all("li"):
        li.insert_before(soup.new_string("\n- "))
    for br in soup.find_all("br"):
        br.replace_with("\n")
    raw = soup.get_text("\n")
    lines = [l.rstrip() for l in raw.splitlines()]
    out: List[str] = []
    blank = False
    for l in lines:
        if l.strip():
            out.append(l)
            blank = False
        else:
            if not blank:
                out.append("")
                blank = True
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


# -----------------------------
# Magento gallery JSON (canonical gallery source)
# -----------------------------
def _extract_gallery_mage_json(html: str) -> List[Dict]:
    """
    Pull the Magento gallery “data” list if present. This is the canonical source of
    what Fotorama should render. If absent, we’ll parse the Fotorama container as a single-variant fallback.
    """
    # 1) <script data-gallery-role="gallery">...</script>
    m = re.search(r'<script[^>]*data-gallery-role="gallery"[^>]*>(.*?)</script>',
                  html, re.I | re.DOTALL)
    if m:
        try:
            blob = (m.group(1) or "").strip()
            j = json.loads(blob)
            if isinstance(j, list):
                return j
            if isinstance(j, dict) and isinstance(j.get("data"), list):
                return j["data"]
        except Exception:
            pass

    # 2) <script type="text/x-magento-init"> ... "mage/gallery/gallery": {data:[...]} ...
    for mm in re.finditer(r'<script[^>]*type="text/x-magento-init"[^>]*>(.*?)</script>',
                          html, re.I | re.DOTALL):
        blob = (mm.group(1) or "").strip()
        try:
            root = json.loads(blob)
        except Exception:
            continue

        def _find_gallery(node: Any):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "mage/gallery/gallery" and isinstance(v, dict) and isinstance(v.get("data"), list):
                        return v["data"]
                    found = _find_gallery(v)
                    if found is not None:
                        return found
            elif isinstance(node, list):
                for v in node:
                    found = _find_gallery(v)
                    if found is not None:
                        return found
            return None

        data = _find_gallery(root)
        if isinstance(data, list):
            return data

    # 3) Regex fallback
    m2 = re.search(r'"mage/gallery/gallery"\s*:\s*({.*?})\s*[},]', html, re.DOTALL)
    if m2:
        try:
            j = json.loads(m2.group(1))
            if isinstance(j, dict) and isinstance(j.get("data"), list):
                return j["data"]
        except Exception:
            pass

    return []


def _gallery_from_items(items: List[Dict]) -> Tuple[List[str], List[Dict]]:
    """
    Convert Magento gallery items list to (images, videos-from-gallery).
    Videos are objects with {"thumbnail": ..., "url": ...}.
    """
    images: List[str] = []
    videos: List[Dict] = []
    for it in items or []:
        # Items may include keys: img, thumb, full, mediaType/type, videoUrl/url, poster, etc.
        mtype = (it.get("mediaType") or it.get("type") or "").lower()
        if mtype == "image" or (not mtype and ("img" in (it.get("thumb", "") + it.get("img", "")).lower())):
            src = it.get("full") or it.get("img") or it.get("thumb") or ""
            if src:
                images.append(_https_no_query(src))
        elif "video" in mtype or it.get("videoUrl"):
            url = it.get("videoUrl") or it.get("url") or ""
            thumb = it.get("thumb") or it.get("poster") or it.get("img") or ""
            if url:
                videos.append({
                    "thumbnail": _https_no_query(thumb) if thumb else "",
                    "url": _https_no_query(url)
                })
    # dedupe keep order
    seen = set()
    out = []
    for u in images:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out, videos


# -----------------------------
# Fotorama gallery DOM parsing (gallery-only; single-variant fallback)
# -----------------------------
def _gallery_from_fotorama_dom(html: str) -> Tuple[List[str], List[Dict]]:
    """
    Parse the Fotorama gallery container only and return (images, videos).
    We DO NOT include anything outside the gallery container.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one('[data-gallery-role="gallery"]')
    if not container:
        return [], []

    images: List[str] = []
    videos: List[Dict] = []

    # Stage frames
    for frame in container.select('.fotorama__stage__frame'):
        img = frame.find('img', class_=re.compile(r'\bfotorama__img\b'))
        if img and img.get("src"):
            images.append(_https_no_query(img.get("src")))
        pv = frame.find('div', class_=re.compile(r'\bproduct-video\b'))
        if pv:
            vtype = (pv.get("data-type") or "").lower()
            code = pv.get("data-code") or ""
            thumb = _https_no_query(img.get("src")) if img and img.get("src") else ""
            if vtype == "youtube" and code:
                url = f"https://www.youtube.com/watch?v={code}"
                videos.append({"thumbnail": thumb, "url": url})

    # Thumbs (ensure we include thumbs that didn’t render in stage yet)
    for nav_img in container.select('.fotorama__nav__frame img'):
        src = nav_img.get("src") or ""
        if src:
            images.append(_https_no_query(src))

    # dedupe
    seen = set(); out = []
    for u in images:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out, videos


# -----------------------------
# Swatch/Configurator extraction (Magento)
# -----------------------------
def _extract_swatch_renderer(html: str) -> Dict[str, Any]:
    """
    Parse Magento swatch renderer config + visible swatch labels.
    Returns:
      {
        "product_labels": {child_id: [labels...]},
        "product_media":  {child_id: [gallery_items...]},  # mediaGallery or jsonConfig.images
        "style_opt_to_children": {option_id: [child_ids...]},
        "style_opt_label": {option_id: "Label"},
        "style_labels_dom": ["Yeti", "Gorilla", ...]
      }
    """
    out: Dict[str, Any] = {
        "product_labels": {},
        "product_media": {},
        "style_opt_to_children": {},
        "style_opt_label": {},
        "style_labels_dom": [],
    }

    # Visible labels from DOM (works even if JSON differs slightly)
    soup = BeautifulSoup(html, "html.parser")
    dom_labels: List[str] = []
    for el in soup.select('div.swatch-attribute.style .swatch-option'):
        lab = (el.get("data-option-label") or el.get_text(" ", strip=True) or "").strip()
        if lab:
            dom_labels.append(lab)
    out["style_labels_dom"] = list(dict.fromkeys(dom_labels))

    # text/x-magento-init JSON
    for mm in re.finditer(r'<script[^>]*type="text/x-magento-init"[^>]*>(.*?)</script>',
                          html, re.I | re.DOTALL):
        blob = (mm.group(1) or "").strip()
        try:
            root = json.loads(blob)
        except Exception:
            continue

        def _walk(node: Any):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "Magento_Swatches/js/swatch-renderer" and isinstance(v, dict):
                        json_cfg = v.get("jsonConfig") or {}
                        attributes = json_cfg.get("attributes") or {}
                        index = json_cfg.get("index") or {}
                        media_gallery = v.get("mediaGallery") or v.get("gallery") or {}
                        images_by_child = json_cfg.get("images") or {}

                        # Identify "style" attribute
                        style_attr_id = None
                        for aid, meta in attributes.items():
                            if (meta.get("code") or "").lower() == "style":
                                style_attr_id = str(aid)
                                break

                        # Build option label map
                        opt_label: Dict[str, Dict[str, str]] = {}
                        for aid, meta in attributes.items():
                            mp = {}
                            for opt in meta.get("options", []):
                                mp[str(opt.get("id"))] = str(opt.get("label") or "")
                            opt_label[str(aid)] = mp

                        # child -> labels from index
                        prod_labels: Dict[str, List[str]] = {}
                        if isinstance(index, dict):
                            for child_id, combo in index.items():
                                labs: List[str] = []
                                if isinstance(combo, dict):
                                    for aid, oid in combo.items():
                                        lab = opt_label.get(str(aid), {}).get(str(oid))
                                        if lab:
                                            labs.append(lab)
                                if labs:
                                    prod_labels[str(child_id)] = labs

                        # attributes[].options[].products add labels + style mapping
                        for aid, meta in attributes.items():
                            for opt in meta.get("options", []):
                                oid = str(opt.get("id"))
                                lab = str(opt.get("label") or "")
                                for child in (opt.get("products") or []):
                                    cid = str(child)
                                    prod_labels.setdefault(cid, [])
                                    if lab and lab not in prod_labels[cid]:
                                        prod_labels[cid].append(lab)
                                if style_attr_id and str(aid) == style_attr_id:
                                    out["style_opt_to_children"].setdefault(oid, [])
                                    for child in (opt.get("products") or []):
                                        cid = str(child)
                                        if cid not in out["style_opt_to_children"][oid]:
                                            out["style_opt_to_children"][oid].append(cid)
                                    out["style_opt_label"][oid] = lab

                        # media maps
                        if isinstance(media_gallery, dict):
                            for cid, items in media_gallery.items():
                                if isinstance(items, list) and items:
                                    out["product_media"][str(cid)] = items
                        if isinstance(images_by_child, dict):
                            for cid, items in images_by_child.items():
                                if isinstance(items, list) and items:
                                    out["product_media"].setdefault(str(cid), items)

                        # merge labels
                        for cid, labs in prod_labels.items():
                            out["product_labels"].setdefault(cid, [])
                            for lab in labs:
                                if lab not in out["product_labels"][cid]:
                                    out["product_labels"][cid].append(lab)

                    _walk(v)
            elif isinstance(node, list):
                for v in node:
                    _walk(v)
        _walk(root)

    return out


# -----------------------------
# Variant label / child selection
# -----------------------------
def _fuzzy_style_from_name(style_labels: List[str], reference_text: str, tokens: Set[str]) -> Tuple[Optional[str], float]:
    """
    Choose the best visible style label by fuzzy overlap with the product name we searched.
    Returns (best_label, best_score).
    """
    if not style_labels:
        return (None, -1.0)
    ref = (reference_text or "").lower()
    ref = ref.replace("×", "x")
    ref = re.sub(r"[^a-z0-9\s-]", " ", ref)
    ref = re.sub(r"\s+", " ", ref)
    tokset = set(re.findall(r"[a-z0-9]+", ref)) | set(tokens or [])
    best = (None, -1.0)
    for lab in style_labels:
        l = (lab or "").lower().strip()
        l = l.replace("blackbear", "black bear")
        l = re.sub(r"\bgrizzle\b", "grizzly", l)
        score = 0.0
        if l in ref:
            score = 100.0
        else:
            ltoks = set(re.findall(r"[a-z0-9]+", l))
            score = float(len(ltoks & tokset)) + (0.1 if any(t in ref for t in ltoks) else 0.0)
        if score > best[1]:
            best = (lab, score)
    return best


def _best_style_option(style_opt_label: Dict[str, str], chosen_label: Optional[str]) -> Optional[str]:
    """Map chosen visible label → swatch optionId (case-insensitive)."""
    if not chosen_label or not style_opt_label:
        return None
    cl = chosen_label.lower().replace("blackbear", "black bear")
    cl = re.sub(r"\bgrizzle\b", "grizzly", cl)
    best_oid, best_score = None, -1
    for oid, lab in style_opt_label.items():
        lab_l = (lab or "").lower()
        if lab_l == cl:
            return oid
        sc = 0
        if lab_l in cl or cl in lab_l:
            sc = 80
        else:
            sc = len(_norm_tokens(lab_l) & _norm_tokens(cl))
        if sc > best_score:
            best_oid, best_score = oid, sc
    return best_oid


def _select_variant_child(product_labels: Dict[str, List[str]], chosen_label: Optional[str], tokens: Set[str]) -> Optional[str]:
    """Choose child by exact label first, else by label-token overlap."""
    if not product_labels:
        return None
    if chosen_label:
        cl = chosen_label.lower()
        for cid, labs in product_labels.items():
            for l in labs or []:
                if (l or "").lower() == cl:
                    return cid
    best_id, best_score = None, -1
    tok_norm = _norm_tokens((chosen_label or "") + " " + " ".join(tokens or []))
    for cid, labs in product_labels.items():
        ltok = _norm_tokens(" ".join(labs or []))
        sc = len(ltok & tok_norm)
        if sc > best_score:
            best_id, best_score = cid, sc
    return best_id


# -----------------------------
# Materials / Care extraction
# -----------------------------
def _extract_materials_and_care(html: str) -> Tuple[str, str]:
    """
    From the Materials tab content:
      <h3><b>Material:</b></h3><p>...</p>
      <h3><b>Care:</b></h3><p>...</p>
    Return (ingredients_text, directions_for_use) as plain text lines.
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one('#materials')
    if not root:
        return "", ""

    def _after_h3_with_text(htext: str) -> str:
        for h3 in root.find_all('h3'):
            t = h3.get_text(" ", strip=True).lower()
            if htext.lower() in t:
                p = h3.find_next_sibling('p')
                while p and not p.get_text(strip=True):
                    p = p.find_next_sibling('p')
                if p:
                    return _collapse_ws(p.get_text(" ", strip=True))
        return ""

    materials = _after_h3_with_text("material")
    care = _after_h3_with_text("care")
    return materials, care


# -----------------------------
# Strategy (site-specific)
# -----------------------------
class TalltailsdogStrategy(SiteStrategy):
    def __init__(self, profile: dict | None = None) -> None:
        super().__init__(profile or {})
        _origin = (self.profile.get("origin") or "https://www.talltailsdog.com").rstrip("/")
        self.origin = _origin
        self.preferred_host = urlsplit(_origin if _origin.startswith("http") else "https://" + _origin).netloc or "www.talltailsdog.com"
        self.search_endpoint: str = ((self.profile.get("search") or {}).get("endpoint") or "/catalogsearch/result/?q={query}")

        learning = (self.profile.get("learning") or {}) if isinstance(self.profile, dict) else {}
        self._UPC_DISABLE_THRESHOLD: int = int(learning.get("upc_disable_after", 5))
        self._upc_fail_count: int = 0
        self._upc_disabled: bool = False

        # verbose logs default ON unless profile["debug"] is explicitly False
        self._debug: bool = bool(self.profile.get("debug", True)) if isinstance(self.profile, dict) else True
        self._log = None  # type: ignore[assignment]

        # carried across methods to drive fuzzy label selection if needed
        self._variant_tokens: Set[str] = set()
        self._variant_query_text: str = ""

    # ---- BV no-op ----
    def bv_base_url(self) -> str: return ""
    def bv_common_params(self) -> dict: return {}

    # ---- Search helpers ----
    def _build_search_url(self, origin: str, raw_query: str) -> str:
        enc_q = quote_plus(raw_query or "")
        origin_fixed = _force_host(origin, self.preferred_host).rstrip("/")
        return f"{origin_fixed}{self.search_endpoint.format(query=enc_q)}"

    def _search_page(self, origin: str, query: str, http_get, timeout: int) -> str:
        url = self._build_search_url(origin, query)
        r = http_get(url, timeout=timeout)
        return r.text if getattr(r, "text", None) else ""

    @staticmethod
    def _score_title(name: str, query_text: str) -> float:
        if not query_text:
            return 0.0
        nt = _norm_tokens(name)
        qt = _norm_tokens(query_text)
        inter = len(nt & qt)
        penalty = 0.10 * max(0, len(nt) - inter)  # prefer tighter titles
        return inter - penalty

    def _first_pdp_from_search(self, html: str, query_text: str = "", log=None) -> Optional[str]:
        """Read the Magento search grid ONLY; ignore header/footer links (e.g., /blog.html)."""
        s = BeautifulSoup(html, "html.parser")
        grid = s.select_one("div.products.wrapper.grid.products-grid ol.products.list.items.product-items")
        if not grid:
            if log: log("[talltailsdog] Search grid not found; trying alternates…")
            grid = (s.select_one("ol.products.list.items.product-items")
                    or s.select_one("ol.products.products.list.items")
                    or s.select_one("div.search.results ol.products.list.items.product-items"))
        if not grid:
            if log: log("[talltailsdog] No product grid on search results.")
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
            if any(bad in href for bad in ("/blog", "/catalogsearch", "/customer", "/account", "/cart", "/privacy", "/terms")):
                continue
            candidates.append((href, name))

        if log: log(f"[talltailsdog] Search grid candidates: {len(candidates)}")
        if not candidates:
            return None

        if query_text:
            candidates.sort(key=lambda t: self._score_title(t[1], query_text), reverse=True)
            if log:
                top = candidates[0]
                log(f"[talltailsdog] Top tile by title score → name='{top[1]}' url={top[0]}")
        return candidates[0][0]

    # --- Query normalization / variants (for searching, not for gallery scraping) ---
    @staticmethod
    def _normalize_variants(base: str) -> List[str]:
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
                variants.update({
                    size_pat.sub(f"{a}x{b}", t),
                    size_pat.sub(f"{a} x {b}", t),
                    size_pat.sub(f"{a}×{b}", t),
                    size_pat.sub(f"{a}/{b}", t),
                })
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

    @staticmethod
    def _derive_variant_tokens(product_data: Optional[dict]) -> Set[str]:
        fields = []
        if isinstance(product_data, dict):
            for k in ("upcitemdb_title", "description_1", "description_2", "title", "name"):
                v = product_data.get(k)
                if isinstance(v, str):
                    fields.append(v)
        text = " ".join(fields)
        toks = _norm_tokens(text)
        # helpful fused labels
        def add_if(words: List[str], label: str):
            if all(w in toks for w in words):
                toks.update(_norm_tokens(label))
                toks.add(label.replace(" ", "_"))
                toks.add(label.replace(" ", ""))
        add_if(["cow"], "highland cow")
        add_if(["black", "bear"], "black bear")
        add_if(["cow", "print"], "cow print")
        return toks

    # ---- Discovery (with learning & verbose logs) ----
    def find_product_page_url_for_upc(
        self, upc: str, http_get, timeout: int, log, product_data: dict | None = None, **kwargs
    ) -> Optional[str]:
        self._log = log  # remember logger for parse_page
        if not upc:
            return None

        # row-specific origin (if present)
        origin = self.origin
        try:
            if isinstance(product_data, dict):
                home = (product_data.get("manufacturer_homepage_found")
                        or product_data.get("manufacturer_homepage") or "").strip()
                if home:
                    origin = home
        except Exception:
            pass
        origin = _force_host(origin, self.preferred_host).rstrip("/")

        # variant tokens & reference string (for label fuzzy matching if needed)
        self._variant_tokens = self._derive_variant_tokens(product_data)
        self._variant_query_text = (product_data or {}).get("description_1") or (product_data or {}).get("upcitemdb_title") or ""

        def is_pdp(ht: str) -> bool:
            return (
                'class="product-info-main"' in (ht or "")
                or 'data-gallery-role="gallery"' in (ht or "")
                or '"@type":"Product"' in (ht or "") or "'@type':'Product'" in (ht or "")
            )

        # 1) UPC search (disable after threshold)
        ran_upc = False
        if self._upc_disabled:
            if self._debug and log: log(f"[talltailsdog] Skipping UPC search (disabled after {self._upc_fail_count} misses; threshold={self._UPC_DISABLE_THRESHOLD}).")
        else:
            ran_upc = True
            try:
                search_url = self._build_search_url(origin, upc)
                if self._debug and log: log(f"[talltailsdog] UPC search URL: {search_url}")
                r = http_get(search_url, timeout=timeout)
                srch_html = getattr(r, "text", "") or ""
                cand = self._first_pdp_from_search(srch_html, query_text=self._variant_query_text, log=log if self._debug else None)
                if cand:
                    if self._debug and log: log(f"[talltailsdog] Candidate PDP from UPC search: {cand} — validating…")
                    pr = http_get(cand, timeout=timeout)
                    cand_html = getattr(pr, "text", "") or ""
                    if is_pdp(cand_html):
                        if self._debug and log: log(f"[talltailsdog] ✔ Valid PDP (UPC): {cand} — resetting UPC fail counter.")
                        self._upc_fail_count = 0
                        self._variant_query_text = upc
                        return cand
                    else:
                        self._upc_fail_count += 1
                else:
                    self._upc_fail_count += 1

                if not self._upc_disabled and self._upc_fail_count >= self._UPC_DISABLE_THRESHOLD:
                    self._upc_disabled = True
                    if self._debug and log: log(f"[talltailsdog] ⚠ Disabling UPC search (consecutive misses={self._upc_fail_count}).")
            except Exception as e:
                if self._debug and log: log(f"[talltailsdog] UPC search error: {e}")
                self._upc_fail_count += 1
                if not self._upc_disabled and self._upc_fail_count >= self._UPC_DISABLE_THRESHOLD:
                    self._upc_disabled = True
                    if self._debug and log: log(f"[talltailsdog] ⚠ Disabling UPC search after error (misses={self._upc_fail_count}).")

        # 2) Name search (upcitemdb_title then description_1)
        for key in ("upcitemdb_title", "description_1"):
            q_base = (product_data or {}).get(key, "") or ""
            if not q_base:
                continue
            variants = self._normalize_variants(q_base)
            if self._debug and log:
                prefix = "Fallback" if ran_upc or self._upc_disabled else "Primary name search"
                log(f"[talltailsdog] {prefix} by {key}: generated {len(variants)} variants.")
            for qi, q in enumerate(variants, 1):
                try:
                    search_url = self._build_search_url(origin, q)
                    if self._debug and log: log(f"[talltailsdog]  • Variant {qi}/{len(variants)}: {search_url}")
                    r = http_get(search_url, timeout=timeout)
                    srch_html = getattr(r, "text", "") or ""
                    cand = self._first_pdp_from_search(srch_html, query_text=q, log=log if self._debug else None)
                    if not cand:
                        continue
                    if self._debug and log: log(f"[talltailsdog]    ↳ Candidate: {cand} — validating…")
                    pr = http_get(cand, timeout=timeout)
                    cand_html = getattr(pr, "text", "") or ""
                    if is_pdp(cand_html):
                        if self._debug and log: log(f"[talltailsdog] ✔ Valid PDP ({key} variant): {cand}")
                        self._variant_query_text = q
                        return cand
                except Exception as e:
                    if self._debug and log: log(f"[talltailsdog] {key} variant search error: {e}")

        if self._debug and log: log(f"[talltailsdog] ❌ Exhausted all search methods for UPC {upc}.")
        return None

    # ---- Parser (variant/child mapping; gallery-only; videos; materials/care; verbose logs) ----
    def parse_page(self, html_text: str) -> dict:
        log = self._log if (self._debug and callable(self._log)) else None

        s = BeautifulSoup(html_text, "html.parser")

        # Title
        title_el = s.select_one("h1") or s.select_one("[data-product-title]")
        title = (title_el.get_text(" ", strip=True) if title_el else "").strip()
        if log: log(f"[talltailsdog] Title: {title!r}")

        # Description (plain text)
        desc_el = s.select_one(".product.attribute.description .value") or s.select_one(".product.attribute.description")
        description_html_raw = str(desc_el) if desc_el else ""
        description_text = _to_plain_text(description_html_raw)
        if log: log(f"[talltailsdog] Description chars: {len(description_text)}")

        # Benefits under .product-info-main
        bullets: List[str] = []
        for ul in s.select(".product-info-main ul"):
            for li in ul.select("li"):
                t = li.get_text(" ", strip=True)
                if t:
                    bullets.append(t)
        seen = set(); benefits = []
        for b in bullets:
            if b not in seen:
                seen.add(b)
                benefits.append({"title": "", "description": b})
        if log: log(f"[talltailsdog] Benefits bullets: {len(benefits)}")

        # Materials / Care
        ingredients_text, directions_for_use = _extract_materials_and_care(html_text)
        if log: log(f"[talltailsdog] Materials->ingredients_text len={len(ingredients_text)}, Care->directions len={len(directions_for_use)}")

        # Swatch/config extraction
        swatch = _extract_swatch_renderer(html_text)
        product_labels = swatch.get("product_labels") or {}
        product_media = swatch.get("product_media") or {}
        style_opt_to_children: Dict[str, List[str]] = swatch.get("style_opt_to_children") or {}
        style_opt_label: Dict[str, str] = swatch.get("style_opt_label") or {}
        style_labels_dom: List[str] = swatch.get("style_labels_dom") or []
        if log:
            log(f"[talltailsdog] Style labels (DOM): {style_labels_dom}")
            if style_opt_label:
                log(f"[talltailsdog] Style options (json): {[(oid, lab) for oid, lab in style_opt_label.items()]}")

        # Resolve best style label from record name/query
        chosen_label, chosen_score = _fuzzy_style_from_name(style_labels_dom, self._variant_query_text, self._variant_tokens)
        if log:
            log(f"[talltailsdog] Chosen style label: {chosen_label} (score={chosen_score}) from ref='{self._variant_query_text}'")

        # Resolve to child id via style option (preferred), else via labels overlap
        chosen_child: Optional[str] = None
        if chosen_label and style_opt_label and style_opt_to_children:
            best_oid = _best_style_option(style_opt_label, chosen_label)
            if log:
                log(f"[talltailsdog] Chosen option id from label: {best_oid} → children={style_opt_to_children.get(best_oid, [])}")
            if best_oid and style_opt_to_children.get(best_oid):
                chosen_child = style_opt_to_children[best_oid][0]

        if not chosen_child:
            chosen_child = _select_variant_child(product_labels, chosen_label, self._variant_tokens)
            if log:
                log(f"[talltailsdog] Chosen child by labels overlap: {chosen_child}")

        # Build gallery (gallery-only)
        images: List[str] = []
        videos: List[Dict] = []
        path_used = ""

        # A) If we have per-child media from swatch-renderer, use ONLY that child's media
        if chosen_child and product_media.get(str(chosen_child)):
            child_items = product_media[str(chosen_child)]
            images, videos = _gallery_from_items(child_items)
            path_used = "child_media"
        else:
            # B) No child media found (non-configurable / single variant):
            #    Use the single-variant gallery: Magento gallery JSON OR Fotorama DOM
            mg_items = _extract_gallery_mage_json(html_text)
            if mg_items:
                images, videos = _gallery_from_items(mg_items)
                path_used = "gallery_json"
            else:
                images, videos = _gallery_from_fotorama_dom(html_text)
                path_used = "fotorama_dom"

        # dedupe images
        seen_i = set(); images = [u for u in images if (u and not (u in seen_i or seen_i.add(u)))]
        # dedupe videos by (thumb,url)
        seen_v = set()
        vids_out = []
        for v in videos or []:
            key = (v.get("thumbnail",""), v.get("url",""))
            if v.get("url") and key not in seen_v:
                seen_v.add(key)
                vids_out.append(v)
        videos = vids_out

        if log:
            log(f"[talltailsdog] Gallery final: path='{path_used}' | label='{chosen_label}' | child='{chosen_child}' | images={len(images)} | videos={len(videos)}")

        # Final payload (plain-text description; gallery-only; include videos + materials/care under model_product)
        return {
            "model_product": {
                "ingredients_text": ingredients_text,
                "directions_for_use": directions_for_use,
                "gallery_videos": videos,  # gallery-only videos (if any)
            },
            "title": title or "",
            "brand_hint": "Tall Tails",
            "benefits": benefits,
            "description": description_text,   # plain text only
            "gallery_images": images,         # gallery-only images (variant-aware when applicable)
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tall Tails Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    args = parser.parse_args()
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
