"""
Comprehensive tests for search module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.search import PurinamillsSearcher


# Test configuration
TEST_CONFIG = {
    "shop_origin": "https://shop.purinamills.com",
    "www_origin": "https://www.purinamills.com",
    "shop_search_path": "/search",
    "www_search_path": "/search",
    "shop_search_param": "q",
    "www_search_param": "s",
    "max_search_candidates": 10,
    "fuzzy_match_threshold": 0.3
}


class TestPurinamillsSearcherInit:
    """Test PurinamillsSearcher initialization."""

    def test_init_with_full_config(self):
        """Should initialize with all config values"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        assert searcher.shop_origin == "https://shop.purinamills.com"
        assert searcher.www_origin == "https://www.purinamills.com"
        assert searcher.shop_search_path == "/search"
        assert searcher.www_search_path == "/search"
        assert searcher.shop_search_param == "q"
        assert searcher.www_search_param == "s"
        assert searcher.max_search_candidates == 10
        assert searcher.fuzzy_match_threshold == 0.3

    def test_init_with_defaults(self):
        """Should use defaults for missing config values"""
        searcher = PurinamillsSearcher({})

        assert searcher.shop_origin == "https://shop.purinamills.com"
        assert searcher.www_origin == "https://www.purinamills.com"
        assert searcher.max_search_candidates == 10
        assert searcher.fuzzy_match_threshold == 0.3


class TestKeywordSet:
    """Test _keyword_set method."""

    def test_basic_keyword_extraction(self):
        """Should extract basic keywords"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        kw = searcher._keyword_set("Premium Dog Food")

        assert "premium" in kw
        assert "dog" in kw
        # "food" is a stop word
        assert "food" not in kw

    def test_stop_words_removed(self):
        """Should remove stop words"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        kw = searcher._keyword_set("Purina Mills Horse Feed with High Nutrition")

        # Stop words should be filtered
        assert "purina" not in kw
        assert "mills" not in kw
        assert "horse" not in kw
        assert "feed" not in kw
        assert "with" not in kw
        assert "high" not in kw
        assert "nutrition" not in kw

    def test_synonym_mapping(self):
        """Should apply synonym mapping"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        kw = searcher._keyword_set("Equine Treats")

        # "equine" should be mapped to "horse" (which is then filtered as stop word)
        assert "equine" not in kw
        assert "treats" in kw

    def test_short_words_filtered(self):
        """Should filter words with < 2 characters"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        kw = searcher._keyword_set("A B Cat D")

        assert "a" not in kw
        assert "b" not in kw
        assert "cat" in kw
        assert "d" not in kw

    def test_digits_filtered(self):
        """Should filter pure digit strings"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        kw = searcher._keyword_set("Product 50 Premium 100")

        assert "50" not in kw
        assert "100" not in kw
        assert "product" in kw
        assert "premium" in kw

    def test_empty_string(self):
        """Should handle empty string"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        kw = searcher._keyword_set("")

        assert len(kw) == 0


class TestFuzzyMatchScore:
    """Test _fuzzy_match_score method."""

    def test_perfect_match(self):
        """Should return 1.0 for identical keyword sets"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        kw1 = {"premium", "dog"}
        kw2 = {"premium", "dog"}

        score = searcher._fuzzy_match_score(kw1, kw2)
        assert score == 1.0

    def test_partial_match(self):
        """Should return fraction for partial match"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        candidate_kw = {"premium", "dog", "treats"}
        query_kw = {"premium", "dog"}

        score = searcher._fuzzy_match_score(candidate_kw, query_kw)
        assert score == 1.0  # 2 out of 2 query keywords found

    def test_no_match(self):
        """Should return 0.0 for no match"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        candidate_kw = {"premium", "dog"}
        query_kw = {"cat", "treats"}

        score = searcher._fuzzy_match_score(candidate_kw, query_kw)
        assert score == 0.0

    def test_empty_query(self):
        """Should return 0.0 for empty query"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        candidate_kw = {"premium", "dog"}
        query_kw = set()

        score = searcher._fuzzy_match_score(candidate_kw, query_kw)
        assert score == 0.0


