"""
Authentication handling for Orgill collector.

Manages login and session authentication.
"""

import re
import time
from typing import Dict, Optional, Callable
import requests
from bs4 import BeautifulSoup
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import text_only


class StrategyLoginError(Exception):
    """Raised when an Orgill login attempt fails so the job can stop immediately."""
    pass


class OrgillAuthenticator:
    """Handles authentication for Orgill portal."""

    def __init__(self, config: dict):
        """
        Initialize authenticator.

        Args:
            config: Site configuration dict
        """
        self.config = config
        self.origin = config.get("origin", "").rstrip("/")
        self.session: Optional[requests.Session] = None
        self.auth: Optional[Dict[str, str]] = None

        # Detected form fields
        self._login_form_action: Optional[str] = None
        self._detected_user_field: Optional[str] = None
        self._detected_pass_field: Optional[str] = None

    def attach_session(self, session: requests.Session) -> None:
        """
        Attach pooled session from the GUI so cookies persist.

        Args:
            session: Requests session
        """
        if isinstance(session, requests.Session):
            self.session = session

    def set_auth(
        self, username: str | dict, password: Optional[str] = None
    ) -> None:
        """
        Set authentication credentials.

        Args:
            username: Username or dict with username/password
            password: Password (if username is string)
        """
        if isinstance(username, dict):
            self.auth = {
                "username": (username.get("username") or "").strip(),
                "password": (username.get("password") or "").strip(),
            }
        else:
            self.auth = {
                "username": (username or "").strip(),
                "password": (password or "").strip(),
            }

    def _ensure_session(self) -> requests.Session:
        """Return the attached session or create a private one if absent."""
        if not isinstance(self.session, requests.Session):
            self.session = requests.Session()
        return self.session

    def _abs(self, path_or_url: str) -> str:
        """Convert relative path to absolute URL."""
        if not path_or_url:
            return ""
        if path_or_url.lower().startswith("http"):
            return path_or_url
        return f"{self.origin}/{path_or_url.lstrip('/')}"

    def _browser_headers(
        self,
        referer: Optional[str] = None,
        origin: Optional[str] = None,
        ua: Optional[str] = None,
    ) -> Dict[str, str]:
        """Build 'browsery' headers using site profile hints with safe fallbacks."""
        origin = (origin or self.config.get("origin") or "").rstrip("/")
        referer = referer or self.config.get("referer") or origin or ""
        ua = ua or self.config.get("user_agent") or (
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
        Extract hidden inputs from the login form.

        Also captures form action and detected username/password field names.

        Args:
            html_text: HTML content

        Returns:
            Dictionary of hidden field values
        """
        vals: Dict[str, str] = {}
        self._login_form_action = None
        self._detected_user_field = None
        self._detected_pass_field = None

        soup = BeautifulSoup(html_text or "", "html.parser")

        # Find login form
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
        Pull inline error text if present.

        Args:
            html_text: HTML content

        Returns:
            Error message or empty string
        """
        try:
            soup = BeautifulSoup(html_text or "", "html.parser")
            lbl = soup.select_one("#cphMainContent_lblErrorMessage")
            if lbl:
                msg = text_only(lbl.get_text(" ", strip=True))
                if msg:
                    return msg
            blob = soup.get_text(" ", strip=True)
            for needle in (
                "Password Expired",
                "Failed Login Attempts",
                "Update Password",
            ):
                if needle.lower() in blob.lower():
                    return needle
        except Exception:
            pass
        return ""

    def login(self, log: Callable[[str], None], timeout: int = 20) -> bool:
        """
        Authenticate against the Orgill portal.

        Args:
            log: Logging function
            timeout: Request timeout in seconds

        Returns:
            True if login successful

        Raises:
            StrategyLoginError: If login fails
        """
        if not self.origin:
            raise StrategyLoginError("OrgillStrategy: missing 'origin' in profile.")

        session = self._ensure_session()

        # Quick probe: already authenticated?
        try:
            hdrs_probe = self._browser_headers(referer=self.origin, origin=self.origin)
            r0 = session.get(
                self._abs("/Default.aspx"),
                headers=hdrs_probe,
                timeout=timeout,
                allow_redirects=True,
            )
            if r0.status_code == 200 and (
                ("Sign Out" in r0.text)
                or ("signOut.aspx" in r0.text)
                or ("My Profile" in r0.text)
            ):
                return True
        except Exception:
            pass

        if not self.auth:
            raise StrategyLoginError(
                "OrgillStrategy: no credentials present; cannot log in."
            )

        user = self.auth.get("username", "")
        pwd = self.auth.get("password", "")
        if not (user and pwd):
            raise StrategyLoginError(
                "OrgillStrategy: no credentials present in auth; cannot log in."
            )

        # Default login landing
        profile_login_url = self.config.get("login_url")
        login_url = self._abs("/index.aspx?tab=8")
        if profile_login_url:
            login_url = (
                profile_login_url
                if profile_login_url.lower().startswith("http")
                else self._abs(profile_login_url)
            )

        # 1) Priming GET — establish cookies + pull hidden fields
        hdrs_get = self._browser_headers(referer=self.origin, origin=self.origin)
        try:
            r1 = session.get(
                login_url, headers=hdrs_get, timeout=timeout, allow_redirects=True
            )
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
                raise StrategyLoginError(
                    f"OrgillStrategy: login page HTTP {r1.status_code}"
                )
            hidden = self._parse_hidden_fields(r1.text)
        except StrategyLoginError:
            raise
        except Exception as e:
            raise StrategyLoginError(f"OrgillStrategy: login GET failed: {e}")

        # Use the actual form action when present
        post_url = self._login_form_action or login_url

        # Use detected field names
        user_field = (
            self._detected_user_field
            or "ctl00$cphMainContent$ctl00$loginOrgillxs$UserName"
        )
        pass_field = (
            self._detected_pass_field
            or "ctl00$cphMainContent$ctl00$loginOrgillxs$Password"
        )

        submit_field = "ctl00$cphMainContent$ctl00$loginOrgillxs$LoginButton"
        remember_key = "ctl00$cphMainContent$ctl00$loginOrgillxs$RememberMe"

        time.sleep(0.35)  # brief pause for WAF friendliness

        ok = False
        last_text = ""
        hdrs_post = self._browser_headers(referer=login_url, origin=self.origin)
        hdrs_post["Content-Type"] = "application/x-www-form-urlencoded"

        # Variant A: include the submit button field
        payload_a = dict(hidden)
        payload_a[user_field] = user
        payload_a[pass_field] = pwd
        payload_a[submit_field] = payload_a.get(submit_field, "LOGIN") or "LOGIN"
        if remember_key in payload_a:
            payload_a[remember_key] = "on"

        # Variant B: drive __EVENTTARGET instead
        payload_b = dict(hidden)
        payload_b["__EVENTTARGET"] = submit_field
        payload_b[user_field] = user
        payload_b[pass_field] = pwd
        if remember_key in payload_b:
            payload_b[remember_key] = "on"

        for idx, payload in enumerate((payload_a, payload_b), 1):
            try:
                r2 = session.post(
                    post_url,
                    data=payload,
                    headers=hdrs_post,
                    timeout=timeout,
                    allow_redirects=True,
                )

                # Log cookie keys after POST
                try:
                    log(
                        f"OrgillStrategy: cookie keys after POST: {list(session.cookies.get_dict().keys())}"
                    )
                except Exception:
                    pass

                if r2.status_code == 403:
                    last_text = r2.text or ""
                    log(
                        f"OrgillStrategy: variant {idx} POST 403 — CSRF/Referer/Origin mismatch or WAF block."
                    )
                    continue
                if r2.status_code >= 400:
                    last_text = r2.text or ""
                    log(f"OrgillStrategy: variant {idx} POST HTTP {r2.status_code}")
                    continue

                chain = " -> ".join(
                    [h.url for h in (r2.history or [])] + [r2.url or ""]
                )
                log(f"OrgillStrategy: variant {idx} landed at {chain}")

                # Heuristic success checks
                if r2.url and re.search(r"/Login\b", r2.url, re.I):
                    last_text = r2.text or ""
                    continue
                if (
                    ("Sign Out" in r2.text)
                    or ("signOut.aspx" in r2.text)
                    or ("My Profile" in r2.text)
                ):
                    ok = True
                    break

                # Fallback probe for signed-in UI
                rp = session.get(
                    self._abs("/Default.aspx"),
                    headers=self._browser_headers(referer=post_url, origin=self.origin),
                    timeout=timeout,
                )
                last_text = rp.text or r2.text or ""
                if rp.status_code == 200 and (
                    ("Sign Out" in rp.text)
                    or ("signOut.aspx" in rp.text)
                    or ("My Profile" in rp.text)
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
            raise StrategyLoginError(
                "OrgillStrategy: login failed (no auth cookie or success indicators)."
            )

        return True
