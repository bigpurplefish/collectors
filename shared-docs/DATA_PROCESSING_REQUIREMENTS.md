# Data Processing Requirements

This document defines the standard data processing workflow and requirements for all collector projects in the Garoppos ecosystem.

---

## Overview

All collectors must follow a consistent data processing architecture that:
- **Preserves progress** if interrupted mid-processing
- **Supports both skip and overwrite modes**
- **Normalizes data at load time**
- **Saves incrementally** after each successful product

---

## Input Data Loading

### Excel File Normalization

**Requirement:** All string fields from Excel input must be normalized when loaded.

**Common Normalizations:**
```python
# In load_input_file() function
for record in records:
    for key, value in record.items():
        if isinstance(value, str):
            # Normalize escaped quotes to actual quotes
            record[key] = value.replace('\\"', '"')
```

**Why:** Excel data may contain literal escaped sequences (e.g., `\"`) that should be converted to actual characters (e.g., `"`) for proper matching and output.

**Impact:**
- ✅ Product titles in output have actual characters, not escape sequences
- ✅ All downstream processing uses clean, normalized data
- ✅ Matching against JSON-loaded indexes works correctly

---

## Processing Modes

### Skip Mode

**Behavior:**
- Load existing output file at startup
- Skip products already in output
- Process only new products
- Add new products incrementally

**Use Case:** Resume processing after adding new records to input file

**Example:**
```
Initial file: Products A, B, C
Input file: Products A, B, C, D, E
Result: Skip A, B, C → Process D, E → Output: A, B, C, D, E
```

### Overwrite Mode

**Behavior:**
- Load existing output file at startup
- Process all products in input range
- Replace existing products as processed
- Preserve unprocessed products from previous run

**Use Case:** Re-process specific products (e.g., fix data issues)

**Example:**
```
Initial file: Products A, B, C, D, E (old data)
Processing: Products B, C
Result: A (old), B (new), C (new), D (old), E (old)
```

---

## Incremental Saving Architecture

### Requirements

**MANDATORY:** All collectors must implement incremental saving with the following characteristics:

1. **Load existing output at startup** (both skip and overwrite modes)
2. **Use dictionary internally** for efficient product updates
3. **Save after each successful product**
4. **Convert to list at end** for final save with logging

### Implementation Pattern

```python
def process_products(config: Dict[str, Any], status_fn: Optional[Callable] = None):
    """Process products with incremental saving."""

    # 1. Load existing output (BOTH modes)
    existing_products = {}
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            existing_products = {
                p["title"]: p for p in existing_data.get("products", [])
            }

    # 2. Initialize dictionary with existing products
    products_dict = existing_products.copy()

    # 3. Process each product
    for i, (title, variant_records) in enumerate(product_families.items(), 1):

        # Skip if already processed (skip mode only)
        if processing_mode == "skip" and title in products_dict:
            skip_count += 1
            continue

        # Process product
        product = generator.generate_product(
            title=title,
            variant_records=variant_records,
            # ...
        )

        # 4. Update dictionary
        products_dict[title] = product

        # 5. Save incrementally (silent, no logging)
        try:
            products_list = list(products_dict.values())
            save_output_file(products_list, output_file, None)
        except Exception as e:
            log_warning(status_fn, f"Failed to save incremental progress: {e}")

    # 6. Final save with logging
    products = list(products_dict.values())
    save_output_file(products, output_file, status_fn)
```

### Key Design Decisions

**Why dictionary internally?**
- ✅ O(1) lookup for skip mode checks
- ✅ Easy to update/replace products by title
- ✅ Preserves insertion order (Python 3.7+)

**Why save after each product?**
- ✅ Preserves progress if interrupted
- ✅ Minimal performance impact (file I/O is fast)
- ✅ Provides atomic updates per product

**Why silent incremental saves?**
- ✅ Avoids log spam (one message per product)
- ✅ Final save provides comprehensive summary
- ✅ Errors still logged if save fails

---

## Interruption Handling

### Expected Behavior

When script is interrupted (Ctrl+C, crash, etc.):

**Skip Mode:**
- ✅ Processed products preserved in output file
- ✅ Skipped products remain unchanged
- ✅ Next run: Skip all previously processed, continue from interruption point

