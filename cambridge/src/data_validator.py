"""
Data Validation for Cambridge Collector

Validates that collected data contains minimum required fields.
Tracks missing fields for detailed failure reporting.
"""

from typing import Dict, List, Any, Tuple


class DataValidator:
    """Validates collected product data for completeness."""

    # Critical fields that MUST be present in public data
    PUBLIC_CRITICAL_FIELDS = ["title"]

    # Important fields that should be present in public data
    PUBLIC_IMPORTANT_FIELDS = ["description", "hero_image", "gallery_images"]

    # Important fields that should be present in portal data (per color)
    PORTAL_IMPORTANT_FIELDS = ["gallery_images", "cost", "model_number"]

    @staticmethod
    def validate_public_data(public_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate public website data.

        Args:
            public_data: Public website data dictionary

        Returns:
            Tuple of (is_valid, missing_critical_fields, missing_important_fields)
        """
        if not public_data:
            return (False, DataValidator.PUBLIC_CRITICAL_FIELDS[:], DataValidator.PUBLIC_IMPORTANT_FIELDS[:])

        missing_critical = []
        missing_important = []

        # Check critical fields
        for field in DataValidator.PUBLIC_CRITICAL_FIELDS:
            value = public_data.get(field)
            if not value or (isinstance(value, (list, str)) and len(value) == 0):
                missing_critical.append(field)

        # Check important fields
        for field in DataValidator.PUBLIC_IMPORTANT_FIELDS:
            value = public_data.get(field)
            if not value or (isinstance(value, (list, str)) and len(value) == 0):
                missing_important.append(field)

        # Valid if no critical fields are missing
        is_valid = len(missing_critical) == 0

        return (is_valid, missing_critical, missing_important)

    @staticmethod
    def validate_portal_data(portal_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate portal data.

        Args:
            portal_data: Portal data dictionary

        Returns:
            Tuple of (has_any_data, missing_important_fields)
        """
        if not portal_data:
            return (False, DataValidator.PORTAL_IMPORTANT_FIELDS[:])

        missing_important = []

        # Check important fields
        for field in DataValidator.PORTAL_IMPORTANT_FIELDS:
            value = portal_data.get(field)
            if not value or (isinstance(value, (list, str)) and len(value) == 0):
                missing_important.append(field)

        # Portal data is optional but nice to have
        has_any_data = len(portal_data) > 0

        return (has_any_data, missing_important)

    @staticmethod
    def get_public_data_summary(public_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of what public data was collected.

        Args:
            public_data: Public website data

        Returns:
            Summary dictionary
        """
        if not public_data:
            return {
                "has_title": False,
                "has_description": False,
                "has_hero_image": False,
                "gallery_image_count": 0,
                "has_specifications": False,
                "has_collection": False,
                "color_count": 0
            }

        gallery_images = public_data.get("gallery_images", [])
        colors = public_data.get("colors", [])

        return {
            "has_title": bool(public_data.get("title")),
            "has_description": bool(public_data.get("description")),
            "has_hero_image": bool(public_data.get("hero_image")),
            "gallery_image_count": len(gallery_images) if isinstance(gallery_images, list) else 0,
            "has_specifications": bool(public_data.get("specifications")),
            "has_collection": bool(public_data.get("collection")),
            "color_count": len(colors) if isinstance(colors, list) else 0
        }

    @staticmethod
    def get_portal_data_summary(portal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of what portal data was collected.

        Args:
            portal_data: Portal data dictionary

        Returns:
            Summary dictionary
        """
        if not portal_data:
            return {
                "has_gallery_images": False,
                "gallery_image_count": 0,
                "has_cost": False,
                "has_model_number": False,
                "has_weight": False
            }

        gallery_images = portal_data.get("gallery_images", [])

        return {
            "has_gallery_images": bool(gallery_images),
            "gallery_image_count": len(gallery_images) if isinstance(gallery_images, list) else 0,
            "has_cost": bool(portal_data.get("cost")),
            "has_model_number": bool(portal_data.get("model_number")),
            "has_weight": bool(portal_data.get("weight"))
        }
