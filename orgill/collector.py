#!/usr/bin/env python3
"""
Orgill Product Collector

Collects product data from https://www.orgill.com.
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
    "key": "orgill",
    "display_name": "Orgill",
    "origin": "https://www.orgill.com",
    "referer": "https://www.orgill.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
    "robots": "respect",
    "search": {
        "upc_overrides": {}
    }
}

# strategies/orgill.py
from __future__ import annotations
from .base import SiteStrategy
from typing import Optional, Dict, Any, List, Tuple
import re
import html
import time
import requests
from bs4 import BeautifulSoup  # pip install beautifulsoup4


class StrategyLoginError(Exception):
    """Raised when an Orgill login attempt fails so the job can stop immediately."""
    pass


class OrgillStrategy(SiteStrategy):
    """
    Authenticates against the Orgill portal using the app's pooled session (attach via attach_session),
    then performs an authenticated UPC search and returns the product page URL.

    self._auth should be {"username": "...", "password": "..."} (set by the GUI).
    """

    # -----------------------
    # helpers
    # -----------------------

    @staticmethod
    def _text_only(s: str) -> str:
        s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        return html.unescape(s).strip()

    def attach_session(self, session: requests.Session) -> None:
        """Attach pooled session from the GUI so cookies persist across login/search."""
        if isinstance(session, requests.Session):
            self._session = session

    def set_auth(self, username: str | dict, password: str | None = None) -> None:
        """
        Accept either a dict {"username": "...", "password": "..."} or username/password pair.
        """
        if isinstance(username, dict):
            self._auth = {
                "username": (username.get("username") or "").strip(),
                "password": (username.get("password") or "").strip(),
            }
        else:
            self._auth = {"username": (username or "").strip(), "password": (password or "").strip()}

    def _ensure_session(self) -> requests.Session:
        """Return the attached session or create a private one if absent."""
        sess = getattr(self, "_session", None)
        if not isinstance(sess, requests.Session):
            sess = requests.Session()
            self._session = sess
        return sess

    def _abs(self, path_or_url: str) -> str:
        if not path_or_url:
            return ""
        if path_or_url.lower().startswith("http"):
            return path_or_url
        origin = (self.profile.get("origin") or "").rstrip("/")
        return f"{origin}/{path_or_url.lstrip('/')}"

    def _browser_headers(
        self,
        referer: Optional[str] = None,
        origin: Optional[str] = None,
        ua: Optional[str] = None,
    ) -> Dict[str, str]:
        """Build ‘browsery’ headers using site profile hints with safe fallbacks."""
        p = self.profile or {}
        origin = (origin or p.get("origin") or "").rstrip("/")
        referer = referer or p.get("referer") or origin or ""
        ua = ua or p.get("user_agent") or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
        )
        h = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Upgrade-Insecure-Requests": "1",
        }
        if origin:
            h["Origin"] = origin
        return h

    def _parse_hidden_fields(self, html_text: str) -> Dict[str, str]:
        """
        Extract hidden inputs from the actual login form (id/name/action ~ ‘login’ or index.aspx?tab=8),
        falling back to the first <form>. Also capture the form action and the
        detected username/password field names if present.
        """
        vals: Dict[str, str] = {}
        self._login_form_action = None
        self._detected_user_field = None
        self._detected_pass_field = None

        soup = BeautifulSoup(html_text or "", "html.parser")

        # Prefer the login form; else first form. The uploaded page’s form action is "./index.aspx?tab=8".
        form = (
            soup.find("form", id=re.compile(r"login", re.I))
            or soup.find("form", {"name": re.compile(r"login", re.I)})
            or soup.find("form", action=re.compile(r"login|index\.aspx\?tab=8", re.I))
            or soup.find("form")
        )

        if form:
            action = form.get("action") or ""
            self._login_form_action = self._abs(action) if action else None
            inputs = form.find_all("input")
        else:
            inputs = soup.find_all("input")

        user_candidates = [
            "ctl00$cphMainContent$ctl00$loginOrgillxs$UserName",
            "Login1$UserName",
            "ctl00$MainContent$Login1$UserName",
            "UserName",
            "username",
        ]
        pass_candidates = [
            "ctl00$cphMainContent$ctl00$loginOrgillxs$Password",
            "Login1$Password",
            "ctl00$MainContent$Login1$Password",
            "Password",
            "password",
        ]

        for el in inputs:
            typ = (el.get("type") or "").lower()
            name = el.get("name") or ""
            val = el.get("value") or ""
            if typ == "hidden" and name:
                vals[name] = val
            if not self._detected_user_field and name in user_candidates:
                self._detected_user_field = name
            if not self._detected_pass_field and name in pass_candidates:
                self._detected_pass_field = name

        # Ensure WebForms scaffolding keys exist
        for k in ("__EVENTTARGET", "__EVENTARGUMENT", "__LASTFOCUS"):
            vals.setdefault(k, "")

        return vals

    def _extract_inline_error(self, html_text: str) -> str:
        """
        Pull inline error text if present (e.g., cphMainContent_lblErrorMessage),
        and heuristic popups (Password Expired / Failed Login Attempts / Update Password).
        """
        try:
            soup = BeautifulSoup(html_text or "", "html.parser")
            lbl = soup.select_one("#cphMainContent_lblErrorMessage")
            if lbl:
                msg = self._text_only(lbl.get_text(" ", strip=True))
                if msg:
                    return msg
            blob = soup.get_text(" ", strip=True)
            for needle in ("Password Expired", "Failed Login Attempts", "Update Password"):
                if needle.lower() in blob.lower():
                    return needle
        except Exception:
            pass
        return ""

    # -----------------------
    # login + search
    # -----------------------

    def _login(self, session: requests.Session, log, timeout: int = 20) -> bool:
        origin = (self.profile.get("origin") or "").rstrip("/")
        if not origin:
            raise StrategyLoginError("OrgillStrategy: missing 'origin' in profile.")

        # Quick probe: already authenticated?
        try:
            hdrs_probe = self._browser_headers(referer=origin, origin=origin)
            r0 = session.get(self._abs("/Default.aspx"), headers=hdrs_probe, timeout=timeout, allow_redirects=True)
            if r0.status_code == 200 and (
                ("Sign Out" in r0.text) or ("signOut.aspx" in r0.text) or ("My Profile" in r0.text)
            ):
                return True
        except Exception:
            pass

        auth = getattr(self, "_auth", None) or {}
        user = (auth.get("username") or "").strip()
        pwd  = (auth.get("password") or "").strip()
        if not (user and pwd):
            raise StrategyLoginError("OrgillStrategy: no credentials present in self._auth; cannot log in.")

        # Default login landing per the page: /index.aspx?tab=8
        profile_login_url = self.profile.get("login_url")
        login_url = self._abs("/index.aspx?tab=8")
        if profile_login_url:
            login_url = profile_login_url if profile_login_url.lower().startswith("http") else self._abs(profile_login_url)

        # 1) Priming GET — establish cookies + pull hidden fields
        hdrs_get = self._browser_headers(referer=origin, origin=origin)
        try:
            r1 = session.get(login_url, headers=hdrs_get, timeout=timeout, allow_redirects=True)
            if r1.status_code == 403:
                try:
                    keys = list(session.cookies.get_dict().keys())
                except Exception:
                    keys = []
                raise StrategyLoginError(
                    f"OrgillStrategy: login page HTTP 403 on GET (likely WAF/headers). "
                    f"Cookie keys after GET: {keys}"
                )
            if r1.status_code >= 400:
                raise StrategyLoginError(f"OrgillStrategy: login page HTTP {r1.status_code}")
            hidden = self._parse_hidden_fields(r1.text)
        except StrategyLoginError:
            raise
        except Exception as e:
            raise StrategyLoginError(f"OrgillStrategy: login GET failed: {e}")

        # Use the actual form action when present
        post_url = self._login_form_action or login_url

        # Use detected field names (fallback to the observed long names)
        user_field = self._detected_user_field or "ctl00$cphMainContent$ctl00$loginOrgillxs$UserName"
        pass_field = self._detected_pass_field or "ctl00$cphMainContent$ctl00$loginOrgillxs$Password"

        # Submit button / remember-me observed on the page.
        submit_field = "ctl00$cphMainContent$ctl00$loginOrgillxs$LoginButton"
        remember_key = "ctl00$cphMainContent$ctl00$loginOrgillxs$RememberMe"

        time.sleep(0.35)  # brief pause for WAF friendliness

        ok = False
        last_text = ""
        hdrs_post = self._browser_headers(referer=login_url, origin=origin)
        hdrs_post["Content-Type"] = "application/x-www-form-urlencoded"

        # Variant A: include the submit button field
        payload_a = dict(hidden)
        payload_a[user_field] = user
        payload_a[pass_field] = pwd
        payload_a[submit_field] = payload_a.get(submit_field, "LOGIN") or "LOGIN"
        if remember_key in payload_a:
            payload_a[remember_key] = "on"

        # Variant B: drive __EVENTTARGET instead of button field
        payload_b = dict(hidden)
        payload_b["__EVENTTARGET"] = submit_field
        payload_b[user_field] = user
        payload_b[pass_field] = pwd
        if remember_key in payload_b:
            payload_b[remember_key] = "on"

        for idx, payload in enumerate((payload_a, payload_b), 1):
            try:
                r2 = session.post(post_url, data=payload, headers=hdrs_post, timeout=timeout, allow_redirects=True)

                # Log cookie keys after POST
                try:
                    log(f"OrgillStrategy: cookie keys after POST: {list(session.cookies.get_dict().keys())}")
                except Exception:
                    pass

                if r2.status_code == 403:
                    last_text = r2.text or ""
                    log(f"OrgillStrategy: variant {idx} POST 403 — CSRF/Referer/Origin mismatch or WAF block.")
                    continue
                if r2.status_code >= 400:
                    last_text = r2.text or ""
                    log(f"OrgillStrategy: variant {idx} POST HTTP {r2.status_code}")
                    continue

                chain = " -> ".join([h.url for h in (r2.history or [])] + [r2.url or ""])
                log(f"OrgillStrategy: variant {idx} landed at {chain}")

                # Heuristic success checks
                if r2.url and re.search(r"/Login\b", r2.url, re.I):
                    last_text = r2.text or ""
                    continue
                if ("Sign Out" in r2.text) or ("signOut.aspx" in r2.text) or ("My Profile" in r2.text):
                    ok = True
                    break

                # Fallback probe for signed-in UI
                rp = session.get(
                    self._abs("/Default.aspx"),
                    headers=self._browser_headers(referer=post_url, origin=origin),
                    timeout=timeout,
                )
                last_text = rp.text or r2.text or ""
                if rp.status_code == 200 and (
                    ("Sign Out" in rp.text) or ("signOut.aspx" in rp.text) or ("My Profile" in rp.text)
                ):
                    ok = True
                    break
            except Exception as e:
                last_text = ""
                log(f"OrgillStrategy: variant {idx} POST error: {e}")

        if not ok:
            friendly = self._extract_inline_error(last_text) if last_text else ""
            if friendly:
                raise StrategyLoginError(f"OrgillStrategy: login failed — {friendly}")
            raise StrategyLoginError("OrgillStrategy: login failed (no auth cookie or success indicators).")

        return True

    def _search_upc(self, upc: str, session: requests.Session, timeout: int, log) -> Tuple[str, str]:
        """
        Perform an authenticated UPC search. Tries the Default.aspx WebForms postback first,
        then falls back to a simpler /findit query if present.
        """
        home_url = self._abs("/Default.aspx")
        try:
            r = session.get(
                home_url,
                headers=self._browser_headers(referer=home_url, origin=self.profile.get("origin")),
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

        hdrs_post = self._browser_headers(referer=home_url, origin=self.profile.get("origin"))
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
                    home_url, data=payload, headers=hdrs_post, timeout=timeout, allow_redirects=True
                )
                if pr.status_code == 200:
                    return pr.url, pr.text
            except Exception:
                pass

        # Fallback: public-ish finder (may still require auth)
        try:
            q = self._abs(f"/findit?search={upc}")
            fr = session.get(
                q,
                headers=self._browser_headers(referer=home_url, origin=self.profile.get("origin")),
                timeout=timeout,
                allow_redirects=True,
            )
            if fr.status_code == 200:
                return fr.url, fr.text
        except Exception:
            pass

        return "", ""

    def _extract_product_link(self, html_text: str) -> str:
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

    # -----------------------
    # strategy API
    # -----------------------

    def find_product_page_url_for_upc(self, upc: str, http_get=None, timeout: int = 20, log=print) -> str:
        upc_digits = re.sub(r"\D", "", str(upc or ""))
        if not upc_digits:
            return ""

        overrides = ((self.profile.get("search") or {}).get("upc_overrides") or {})
        if upc_digits in overrides:
            return overrides[upc_digits]

        session = self._ensure_session()

        # IMPORTANT: if login fails, this will raise StrategyLoginError (abort job).
        self._login(session, log, timeout=timeout)

        final_url, html_text = self._search_upc(upc_digits, session, timeout, log)
        if not html_text:
            return ""

        if re.search(r"/index\.aspx\?tab=7(&|&amp;)sku=\d+", final_url or "", re.I):
            return self._abs(final_url)

        rel = self._extract_product_link(html_text)
        return self._abs(rel) if rel else ""

    def parse_page(self, html_text: str) -> dict:
        """
        Parse product detail page. Pull:
        - title (existing heuristic),
        - brand (Vendor),
        - description (Product Overview paragraph),
        - benefits (Features list; ALL <li> items),
        - gallery_images (regex for Orgill CDN),
        - extra hints if present.
        """
        soup = BeautifulSoup(html_text or "", "html.parser")

        def grab_id(i: str) -> str:
            el = soup.select_one(f'#{i}')
            if el:
                return self._text_only(el.get_text(" ", strip=True))
            m = re.search(rf'id="{re.escape(i)}"\s*>\s*([^<]+)<', html_text or "")
            return self._text_only(m.group(1)) if m else ""

        # Title
        title = grab_id("cphMainContent_ctl00_lblDescription") or grab_id("cphMainContent_lblDescription")

        # Brand (Vendor)
        brand_el = soup.select_one("#cphMainContent_ctl00_lblVendorName") or soup.select_one("#cphMainContent_lblVendorName")
        brand = self._text_only(brand_el.get_text(" ", strip=True)) if brand_el else ""

        # Description (Product Overview)
        def first_overview_paragraph(container) -> str:
            if not container:
                return ""
            p = container.find("p", class_=re.compile(r"\btext-details-description\b", re.I))
            return self._text_only(p.get_text(" ", strip=True)) if p else ""

        pov = soup.select_one("#cphMainContent_ctl00_lblProductOverview")
        pov_xs = soup.select_one("#cphMainContent_ctl00_lblProductOverviewxs")
        description = first_overview_paragraph(pov) or first_overview_paragraph(pov_xs)

        # --- BENEFITS (robust “Features” list capture) ---
        benefits: List[str] = []

        # 1) Find the header whose text is exactly "Features"
        header = None
        for h in soup.find_all(["h3", "h4"], class_=re.compile(r"\btext-details-header\b", re.I)):
            if self._text_only(h.get_text()).lower() == "features":
                header = h
                break

        # 2) From that header, locate the first following UL/OL (or any block that contains <li>)
        if header:
            # Look ahead for a list container right after the header
            list_container = header.find_next(lambda t: (
                t.name in ("ul", "ol") or
                (t.name in ("div", "section") and t.find("li"))
            ))
            if list_container:
                for li in list_container.find_all("li"):
                    txt = self._text_only(li.get_text(" ", strip=True))
                    if txt:
                        benefits.append(txt)

        # Fallback: if nothing found, try any block adjacent to a “Features” label
        if not benefits:
            cand = soup.find(string=re.compile(r"^\s*Features\s*$", re.I))
            if cand:
                parent = getattr(cand, "parent", None)
                block = parent.find_next(lambda t: t and (t.name in ("ul", "ol") or t.find("li"))) if parent else None
                if block:
                    for li in block.find_all("li"):
                        txt = self._text_only(li.get_text(" ", strip=True))
                        if txt:
                            benefits.append(txt)

        # Gallery images (Orgill CDN)
        imgs: List[str] = []
        for m in re.finditer(r'https?://images\.orgill\.com/weblarge/[^"]+\.jpg', html_text or "", flags=re.I):
            u = html.unescape(m.group(0))
            if u not in imgs:
                imgs.append(u)

        country = grab_id("cphMainContent_ctl00_lblCountryOfOrigin")
        item_number = grab_id("cphMainContent_ctl00_lblOrgillItemNumber")

        return {
            "title": title,
            "brand_hint": brand,
            "description": description,
            "benefits": benefits,              # <- now all features, not just the last one
            "gallery_images": imgs,
            "country_of_origin": country,
            "orgill_item_number": item_number,
        }



def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Orgill Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

if __name__ == "__main__":
    main()