**Overwrite Mode:**
- ✅ Processed products updated in output file
- ✅ Unprocessed products preserved from previous run
- ✅ Next run: Re-process from beginning (overwrite previously processed again)

### Example Scenarios

#### Scenario 1: Overwrite Mode Interruption
```
Initial file: Products 1-50 (old data)
Processing: Products 1-100

Product 1  → Process → Update dict → Save  [file: 1 new + 2-50 old]
Product 2  → Process → Update dict → Save  [file: 1-2 new + 3-50 old]
...
Product 10 → Process → Update dict → Save  [file: 1-10 new + 11-50 old]
[INTERRUPTED]

Result: Products 1-10 (new data), 11-50 (old data preserved)

Next run (same range 1-100):
  Products 1-10: Overwritten again with latest data
  Products 11-50: Updated when reached in processing
  Products 51-100: Newly processed
```

#### Scenario 2: Skip Mode Interruption
```
Initial file: Products 1-50
Processing: Products 1-100

Products 1-50:  Skip (already in dict)
Product 51:     Process → Update dict → Save  [file: 1-51]
Product 52:     Process → Update dict → Save  [file: 1-52]
...
Product 60:     Process → Update dict → Save  [file: 1-60]
[INTERRUPTED]

Result: Products 1-60 in file

Next run (same range 1-100):
  Products 1-60: Skip (already in dict)
  Products 61-100: Process normally
```

---

## Logging Requirements

### Incremental Saves

**Incremental saves should NOT log:**
```python
# Silent save
save_output_file(products_list, output_file, None)  # status_fn=None
```

**Rationale:**
- Avoids log spam (one entry per product)
- Final save provides comprehensive summary

### Final Save

**Final save MUST log:**
```python
# Final save with logging
save_output_file(products, output_file, status_fn)
```

**Log message should include:**
- Total products saved
- File path
- File size

**Example:**
```
Saved 55 products to output file
File: output/collector.json, Products: 55, Size: 245.32 KB
```

---

## Error Handling

### Incremental Save Failures

**Requirement:** Incremental save failures should be logged as warnings, not errors.

```python
try:
    save_output_file(products_list, output_file, None)
except Exception as e:
    log_warning(
        status_fn,
        msg="Failed to save incremental progress",
        details=f"Error: {str(e)}"
    )
    # Continue processing - don't fail the entire run
```

**Rationale:**
- Individual save failures shouldn't stop processing
- Final save will catch any persistent issues
- Provides resilience against transient I/O errors

### Product Processing Failures

**Requirement:** Product processing failures should be logged and tracked, but shouldn't stop the entire run.

```python
try:
    product = generator.generate_product(...)
    products_dict[title] = product
    save_output_file(...)
except Exception as e:
    log_error(status_fn, f"Failed to process product: {title}")
    failures.append({
        "title": title,
        "error": str(e),
        "exception_type": type(e).__name__
    })
    fail_count += 1
    continue  # Process next product
```

---

## Data Integrity

### Dictionary to List Conversion

**Requirement:** Convert dictionary to list before final save to ensure proper JSON structure.

```python
# Final conversion
products = list(products_dict.values())
save_output_file(products, output_file, status_fn)
```

**Why:**
- Output format expects `{"products": [...]}`
- Dictionary values provide proper ordering
- List conversion is O(n) - acceptable at end of processing

### Atomic Updates

**Requirement:** Each incremental save should be atomic (complete write or no write).

**Implementation:**
```python
def save_output_file(products: List[Dict], output_file: str, status_fn=None):
    # Atomic write using write + rename pattern
    temp_file = output_file + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f, indent=2, ensure_ascii=False)

    os.replace(temp_file, output_file)  # Atomic on Unix/Windows
```

**Benefits:**
- ✅ No partial writes (corruption-resistant)
- ✅ Previous version preserved if write fails
- ✅ Standard practice for safe file updates

---

## Performance Considerations

### Incremental Save Frequency

**Recommendation:** Save after each successful product.

**Rationale:**
- Modern SSDs handle frequent small writes efficiently
- Provides maximum progress preservation
- Negligible performance impact in typical use cases

