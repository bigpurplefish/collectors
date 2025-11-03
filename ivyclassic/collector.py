#!/usr/bin/env python3
"""
Ivyclassic Product Collector

Collects product data from https://ivyclassic.com.
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
    "site_key": "ivyclassic",
    "origin": "https://ivyclassic.com",
    "referer": "https://ivyclassic.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "fetch_jitter_min_ms": 200,
    "fetch_jitter_max_ms": 700,
    "candidate_cap": 8,
    "hl": "en",
    "gl": "us",
    "bv_auth_required": false,
    "bv_base_url": "",
    "bv_common_params": {},
    "requires_catalog": true
}

# strategies/ivyclassic.py
from __future__ import annotations

import re
import json
from typing import Any, Dict, List, Optional, Callable
from bs4 import BeautifulSoup

from .base import SiteStrategy


class IvyclassicStrategy(SiteStrategy):
    """
    Ivy Classic (ivyclassic.com) scraper — uses ONLY a local JSON catalog of
    UPC → PDP URL mappings provided by the GUI (profile['catalog_json_file'] or 'product_catalog').
    No web search fallback. If profile["requires_catalog"] is true and no catalog path is
    provided, discovery is aborted.
    """

    # -------------- lifecycle / config --------------
    def __init__(self, profile: Optional[Dict[str, Any]] = None):
        self.profile: Dict[str, Any] = profile or {}
        self._session = None
        self._auth: Optional[Dict[str, Any]] = None

        self._origin: str = (self.profile.get("origin") or "https://ivyclassic.com").rstrip("/")
        self._referer: str = (self.profile.get("referer") or f"{self._origin}/").strip()
        self._ua: str = self.profile.get("user_agent") or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        )

        # --- Catalog support ---
        # Accept either profile['catalog_json_file'] or profile['product_catalog']
        self._catalog_path: str = (self.profile.get("catalog_json_file")
                                   or self.profile.get("product_catalog")
                                   or "").strip()
        self._catalog: Optional[Dict[str, str]] = None  # lazy-loaded

    # -------------- optional integration hooks --------------
    def attach_session(self, session) -> None:
        self._session = session

    def set_auth(self, auth: Dict[str, Any] | None) -> None:
        self._auth = auth or None

    def set_catalog_path(self, path: Optional[str]) -> None:
        """Optional hook for the GUI to override/attach the catalog path at runtime."""
        self._catalog_path = (path or "").strip()
        self._catalog = None  # force reload on next use

    # -------------- Bazaarvoice placeholders --------------
    def bv_base_url(self) -> str:
        return str(self.profile.get("bv_base_url") or "")

    def bv_common_params(self) -> Dict[str, Any]:
        params = self.profile.get("bv_common_params") or {}
        return dict(params)

    # -------------- UPC normalization --------------
    @staticmethod
    def _normalize_upc_variants(upc: str) -> List[str]:
        """
        Return a list of plausible key forms to try against the catalog.
        We keep only digits and try 12/13/14-digit padded/sliced + stripped.
        """
        try:
            upc_num = re.sub(r"[^0-9]", "", upc or "")
        except Exception:
            upc_num = str(upc or "")

        variants: List[str] = []
        if not upc_num:
            return variants

        L = len(upc_num)
        for target in (12, 13, 14):
            if L == target:
                variants.append(upc_num)
            elif L < target:
                variants.append(upc_num.zfill(target))
            else:
                variants.append(upc_num[-target:])

        stripped = upc_num.lstrip("0")
        if stripped:
            if stripped not in variants:
                variants.append(stripped)
            for target in (12, 13, 14):
                cand = stripped.zfill(target) if len(stripped) <= target else stripped[-target:]
                if cand not in variants:
                    variants.append(cand)

        if upc_num not in variants:
            variants.append(upc_num)

        # Deduplicate while preserving order
        seen = set()
        out: List[str] = []
        for v in variants:
            if v and v not in seen:
                out.append(v)
                seen.add(v)
        return out

    # -------------- Catalog support --------------
    def _ensure_catalog_loaded(self, log: Callable[[str], None]) -> None:
        """Load the JSON catalog one time (if a path is present)."""
        if self._catalog is not None:
            return
        self._catalog = {}
        if not self._catalog_path:
            log("[Ivy] No catalog_json_file path set on strategy.")
            return

        log(f"[Ivy] Loading catalog from: {self._catalog_path}")
        try:
            with open(self._catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Accept either a mapping {upc: url, ...} or an array of {upc, url}
            if isinstance(data, dict):
                for k, v in data.items():
                    if v and isinstance(v, str):
                        self._catalog[str(k).strip()] = v.strip()
            elif isinstance(data, list):
                for row in data:
                    if not isinstance(row, dict):
                        continue
                    k = str(row.get("upc") or "").strip()
                    v = str(row.get("url") or "").strip()
                    if k and v:
                        self._catalog[k] = v
            else:
                log(f"[Ivy] Catalog is neither object nor array; ignoring contents.")

            log(f"[Ivy] Catalog loaded with {len(self._catalog)} entries.")
        except FileNotFoundError:
            log(f"[Ivy] Catalog file not found: {self._catalog_path}")
        except Exception as e:
            log(f"[Ivy] Catalog load error ({self._catalog_path}): {e}")

    def _lookup_catalog(self, upc: str, log: Callable[[str], None]) -> Optional[str]:
        """Try to resolve UPC via the loaded catalog; returns URL or None."""
        self._ensure_catalog_loaded(log)
        if not self._catalog:
            return None
        variants = self._normalize_upc_variants(upc)
        for key in [upc] + variants:
            url = self._catalog.get(key)
            if url:
                return url
        return None

    # -------------- Public API: discovery --------------
    def find_product_page_url_for_upc(
        self,
        upc: str,
        http_get: Callable[..., Any],   # kept for interface compatibility; ignored here
        timeout: float,                 # kept for interface compatibility; ignored here
        log: Callable[[str], None],
    ) -> Optional[str]:
        """
        Discovery order:
          1) If profile requires a catalog, enforce presence of a catalog path.
          2) Try local UPC→PDP catalog (exact/normalized matches).
          3) If not found, return None (no search fallback).
        """
        if not upc:
            log("[Ivy] No UPC provided.")
            return None

        # Honor profile flag 'requires_catalog' (backward compatible: defaults False)
        requires_catalog = bool(self.profile.get("requires_catalog", False))
        if requires_catalog and not (self._catalog_path or "").strip():
            log("[Ivy] Catalog required by profile ('requires_catalog': true), but no path was provided.")
            return None

        catalog_url = self._lookup_catalog(upc, log)
        if catalog_url:
            log(f"[Ivy] Catalog hit for UPC {upc}: {catalog_url}")
            return catalog_url

        log(f"[Ivy] Catalog miss for UPC {upc}; no search fallback enabled.")
        return None

    # -------------- Parsing --------------
    @staticmethod
    def _clean_image_url(src: str, origin: str) -> str:
        if not src:
            return ""
        s = src.strip()
        if s.startswith("//"):
            s = "https:" + s
        elif s.startswith("/"):
            s = origin.rstrip("/") + s
        elif not s.startswith("http"):
            s = origin.rstrip("/") + "/" + s.lstrip("/")

        if "GetImage.ashx" in s and "image=" in s:
            image_qs = s.split("image=", 1)[1]
            image_path = image_qs.split("&", 1)[0] if "&" in s else image_qs
            image_path = image_path.replace("+", " ").replace(" ", "%20")
            if not image_path.startswith("http"):
                if not image_path.startswith("/"):
                    image_path = "/" + image_path
                s = origin.rstrip("/") + image_path
            else:
                s = image_path
        else:
            s = s.split("?", 1)[0].split("#", 1)[0]

        return s.replace("http://", "https://")

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        - Title: from on-page heading.
        - Benefits: ONLY from the Features tab bulleted list; each bullet goes to benefits[i]['description'] (empty title).
        - Description: leave empty unless you want another section mapped in the future.
        - Gallery images: keep existing heuristic.
        """
        soup = BeautifulSoup(html_text or "", "html.parser")

        # -------- Title --------
        h = soup.find(["h2", "h1"])
        title = (h.get_text(strip=True) if h else "") or ""

        # -------- Benefits from "Features" tab only --------
        features_container = None

        # Path A: find the Features tab button and follow its data-bs-target to the pane
        btn = None
        for b in soup.find_all("button"):
            txt = (b.get_text() or "").strip().lower()
            if txt == "features":
                btn = b
                break
        if btn:
            target = btn.get("data-bs-target") or ""
            if target.startswith("#"):
                pane = soup.select_one(target)
                if pane:
                    features_container = pane

        # Path B (fallback): match a common id pattern like item_swiftrizzo_tabs_<num>_1 (the "Features" pane)
        if not features_container:
            features_container = soup.find("div", id=re.compile(r"item_swiftrizzo_tabs_\d+_1"))

        # Extract list items within the features pane
        benefits: List[Dict[str, str]] = []
        if features_container:
            # Take the first obvious bullet list under the features pane
            ul = features_container.find("ul")
            if ul:
                for li in ul.find_all("li"):
                    text = li.get_text(separator=" ", strip=True)
                    if not text:
                        continue
                    # Keep only the clean bullets (skip obvious spec table rows that might leak in other layouts)
                    if re.search(r"^\s*(Product No\.|UPC Code|Box Qty|Case Qty|Weight)\b", text, re.I):
                        continue
                    benefits.append({"title": "", "description": text})

        # -------- Images (unchanged logic) --------
        gallery_images: List[str] = []
        for img in soup.find_all("img"):
            src = (img.get("src") or "").strip()
            if not src:
                continue
            alt = (img.get("alt") or "").strip().lower()
            if alt in {"in stock", "on backorder"}:
                continue
            w = img.get("width")
            if (isinstance(w, str) and w.isdigit() and int(w) <= 200) or (isinstance(w, int) and w <= 200):
                continue

            full = self._clean_image_url(src, self._origin)
            if not full:
                continue
            if ("Single%20Item%20Images" not in full) and ("Shared%20Images" not in full):
                continue
            if full not in gallery_images:
                gallery_images.append(full)

        return {
            "title": title,
            "description": "",
            "benefits": benefits,
            "gallery_images": gallery_images,
            "brand_hint": "Ivy Classic",
            "model_product": None,
        }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Ivyclassic Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
