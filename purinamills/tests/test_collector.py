"""
Tests for collector module.
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collector import PurinamillsCollector, SITE_CONFIG


class TestCollectorInit:
    """Test collector initialization."""

    def test_init_creates_searcher_and_parser(self):
        """Should initialize with searcher and parser"""
        collector = PurinamillsCollector()

        assert collector.searcher is not None
        assert collector.parser is not None

    def test_site_config_values(self):
        """Should have correct site config"""
        assert SITE_CONFIG["site_key"] == "purinamills"
        assert "shop.purinamills.com" in SITE_CONFIG["shop_origin"]
        assert "www.purinamills.com" in SITE_CONFIG["www_origin"]


class TestFindProductUrl:
    """Test find_product_url method."""

    @patch('src.collector.PurinamillsSearcher')
    def test_delegates_to_searcher(self, mock_searcher_class):
        """Should delegate to searcher.find_product_url"""
        mock_searcher = Mock()
        mock_searcher.find_product_url.return_value = "https://example.com/product"
        mock_searcher_class.return_value = mock_searcher

        collector = PurinamillsCollector()
        collector.searcher = mock_searcher

        result = collector.find_product_url(
            upc="123456",
            http_get=Mock(),
            timeout=30,
            log=print,
            product_data={"description_1": "Test"}
        )

        assert result == "https://example.com/product"
        mock_searcher.find_product_url.assert_called_once()


class TestParsePage:
    """Test parse_page method."""

    @patch('src.collector.PurinamillsParser')
    def test_delegates_to_parser(self, mock_parser_class):
        """Should delegate to parser.parse_page"""
        mock_parser = Mock()
        mock_parser.parse_page.return_value = {"title": "Test Product"}
        mock_parser_class.return_value = mock_parser

        collector = PurinamillsCollector()
        collector.parser = mock_parser

        result = collector.parse_page("<html>Test</html>")

        assert result["title"] == "Test Product"
        mock_parser.parse_page.assert_called_once_with("<html>Test</html>")


class TestIntegration:
    """Integration tests for full workflow."""

    def test_collector_workflow(self):
        """Should support full collector workflow"""
        collector = PurinamillsCollector()

        # Verify all components initialized
        assert collector.searcher is not None
        assert collector.parser is not None

        # Verify config is accessible
        assert hasattr(collector, 'config')
        assert collector.config["site_key"] == "purinamills"
