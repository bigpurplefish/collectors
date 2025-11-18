#!/usr/bin/env python3
"""
Tests for Cambridge Data Validator

Tests validation of public and portal data to ensure
missing critical fields are detected.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_validator import DataValidator


class TestDataValidator(unittest.TestCase):
    """Test data validation functionality."""

    def test_validate_public_data_with_all_fields(self):
        """Test validation with complete public data."""
        public_data = {
            "title": "Test Product",
            "description": "Test description",
            "hero_image": "https://example.com/hero.jpg",
            "gallery_images": ["https://example.com/1.jpg", "https://example.com/2.jpg"],
            "specifications": "Test specs",
            "collection": "Test Collection",
            "colors": ["Red", "Blue"]
        }

        is_valid, missing_critical, missing_important = DataValidator.validate_public_data(public_data)

        self.assertTrue(is_valid)
        self.assertEqual(len(missing_critical), 0)
        self.assertEqual(len(missing_important), 0)

    def test_validate_public_data_missing_critical(self):
        """Test validation when critical fields are missing."""
        public_data = {
            "description": "Test description",
            "hero_image": "https://example.com/hero.jpg"
        }

        is_valid, missing_critical, missing_important = DataValidator.validate_public_data(public_data)

        self.assertFalse(is_valid)
        self.assertIn("title", missing_critical)

    def test_validate_public_data_missing_important(self):
        """Test validation when important fields are missing."""
        public_data = {
            "title": "Test Product",
            # Missing description, hero_image, gallery_images
        }

        is_valid, missing_critical, missing_important = DataValidator.validate_public_data(public_data)

        self.assertTrue(is_valid)  # Still valid because title is present
        self.assertIn("description", missing_important)
        self.assertIn("hero_image", missing_important)
        self.assertIn("gallery_images", missing_important)

    def test_validate_public_data_empty(self):
        """Test validation with empty public data."""
        public_data = {}

        is_valid, missing_critical, missing_important = DataValidator.validate_public_data(public_data)

        self.assertFalse(is_valid)
        self.assertGreater(len(missing_critical), 0)
        self.assertGreater(len(missing_important), 0)

    def test_validate_public_data_none(self):
        """Test validation with None public data."""
        is_valid, missing_critical, missing_important = DataValidator.validate_public_data(None)

        self.assertFalse(is_valid)
        self.assertGreater(len(missing_critical), 0)

    def test_validate_portal_data_with_all_fields(self):
        """Test validation with complete portal data."""
        portal_data = {
            "gallery_images": ["https://example.com/1.jpg"],
            "cost": "19.99",
            "model_number": "TEST-123",
            "weight": "50 lb"
        }

        has_data, missing_important = DataValidator.validate_portal_data(portal_data)

        self.assertTrue(has_data)
        self.assertEqual(len(missing_important), 0)

    def test_validate_portal_data_missing_fields(self):
        """Test validation when portal fields are missing."""
        portal_data = {
            "gallery_images": ["https://example.com/1.jpg"]
            # Missing cost, model_number
        }

        has_data, missing_important = DataValidator.validate_portal_data(portal_data)

        self.assertTrue(has_data)  # Has some data
        self.assertIn("cost", missing_important)
        self.assertIn("model_number", missing_important)

    def test_validate_portal_data_empty(self):
        """Test validation with empty portal data."""
        portal_data = {}

        has_data, missing_important = DataValidator.validate_portal_data(portal_data)

        self.assertFalse(has_data)
        self.assertGreater(len(missing_important), 0)

    def test_validate_portal_data_none(self):
        """Test validation with None portal data."""
        has_data, missing_important = DataValidator.validate_portal_data(None)

        self.assertFalse(has_data)
        self.assertGreater(len(missing_important), 0)

    def test_get_public_data_summary_complete(self):
        """Test summary generation for complete public data."""
        public_data = {
            "title": "Test Product",
            "description": "Test description",
            "hero_image": "https://example.com/hero.jpg",
            "gallery_images": ["https://example.com/1.jpg", "https://example.com/2.jpg"],
            "specifications": "Test specs",
            "collection": "Test Collection",
            "colors": ["Red", "Blue"]
        }

        summary = DataValidator.get_public_data_summary(public_data)

        self.assertTrue(summary["has_title"])
        self.assertTrue(summary["has_description"])
        self.assertTrue(summary["has_hero_image"])
        self.assertEqual(summary["gallery_image_count"], 2)
        self.assertTrue(summary["has_specifications"])
        self.assertTrue(summary["has_collection"])
        self.assertEqual(summary["color_count"], 2)

    def test_get_public_data_summary_empty(self):
        """Test summary generation for empty public data."""
        public_data = {}

        summary = DataValidator.get_public_data_summary(public_data)

        self.assertFalse(summary["has_title"])
        self.assertFalse(summary["has_description"])
        self.assertFalse(summary["has_hero_image"])
        self.assertEqual(summary["gallery_image_count"], 0)

    def test_get_portal_data_summary_complete(self):
        """Test summary generation for complete portal data."""
        portal_data = {
            "gallery_images": ["https://example.com/1.jpg", "https://example.com/2.jpg"],
            "cost": "19.99",
            "model_number": "TEST-123",
            "weight": "50 lb"
        }

        summary = DataValidator.get_portal_data_summary(portal_data)

        self.assertTrue(summary["has_gallery_images"])
        self.assertEqual(summary["gallery_image_count"], 2)
        self.assertTrue(summary["has_cost"])
        self.assertTrue(summary["has_model_number"])
        self.assertTrue(summary["has_weight"])

    def test_get_portal_data_summary_empty(self):
        """Test summary generation for empty portal data."""
        portal_data = {}

        summary = DataValidator.get_portal_data_summary(portal_data)

        self.assertFalse(summary["has_gallery_images"])
        self.assertEqual(summary["gallery_image_count"], 0)
        self.assertFalse(summary["has_cost"])
        self.assertFalse(summary["has_model_number"])


if __name__ == "__main__":
    unittest.main()