class TestAbsUrl:
    """Test _abs_url method."""

    def test_absolute_url_unchanged(self):
        """Should leave absolute URLs unchanged"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        url = "https://example.com/product"

        result = searcher._abs_url(url, "https://shop.purinamills.com")
        assert result == url

    def test_relative_url_with_slash(self):
        """Should convert relative URL with leading slash"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        href = "/products/horse-feed"

        result = searcher._abs_url(href, "https://shop.purinamills.com")
        assert result == "https://shop.purinamills.com/products/horse-feed"

    def test_relative_url_without_slash(self):
        """Should convert relative URL without leading slash"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        href = "products/horse-feed"

        result = searcher._abs_url(href, "https://shop.purinamills.com")
        assert result == "https://shop.purinamills.com/products/horse-feed"

    def test_empty_url(self):
        """Should return empty string for empty URL"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        result = searcher._abs_url("", "https://shop.purinamills.com")
        assert result == ""

    def test_origin_with_trailing_slash(self):
        """Should handle origin with trailing slash"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        href = "/products/feed"

        result = searcher._abs_url(href, "https://shop.purinamills.com/")
        assert result == "https://shop.purinamills.com/products/feed"


class TestSearchShopSite:
    """Test _search_shop_site method."""

    def test_successful_search(self):
        """Should return candidates from shop site search"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        # Mock HTML response
        html = """
        <html>
            <a href="/products/horse-feed">Premium Horse Feed</a>
            <a href="/products/dog-food">Premium Dog Food</a>
        </html>
        """

        mock_response = Mock()
        mock_response.text = html
        mock_get = Mock(return_value=mock_response)
        mock_log = Mock()

        candidates = searcher._search_shop_site("horse feed", mock_get, 30, mock_log)

        assert len(candidates) == 2
        assert candidates[0]["name"] == "Premium Horse Feed"
        assert "/products/horse-feed" in candidates[0]["url"]
        assert candidates[0]["source"] == "shop"

    def test_deduplicates_urls(self):
        """Should deduplicate same product with different query params"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        html = """
        <html>
            <a href="/products/horse-feed?_pos=1&_sid=abc">Horse Feed</a>
            <a href="/products/horse-feed?_pos=2&_sid=def">Horse Feed</a>
        </html>
        """

        mock_response = Mock()
        mock_response.text = html
        mock_get = Mock(return_value=mock_response)
        mock_log = Mock()

        candidates = searcher._search_shop_site("horse feed", mock_get, 30, mock_log)

        # Should only return one candidate (deduplicated)
        assert len(candidates) == 1

    def test_respects_max_candidates(self):
        """Should respect max_search_candidates limit"""
        config = TEST_CONFIG.copy()
        config["max_search_candidates"] = 2
        searcher = PurinamillsSearcher(config)

        html = """
        <html>
            <a href="/products/feed1">Feed 1</a>
            <a href="/products/feed2">Feed 2</a>
            <a href="/products/feed3">Feed 3</a>
            <a href="/products/feed4">Feed 4</a>
        </html>
        """

        mock_response = Mock()
        mock_response.text = html
        mock_get = Mock(return_value=mock_response)
        mock_log = Mock()

        candidates = searcher._search_shop_site("feed", mock_get, 30, mock_log)

        assert len(candidates) <= 2

    def test_handles_error(self):
        """Should return empty list on error"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        mock_get = Mock(side_effect=Exception("Network error"))
        mock_log = Mock()

        candidates = searcher._search_shop_site("feed", mock_get, 30, mock_log)

        assert candidates == []
        # Should log error
        assert any("failed" in str(call).lower() for call in mock_log.call_args_list)


class TestSearchWwwSite:
    """Test _search_www_site method."""

    @patch.object(PurinamillsSearcher, '_fetch_with_playwright')
    def test_successful_search(self, mock_fetch):
        """Should return candidates from www site search"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        html = """
        <html>
            <a href="/products/detail/horse-feed">Premium Horse Feed</a>
            <a href="/product/dog-food">Premium Dog Food</a>
        </html>
        """

        mock_fetch.return_value = html
        mock_get = Mock()
        mock_log = Mock()

        candidates = searcher._search_www_site("horse feed", mock_get, 30, mock_log)

        assert len(candidates) == 2
        assert candidates[0]["source"] == "www"

    @patch.object(PurinamillsSearcher, '_fetch_with_playwright')
    def test_handles_playwright_error(self, mock_fetch):
        """Should return empty list on Playwright error"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        mock_fetch.side_effect = Exception("Playwright error")
        mock_get = Mock()
        mock_log = Mock()

        candidates = searcher._search_www_site("feed", mock_get, 30, mock_log)

        assert candidates == []


