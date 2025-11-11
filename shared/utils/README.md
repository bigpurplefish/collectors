# Shared Utility Tools

Reusable utilities for all Garoppos collectors.

## Available Utilities

### SKU Generator (`sku_generator.py`)

Thread-safe SKU generation utility that ensures unique SKU assignment across all collectors.

**Purpose**: Generate unique 5-digit SKUs starting from 50000 for products that don't have SKUs in their source data.

**Key Features**:
- ✅ Cross-collector uniqueness (shared registry)
- ✅ Thread-safe for concurrent access
- ✅ Persistent registry (survives crashes/restarts)
- ✅ Automatic registry corruption recovery
- ✅ Custom starting SKU support

**Usage**:
```python
from shared.utils.sku_generator import SKUGenerator

# Initialize generator (uses default shared registry)
generator = SKUGenerator()

# Generate unique SKUs
sku1 = generator.generate_unique_sku()  # "50000"
sku2 = generator.generate_unique_sku()  # "50001"
sku3 = generator.generate_unique_sku()  # "50002"

# Mark existing SKUs as used (import from other systems)
generator.mark_sku_used("12345")

# Check if SKU is already used
if generator.is_sku_used("12345"):
    print("SKU already exists")

# Get registry statistics
stats = generator.get_stats()
print(f"Total SKUs used: {stats['total_skus_used']}")
print(f"Next available SKU: {stats['next_auto_sku']}")
```

**Registry Location**: `/collectors/cache/sku_registry.json` (parent-level cache shared across all collectors)

**Testing**: Run comprehensive test suite with:
```bash
cd /path/to/collectors/shared
python3 tests/test_sku_generator.py
```

---

### Batcher (`batcher.py`)

Batch processing utility for handling large datasets.

**Purpose**: Split large product collections into manageable batches for API uploads.

---

### JSON to Excel Converter (`json_to_excel_converter.py`)

Converts JSON product data to Excel format.

**Purpose**: Export Shopify product data to Excel spreadsheets for review and editing.

---

## Adding New Utilities

To add a new shared utility:

1. Create the utility file in `shared/utils/`
2. Add comprehensive docstrings and type hints
3. Create unit tests in `shared/tests/test_<utility_name>.py`
4. Update `shared/utils/__init__.py` to include the new utility
5. Document the utility in this README
6. Run tests to ensure everything works

Example:
```python
# shared/utils/my_utility.py
def my_function():
    """
    Does something useful.

    Returns:
        str: A result
    """
    return "result"
```

---

## Best Practices

1. **Thread Safety**: All utilities should be thread-safe if they maintain state
2. **Error Handling**: Gracefully handle errors and provide meaningful messages
3. **Testing**: Write comprehensive unit tests for all functionality
4. **Documentation**: Include docstrings, type hints, and usage examples
5. **Shared State**: Use persistent files (in `/collectors/cache/`) for cross-collector shared state

---

## Version History

- **2025-11-11**: Added SKU Generator utility with cross-collector uniqueness
- **2024**: Initial utilities (batcher, json_to_excel_converter)

---

## Support

For issues or questions about shared utilities, please create an issue in the project repository.
