"""
Test weight parsing functionality
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.shopify_output import _parse_weight_from_size


def test_weight_parsing():
    """Test various size string formats"""

    test_cases = [
        # (input, expected_weight, expected_unit, expected_grams)
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
        ("EACH", None, None, 0),
        ("EA", None, None, 0),
        ("1 GAL", None, None, 0),
        ("", None, None, 0),
        (None, None, None, 0),
    ]

    print("Testing weight parsing functionality:\n")

    passed = 0
    failed = 0

    for input_val, expected_weight, expected_unit, expected_grams in test_cases:
        weight, unit, grams = _parse_weight_from_size(input_val if input_val else "")

        # Check if results match expected
        success = (weight == expected_weight and
                   unit == expected_unit and
                   grams == expected_grams)

        status = "✓" if success else "✗"

        if success:
            passed += 1
        else:
            failed += 1

        print(f"{status} Input: '{input_val}' -> weight={weight}, unit={unit}, grams={grams}")

        if not success:
            print(f"  Expected: weight={expected_weight}, unit={expected_unit}, grams={expected_grams}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    success = test_weight_parsing()
    sys.exit(0 if success else 1)