class TestFetchWithPlaywright:
    """Test _fetch_with_playwright method."""

    @patch('src.search.sync_playwright')
    def test_successful_fetch(self, mock_playwright):
        """Should fetch HTML with Playwright"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        # Mock Playwright components
        mock_page = Mock()
        mock_page.content.return_value = "<html>Test</html>"

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock()
        mock_browser.new_context.return_value = mock_context

        mock_p = Mock()
        mock_p.chromium.launch.return_value = mock_browser

        mock_playwright.return_value.__enter__.return_value = mock_p

        html = searcher._fetch_with_playwright("https://example.com")

        assert html == "<html>Test</html>"
        mock_browser.close.assert_called_once()

    @patch('src.search.sync_playwright')
    def test_handles_timeout(self, mock_playwright):
        """Should return empty string on timeout"""
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        searcher = PurinamillsSearcher(TEST_CONFIG)

        mock_page = Mock()
        mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout")

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock()
        mock_browser.new_context.return_value = mock_context

        mock_p = Mock()
        mock_p.chromium.launch.return_value = mock_browser

        mock_playwright.return_value.__enter__.return_value = mock_p

        html = searcher._fetch_with_playwright("https://example.com")

        assert html == ""

    @patch('src.search.sync_playwright')
    def test_handles_exception(self, mock_playwright):
        """Should return empty string on exception"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        mock_playwright.return_value.__enter__.side_effect = Exception("Error")

        html = searcher._fetch_with_playwright("https://example.com")

        assert html == ""


class TestFindProductUrl:
    """Test find_product_url method (main search workflow)."""

    def test_no_upc(self):
        """Should return empty string if no UPC"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        mock_log = Mock()

        result = searcher.find_product_url("", Mock(), 30, mock_log, {})

        assert result == ""

    def test_no_product_data(self):
        """Should return empty string if no product data"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        mock_log = Mock()

        result = searcher.find_product_url("123456", Mock(), 30, mock_log, None)

        assert result == ""

    def test_no_product_names(self):
        """Should return empty string if no product names"""
        searcher = PurinamillsSearcher(TEST_CONFIG)
        mock_log = Mock()
        product_data = {"description_1": "", "upcitemdb_title": ""}

        result = searcher.find_product_url("123456", Mock(), 30, mock_log, product_data)

        assert result == ""

    @patch.object(PurinamillsSearcher, '_search_shop_site')
    def test_exact_match_found(self, mock_search):
        """Should return URL when exact match found"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        mock_search.return_value = [
            {
                "name": "Premium Horse Feed 50 LB",
                "url": "https://shop.purinamills.com/products/horse-feed",
                "kw": {"premium"},
                "source": "shop"
            }
        ]

        product_data = {"description_1": "Premium Horse Feed"}
        mock_log = Mock()

        result = searcher.find_product_url(
            "123456", Mock(), 30, mock_log, product_data
        )

        assert result == "https://shop.purinamills.com/products/horse-feed"

    @patch.object(PurinamillsSearcher, '_search_shop_site')
    def test_fuzzy_match_found(self, mock_search):
        """Should return URL when fuzzy match above threshold"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        mock_search.return_value = [
            {
                "name": "Premium Horse Formula",
                "url": "https://shop.purinamills.com/products/horse-formula",
                "kw": {"premium", "formula"},
                "source": "shop"
            }
        ]

        product_data = {"description_1": "Premium Horse Feed"}
        mock_log = Mock()

        result = searcher.find_product_url(
            "123456", Mock(), 30, mock_log, product_data
        )

        # Should find fuzzy match (both have "premium")
        assert "horse-formula" in result

    @patch.object(PurinamillsSearcher, '_search_shop_site')
    @patch.object(PurinamillsSearcher, '_search_www_site')
    def test_www_site_fallback(self, mock_www_search, mock_shop_search):
        """Should fall back to www site if shop site fails"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        # Shop site returns no matches
        mock_shop_search.return_value = []

        # WWW site returns match
        mock_www_search.return_value = [
            {
                "name": "Premium Horse Feed",
                "url": "https://www.purinamills.com/products/detail/horse-feed",
                "kw": {"premium"},
                "source": "www"
            }
        ]

        product_data = {"description_1": "Premium Horse Feed"}
        mock_log = Mock()

        result = searcher.find_product_url(
            "123456", Mock(), 30, mock_log, product_data
        )

        assert "www.purinamills.com" in result

    @patch.object(PurinamillsSearcher, '_search_shop_site')
    @patch.object(PurinamillsSearcher, '_search_www_site')
    def test_no_match_found(self, mock_www_search, mock_shop_search):
        """Should return empty string if no match found anywhere"""
        searcher = PurinamillsSearcher(TEST_CONFIG)

        mock_shop_search.return_value = []
        mock_www_search.return_value = []

        product_data = {"description_1": "Premium Horse Feed"}
        mock_log = Mock()

        result = searcher.find_product_url(
            "123456", Mock(), 30, mock_log, product_data
        )

        assert result == ""