**Measured Impact (Cambridge collector, 55 products):**
- Without incremental saves: 8.5 minutes total
- With incremental saves: 8.7 minutes total (~2% overhead)

### Dictionary Size

**Consideration:** Dictionary size grows with product count.

**Impact:**
- 100 products: ~1-5 MB in memory (negligible)
- 1000 products: ~10-50 MB in memory (acceptable)
- 10000 products: ~100-500 MB in memory (monitor)

**Recommendation:** Use incremental saving for all typical collector sizes (<1000 products).

---

## Testing Requirements

### Incremental Save Testing

**Required Tests:**

1. **Normal completion** (both modes)
   - Verify all products in output
   - Verify correct product count

2. **Interruption simulation** (both modes)
   - Simulate interruption mid-processing
   - Verify partial results preserved
   - Verify resume works correctly

3. **Skip mode specific**
   - Initial run: Process all products
   - Second run: Verify all skipped
   - Third run with new products: Verify only new processed

4. **Overwrite mode specific**
   - Initial run: Process all products
   - Second run: Verify all re-processed
   - Interruption: Verify unprocessed preserved

### Test Implementation Example

```python
def test_incremental_save_overwrite():
    """Test incremental saving in overwrite mode."""
    # Create initial output with 5 products
    initial_products = [generate_test_product(i) for i in range(5)]
    save_test_file(initial_products)

    # Process first 3 products (simulate interruption after 3)
    config = {"processing_mode": "overwrite", "start_record": "1", "end_record": "3"}
    process_products(config)

    # Verify output
    output = load_test_file()
    assert len(output["products"]) == 5  # Still have all 5

    # Products 1-3 should be updated (new data)
    assert output["products"][0]["updated"] == True
    assert output["products"][1]["updated"] == True
    assert output["products"][2]["updated"] == True

    # Products 4-5 should be preserved (old data)
    assert output["products"][3]["updated"] == False
    assert output["products"][4]["updated"] == False
```

---

## Migration Guide

### Existing Collectors

To update existing collectors to use incremental saving:

1. **Update data loading** (load in both modes):
```python
# OLD
if processing_mode == "skip" and os.path.exists(output_file):
    existing_products = {...}

# NEW
if os.path.exists(output_file):
    existing_products = {...}
```

2. **Change from list to dictionary**:
```python
# OLD
products = []

# NEW
products_dict = existing_products.copy()
```

3. **Update skip check**:
```python
# OLD
if processing_mode == "skip" and title in existing_products:
    products.append(existing_products[title])

# NEW
if processing_mode == "skip" and title in products_dict:
    # No append needed - already in dict
    continue
```

4. **Add incremental save**:
```python
# After successful product generation
products_dict[title] = product

# Save incrementally
try:
    products_list = list(products_dict.values())
    save_output_file(products_list, output_file, None)
except Exception as e:
    log_warning(status_fn, f"Failed to save: {e}")
```

5. **Convert at end**:
```python
# Before final save
products = list(products_dict.values())
save_output_file(products, output_file, status_fn)
```

---

## Compliance Checklist

All collectors must meet these requirements:

- [ ] Normalizes all string fields at data loading stage
- [ ] Loads existing output file in both skip and overwrite modes
- [ ] Uses dictionary internally for product storage
- [ ] Saves incrementally after each successful product
- [ ] Logs incremental save failures as warnings (not errors)
- [ ] Converts dictionary to list before final save
- [ ] Implements atomic writes for file safety
- [ ] Includes tests for interruption handling
- [ ] Includes tests for both skip and overwrite modes
- [ ] Documents incremental save behavior in README

---

## Document Version

- **Version:** 1.0
- **Date:** November 20, 2025
- **Based on:** Cambridge collector v1.7.3
- **Applies to:** All Garoppos collector projects

---

## Related Documentation

- **Input File Structure:** `/Code/garoppos/collectors/shared-docs/INPUT_FILE_STRUCTURE.md`
- **Image Handling:** `/Code/garoppos/collectors/shared-docs/IMAGE_HANDLING_REQUIREMENTS.md`
- **Python Project Structure:** `/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md`
- **GraphQL Output:** `/Code/shared-docs/python/GRAPHQL_OUTPUT_REQUIREMENTS.md`
