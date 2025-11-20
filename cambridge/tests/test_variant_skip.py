#!/usr/bin/env python3
"""
Test Variant-Level Skip Mode

Tests the new variant-level skip logic that allows adding new colors
to existing products without re-processing variants that already have portal data.
"""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.processor import extract_existing_variants_by_color, variant_has_portal_data


def test_extract_variants_by_color():
    """Test extracting variants grouped by color."""
    print("")
    print("=" * 80)
    print("TEST: Extract Variants by Color")
    print("=" * 80)
    print("")

    # Create test product with multiple variants
    product = {
        "title": "Test Product",
        "variants": [
            {"option1": "Red", "option2": "Piece", "sku": "TEST-RED-P", "price": "10.00", "cost": "5.00"},
            {"option1": "Red", "option2": "Sq Ft", "sku": "TEST-RED-SF", "price": "20.00", "cost": "10.00"},
            {"option1": "Blue", "option2": "Piece", "sku": "TEST-BLUE-P", "price": "15.00", "cost": "7.50"},
            {"option1": "Green", "option2": "Piece", "sku": "TEST-GREEN-P", "price": "12.00", "cost": "6.00"},
        ]
    }

    # Extract variants by color
    variants_by_color = extract_existing_variants_by_color(product)

    # Verify results
    assert len(variants_by_color) == 3, f"Expected 3 colors, got {len(variants_by_color)}"
    assert "Red" in variants_by_color, "Red should be in variants_by_color"
    assert "Blue" in variants_by_color, "Blue should be in variants_by_color"
    assert "Green" in variants_by_color, "Green should be in variants_by_color"

    assert len(variants_by_color["Red"]) == 2, f"Expected 2 Red variants, got {len(variants_by_color['Red'])}"
    assert len(variants_by_color["Blue"]) == 1, f"Expected 1 Blue variant, got {len(variants_by_color['Blue'])}"
    assert len(variants_by_color["Green"]) == 1, f"Expected 1 Green variant, got {len(variants_by_color['Green'])}"

    print("✓ Extracted variants correctly:")
    for color, variants in variants_by_color.items():
        print(f"  {color}: {len(variants)} variant(s)")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Variants extracted correctly by color")
    print("=" * 80)
    print("")

    return True


def test_variant_has_portal_data():
    """Test checking if variants have portal data."""
    print("")
    print("=" * 80)
    print("TEST: Check Variant Has Portal Data")
    print("=" * 80)
    print("")

    # Test 1: Variant with complete portal data
    complete_variants = [
        {"option1": "Red", "sku": "TEST-RED", "price": "10.00", "cost": "5.00"}
    ]
    assert variant_has_portal_data(complete_variants) == True, "Should return True for complete data"
    print("✓ Test 1: Complete portal data detected")

    # Test 2: Variant missing SKU
    missing_sku = [
        {"option1": "Blue", "price": "10.00", "cost": "5.00"}
    ]
    assert variant_has_portal_data(missing_sku) == False, "Should return False when SKU missing"
    print("✓ Test 2: Missing SKU detected")

    # Test 3: Variant missing price
    missing_price = [
        {"option1": "Green", "sku": "TEST-GREEN", "cost": "5.00"}
    ]
    assert variant_has_portal_data(missing_price) == False, "Should return False when price missing"
    print("✓ Test 3: Missing price detected")

    # Test 4: Variant missing cost
    missing_cost = [
        {"option1": "Yellow", "sku": "TEST-YELLOW", "price": "10.00"}
    ]
    assert variant_has_portal_data(missing_cost) == False, "Should return False when cost missing"
    print("✓ Test 4: Missing cost detected")

    # Test 5: Multiple variants, one complete
    mixed_variants = [
        {"option1": "Red", "price": "10.00"},  # Missing SKU and cost
        {"option1": "Red", "sku": "TEST-RED", "price": "10.00", "cost": "5.00"}  # Complete
    ]
    assert variant_has_portal_data(mixed_variants) == True, "Should return True if at least one variant is complete"
    print("✓ Test 5: Mixed variants - at least one complete")

    # Test 6: Empty list
    assert variant_has_portal_data([]) == False, "Should return False for empty list"
    print("✓ Test 6: Empty list handled correctly")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Portal data detection working correctly")
    print("=" * 80)
    print("")

    return True


def test_variant_skip_logic():
    """Test the variant-level skip logic simulation."""
    print("")
    print("=" * 80)
    print("TEST: Variant-Level Skip Logic Simulation")
    print("=" * 80)
    print("")

    # Simulate existing product with 2 colors (Red and Blue)
    existing_product = {
        "title": "Test Product",
        "variants": [
            {"option1": "Red", "option2": "Piece", "sku": "TEST-RED-P", "price": "10.00", "cost": "5.00"},
            {"option1": "Blue", "option2": "Piece", "sku": "TEST-BLUE-P", "price": "15.00", "cost": "7.50"},
        ]
    }

    # Simulate input records that include Red (existing), Blue (existing), and Green (new)
    input_colors = {"Red", "Blue", "Green"}

    # Extract existing variants
    variants_by_color = extract_existing_variants_by_color(existing_product)

    # Determine which colors to skip vs process
    colors_to_skip = set()
    colors_to_process = set()

    for color in input_colors:
        if color in variants_by_color:
            # Check if this color has portal data
            if variant_has_portal_data(variants_by_color[color]):
                colors_to_skip.add(color)
            else:
                colors_to_process.add(color)
        else:
            # New color, needs processing
            colors_to_process.add(color)

    # Verify results
    assert colors_to_skip == {"Red", "Blue"}, f"Expected to skip Red and Blue, got {colors_to_skip}"
    assert colors_to_process == {"Green"}, f"Expected to process Green, got {colors_to_process}"

    print("✓ Input colors: Red, Blue, Green")
    print(f"✓ Colors to skip (have portal data): {', '.join(sorted(colors_to_skip))}")
    print(f"✓ Colors to process (new/missing data): {', '.join(sorted(colors_to_process))}")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Variant skip logic working correctly")
    print("=" * 80)
    print("")

    return True


if __name__ == "__main__":
    try:
        print("")
        print("Running Variant-Level Skip Mode Tests")
        print("")

        test_extract_variants_by_color()
        test_variant_has_portal_data()
        test_variant_skip_logic()

        print("")
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("Extract Variants by Color: ✓ PASSED")
        print("Check Variant Has Portal Data: ✓ PASSED")
        print("Variant Skip Logic Simulation: ✓ PASSED")
        print("=" * 80)
        print("")

    except AssertionError as e:
        print("")
        print("=" * 80)
        print("✗ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print("")
        sys.exit(1)
    except Exception as e:
        print("")
        print("=" * 80)
        print("✗ TEST ERROR")
        print("=" * 80)
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("")
        sys.exit(1)
