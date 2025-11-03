"""
HTTP request utilities for product collectors.

Provides session management, header building, and request helpers.
"""

from typing import Optional, Dict, Any
import time


def build_browser_headers(
    origin: str,
    referer: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Dict[str, str]:
    """
    Build browser-like HTTP headers.

    Args:
        origin: Origin URL (e.g., "https://example.com")
        referer: Referer URL (defaults to origin + "/")
        user_agent: User agent string (defaults to Safari on macOS)

    Returns:
        Dictionary of HTTP headers
    """
    if user_agent is None:
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.6 Safari/605.1.15"
        )

    if referer is None:
        referer = origin.rstrip("/") + "/"

    return {
        "User-Agent": user_agent,
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }


class RateLimiter:
    """
    Simple rate limiter for HTTP requests.

    Ensures minimum time between requests to respect server resources.
    """

    def __init__(self, min_delay_seconds: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            min_delay_seconds: Minimum seconds between requests
        """
        self.min_delay = min_delay_seconds
        self.last_request_time: Optional[float] = None

    def wait(self) -> None:
        """
        Wait if necessary to respect rate limit.

        Call before making an HTTP request.
        """
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)

        self.last_request_time = time.time()


def retry_request(
    func,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
    *args,
    **kwargs
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to call
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func if successful

    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    delay = 1.0

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= backoff_factor

    # All retries failed
    raise last_exception
