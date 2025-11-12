"""
Test weight parsing functionality
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.shopify_output import _parse_weight_from_size


import pytest


@pytest.mark.parametrize("input_val,expected_weight,expected_unit,expected_grams", [
    # Direct weight units
    ("50 LB", 50.0, "lb", 22680),
    ("50LB", 50.0, "lb", 22680),
    ("50 lb", 50.0, "lb", 22680),
    ("16 OZ", 16.0, "oz", 454),
    ("16OZ", 16.0, "oz", 454),
    ("2.5 KG", 2.5, "kg", 2500),
    ("2.5KG", 2.5, "kg", 2500),
    ("500 G", 500.0, "g", 500),
    ("500G", 500.0, "g", 500),
    ("50 LBS", 50.0, "lb", 22680),
    ("16 OUNCES", 16.0, "oz", 454),
    ("2 KILOGRAMS", 2.0, "kg", 2000),

    # Volume units (converted to weight)
    ("1 GALLON", 7.5, "lb", 3402),
    ("1 GAL", 7.5, "lb", 3402),
    ("2 GALLONS", 15.0, "lb", 6804),
    ("1 LITER", 1.65, "lb", 748),
    ("1 L", 1.65, "lb", 748),
    ("500 ML", 375.0, "g", 375),
    ("1 QUART", 1.875, "lb", 850),
    ("1 QT", 1.875, "lb", 850),
    ("1 PINT", 0.9375, "lb", 425),
    ("1 PT", 0.9375, "lb", 425),

    # Complex format: quantity - measurement unit
    ("3 - 0.17 OZ PACKETS", 0.51, "oz", 14),
    ("2 - 8 OZ PACKETS", 16.0, "oz", 454),
    ("5 - 0.5 LB BAGS", 2.5, "lb", 1134),
    ("10 - 100 G PACKETS", 1000.0, "g", 1000),

    # Non-weight units
    ("EACH", None, None, 0),
    ("EA", None, None, 0),
    ("", None, None, 0),
    (None, None, None, 0),
])
def test_weight_parsing(input_val, expected_weight, expected_unit, expected_grams):
    """Test various size string formats"""
    weight, unit, grams = _parse_weight_from_size(input_val if input_val else "")

    assert weight == expected_weight, f"Weight mismatch for '{input_val}'"
    assert unit == expected_unit, f"Unit mismatch for '{input_val}'"
    assert grams == expected_grams, f"Grams mismatch for '{input_val}'"


def test_weight_parsing_with_brackets():
    """Test parsing weight from upcitemdb_size format with brackets"""
    from src.utils.shopify_output import _parse_weight_from_size
    
    # Simulate cleaning brackets like we do in shopify_output.py
    upcitemdb_size = "[50 lbs]"
    size_cleaned = upcitemdb_size.strip('[]').strip()
    
    weight, unit, grams = _parse_weight_from_size(size_cleaned)
    
    assert weight == 50.0, f"Expected 50.0, got {weight}"
    assert unit == "lb", f"Expected 'lb', got {unit}"
    assert grams == 22680, f"Expected 22680, got {grams}"


def test_weight_extraction_from_title():
    """Test extracting weight from upcitemdb_title"""
    import re
    from src.utils.shopify_output import _parse_weight_from_size
    
    # Test the regex pattern used in fallback 2
    upcitemdb_title = "Purina Animal Nutrition Purina Goat Grower 16 DQ .0015 50lb PLT 50 lb"
    
    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*[-\s]?\s*(lb|lbs|oz|kg|g|gallon|gal|liter|l)\b',
                           upcitemdb_title, re.IGNORECASE)
    
    assert weight_match is not None, "Should find weight in title"
    
    weight_str = weight_match.group(1)
    unit_str = weight_match.group(2)
    size_from_title = f"{weight_str} {unit_str}"
    
    weight, unit, grams = _parse_weight_from_size(size_from_title)
    
    assert weight == 50.0, f"Expected 50.0, got {weight}"
    assert unit == "lb", f"Expected 'lb', got {unit}"
    assert grams == 22680, f"Expected 22680, got {grams}"
