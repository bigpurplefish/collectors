#!/usr/bin/env python3
"""
Test Image URL Validation

Tests the hardened verify_image_url() and clean_and_verify_image_url() functions
in shared/utils/image_utils.py. All tests are fast (mocked, no network).
"""

import logging
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Add shared utils to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'shared'))

from utils.image_utils import verify_image_url, clean_and_verify_image_url


def _mock_response(status_code=200, content_type="image/jpeg", body=b"\x89PNG\r\n"):
    """Create a mock response object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"Content-Type": content_type} if content_type else {}
    resp.iter_content = MagicMock(return_value=iter([body]))
    return resp


class TestVerifyImageUrl(unittest.TestCase):

    @patch("utils.image_utils.requests.head")
    def test_verify_rejects_html_content_type(self, mock_head):
        """HEAD returns text/html -> False"""
        mock_head.return_value = _mock_response(content_type="text/html")
        result = verify_image_url("https://example.com/image.jpg")
        self.assertFalse(result)

    @patch("utils.image_utils.requests.get")
    @patch("utils.image_utils.requests.head")
    def test_verify_rejects_html_body(self, mock_head, mock_get):
        """GET body starts with <!DOCTYPE -> False"""
        # HEAD returns no Content-Type, triggering GET fallback
        mock_head.return_value = _mock_response(content_type=None)
        # GET also has no Content-Type so body inspection runs
        mock_get.return_value = _mock_response(
            content_type=None,
            body=b"<!DOCTYPE html><html><body>Not Found</body></html>"
        )
        result = verify_image_url("https://example.com/image.jpg")
        self.assertFalse(result)

    @patch("utils.image_utils.requests.head")
    def test_verify_accepts_valid_image(self, mock_head):
        """HEAD returns image/jpeg -> True"""
        mock_head.return_value = _mock_response(content_type="image/jpeg")
        result = verify_image_url("https://example.com/image.jpg")
        self.assertTrue(result)

    @patch("utils.image_utils.requests.get")
    @patch("utils.image_utils.requests.head")
    def test_verify_falls_through_on_empty_content_type(self, mock_head, mock_get):
        """HEAD missing Content-Type, GET returns valid image -> True"""
        mock_head.return_value = _mock_response(content_type=None)
        mock_get.return_value = _mock_response(
            content_type="image/png",
            body=b"\x89PNG\r\n"
        )
        result = verify_image_url("https://example.com/image.png")
        self.assertTrue(result)

    @patch("utils.image_utils.requests.get")
    @patch("utils.image_utils.requests.head")
    def test_verify_rejects_xml_body(self, mock_head, mock_get):
        """GET body starts with <?xml -> False"""
        mock_head.return_value = _mock_response(content_type=None)
        # GET has no Content-Type so body inspection runs
        mock_get.return_value = _mock_response(
            content_type=None,
            body=b"<?xml version='1.0'?><error>Not Found</error>"
        )
        result = verify_image_url("https://example.com/image.jpg")
        self.assertFalse(result)

    @patch("utils.image_utils.requests.get")
    @patch("utils.image_utils.requests.head")
    def test_clean_and_verify_returns_none_on_failure(self, mock_head, mock_get):
        """Both cleaned and original fail -> None"""
        mock_head.return_value = _mock_response(status_code=404)
        mock_get.return_value = _mock_response(status_code=404)
        result = clean_and_verify_image_url("https://example.com/image.jpg?v=123")
        self.assertIsNone(result)

    @patch("utils.image_utils.requests.head")
    def test_verify_logs_rejection_reason(self, mock_head):
        """Debug-level messages emitted on rejection"""
        mock_head.return_value = _mock_response(content_type="text/html")
        with self.assertLogs("root", level="DEBUG") as cm:
            verify_image_url("https://example.com/image.jpg")
        self.assertTrue(any("Content-Type" in msg for msg in cm.output))


def run_tests():
    print("")
    print("=" * 80)
    print("TEST: Image URL Validation")
    print("=" * 80)
    print("")

    # Enable debug logging for the test that checks log output
    logging.basicConfig(level=logging.DEBUG, force=True)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestVerifyImageUrl)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
