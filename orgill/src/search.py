"""
Search functionality for Orgill collector.

Handles authenticated UPC-based product search.
"""

import re
import html
from typing import Tuple, Callable, Dict
import requests
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import normalize_upc


class OrgillSearcher:
    """Handles product search for Orgill."""

    def __init__(self, config: dict):
        """
        Initialize searcher.

        Args:
            config: Site configuration dict
        """
        self.origin = config.get("origin", "").rstrip("/")
        search_config = config.get("search", {})
        self.upc_overrides = search_config.get("upc_overrides", {})

    def _abs(self, path_or_url: str) -> str:
        """Convert relative path to absolute URL."""
        if not path_or_url:
            return ""
        if path_or_url.lower().startswith("http"):
            return path_or_url
        return f"{self.origin}/{path_or_url.lstrip('/')}"

    def _browser_headers(
        self,
        referer: str = None,
        origin: str = None,
    ) -> Dict[str, str]:
        """Build browser headers."""
        origin = (origin or self.origin).rstrip("/")
        referer = referer or origin or ""
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Upgrade-Insecure-Requests": "1",
            "Origin": origin,
        }

    def _parse_hidden_fields(self, html_text: str) -> Dict[str, str]:
        """Extract hidden form fields."""
        from bs4 import BeautifulSoup

        vals: Dict[str, str] = {}
        soup = BeautifulSoup(html_text or "", "html.parser")
        for el in soup.find_all("input", {"type": "hidden"}):
            name = el.get("name") or ""
            val = el.get("value") or ""
            if name:
                vals[name] = val

        # Ensure WebForms scaffolding
        for k in ("__EVENTTARGET", "__EVENTARGUMENT", "__LASTFOCUS"):
            vals.setdefault(k, "")

        return vals

    def _search_upc(
        self,
        upc: str,
        session: requests.Session,
        timeout: int,
        log: Callable[[str], None],
    ) -> Tuple[str, str]:
        """
        Perform an authenticated UPC search.

        Args:
            upc: UPC to search for
            session: Authenticated session
            timeout: Request timeout
            log: Logging function

        Returns:
            Tuple of (final_url, html_text)
        """
        home_url = self._abs("/Default.aspx")
        try:
            r = session.get(
                home_url,
                headers=self._browser_headers(referer=home_url, origin=self.origin),
                timeout=timeout,
            )
            if r.status_code != 200:
                return "", ""
            hidden = self._parse_hidden_fields(r.text)
        except Exception:
            return "", ""

        possible_fields = [
            {
                "__EVENTTARGET": "ctl00$lvwOrgill$ucPrivateHeader$btnFind",
                "ctl00$lvwOrgill$ucPrivateHeader$ddlSearchType": "Orgill",
                "txtAdvKeyword1": upc,
            },
            {
                "__EVENTTARGET": "lvwOrgill$ucPrivateHeader$btnFind",
                "lvwOrgill$ucPrivateHeader$ddlSearchType": "Orgill",
                "txtAdvKeyword1": upc,
            },
        ]

        hdrs_post = self._browser_headers(referer=home_url, origin=self.origin)
        hdrs_post["Content-Type"] = "application/x-www-form-urlencoded"

        for fields in possible_fields:
            payload = dict(hidden)
            payload["__EVENTTARGET"] = fields["__EVENTTARGET"]
            payload["__EVENTARGUMENT"] = payload.get("__EVENTARGUMENT", "")
            payload["__LASTFOCUS"] = payload.get("__LASTFOCUS", "")
            for k, v in fields.items():
                if not k.startswith("__"):
                    payload[k] = v
            try:
                pr = session.post(
                    home_url,
                    data=payload,
                    headers=hdrs_post,
                    timeout=timeout,
                    allow_redirects=True,
                )
                if pr.status_code == 200:
                    return pr.url, pr.text
            except Exception:
                pass

        # Fallback: public-ish finder
        try:
            q = self._abs(f"/findit?search={upc}")
            fr = session.get(
                q,
                headers=self._browser_headers(referer=home_url, origin=self.origin),
                timeout=timeout,
                allow_redirects=True,
            )
            if fr.status_code == 200:
                return fr.url, fr.text
        except Exception:
            pass

        return "", ""

    def _extract_product_link(self, html_text: str) -> str:
        """Extract product link from search results."""
        m = re.search(r'href="(/index\.aspx\?tab=7&amp;sku=\d+)"', html_text, re.I)
        if m:
            return html.unescape(m.group(1)).replace("&amp;", "&")
        m = re.search(r'href="(/index\.aspx\?tab=7&sku=\d+)"', html_text, re.I)
        if m:
            return html.unescape(m.group(1))
        m = re.search(r'href="(/product/[^"]+)"', html_text, re.I)
        if m:
            return html.unescape(m.group(1))
        return ""

    def find_product_url(
        self,
        upc: str,
        session: requests.Session,
        timeout: int,
        log: Callable[[str], None],
    ) -> str:
        """
        Find product page URL for a given UPC.

        Args:
            upc: UPC to search for
            session: Authenticated session
            timeout: Request timeout in seconds
            log: Logging function

        Returns:
            Product URL or empty string if not found
        """
        upc_digits = normalize_upc(upc)
        if not upc_digits:
            return ""

        # Check overrides first
        if upc_digits in self.upc_overrides:
            return self.upc_overrides[upc_digits]

        # Perform search
        final_url, html_text = self._search_upc(upc_digits, session, timeout, log)
        if not html_text:
            return ""

        # Check if we're already on a product page
        if re.search(r"/index\.aspx\?tab=7(&|&amp;)sku=\d+", final_url or "", re.I):
            return self._abs(final_url)

        # Extract product link from results
        rel = self._extract_product_link(html_text)
        return self._abs(rel) if rel else ""
