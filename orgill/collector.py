#!/usr/bin/env python3
"""
Orgill Product Collector

Collects product data from https://www.orgill.com.
"""

import os
import sys
from typing import Dict, Any, Optional

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .auth import OrgillAuthenticator, StrategyLoginError
from .search import OrgillSearcher
from .parser import OrgillParser


# Site Configuration (embedded from profile)
SITE_CONFIG = {
    "key": "orgill",
    "display_name": "Orgill",
    "origin": "https://www.orgill.com",
    "referer": "https://www.orgill.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
    "robots": "respect",
    "search": {"upc_overrides": {}},
}


class OrgillCollector:
    """Orgill product data collector."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize collector.

        Args:
            config: Optional site configuration (defaults to SITE_CONFIG)
        """
        self.config = config or SITE_CONFIG
        self.authenticator = OrgillAuthenticator(self.config)
        self.searcher = OrgillSearcher(self.config)
        self.parser = OrgillParser(self.config.get("origin", ""))

    def attach_session(self, session) -> None:
        """
        Attach pooled session for persistent cookies.

        Args:
            session: Requests session
        """
        self.authenticator.attach_session(session)

    def set_auth(
        self, username: str | dict, password: Optional[str] = None
    ) -> None:
        """
        Set authentication credentials.

        Args:
            username: Username or dict with username/password
            password: Password (if username is string)
        """
        self.authenticator.set_auth(username, password)

    def find_product_url(self, upc: str, http_get=None, timeout: int = 20, log=print) -> str:
        """
        Find product page URL for a given UPC.

        Requires authentication. Will raise StrategyLoginError if login fails.

        Args:
            upc: UPC to search for
            http_get: HTTP GET function (not used, kept for interface compatibility)
            timeout: Request timeout in seconds
            log: Logging function

        Returns:
            Product URL or empty string if not found

        Raises:
            StrategyLoginError: If authentication fails
        """
        # Login (will raise StrategyLoginError if it fails)
        self.authenticator.login(log, timeout=timeout)

        # Get authenticated session
        session = self.authenticator._ensure_session()

        # Perform search
        return self.searcher.find_product_url(upc, session, timeout, log)

    def parse_page(self, html_text: str) -> Dict[str, Any]:
        """
        Parse product page HTML.

        Args:
            html_text: HTML content of product page

        Returns:
            Dictionary with extracted product data
        """
        return self.parser.parse_page(html_text)


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
