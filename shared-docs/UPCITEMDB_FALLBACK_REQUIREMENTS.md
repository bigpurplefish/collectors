# UPCItemDB Fallback Requirements

**Version:** 1.0
**Last Updated:** 2025-11-05
**Applies To:** All Product Collectors

---

## Overview

When a product cannot be found on a manufacturer or retailer website, collectors should fall back to UPCItemDB data if available. This document defines the standard workflow, data mapping, and image quality requirements for UPCItemDB fallback functionality.

**Purpose:**
- Maximize product coverage by using UPCItemDB as fallback
- Ensure consistent data quality across all collectors
- Maintain image quality standards even for fallback data

---

## Table of Contents

1. [Fallback Decision Flow](#fallback-decision-flow)
2. [Data Requirements](#data-requirements)
3. [Image Selection Criteria](#image-selection-criteria)
4. [Field Mapping](#field-mapping)
5. [Content Restrictions](#content-restrictions)
6. [Error Handling](#error-handling)
7. [GUI Requirements](#gui-requirements)
8. [Implementation Example](#implementation-example)

---

## Fallback Decision Flow

When a product search returns no results:

```
Product Search Failed
    ↓
Check upcitemdb_status field
    ↓
┌─────────────────────────────────────┐
│ upcitemdb_status = "Lookup failed"? │
└─────────────────────────────────────┘
    │
    ├─→ YES: Skip record, log error
    │        Error: "Product not found and UPCItemDB lookup failed"
    │
    └─→ NO: Check if "Match found"
            ↓
        ┌─────────────────────────────────┐
        │ upcitemdb_status = "Match found"│
        └─────────────────────────────────┘
            │
            ├─→ YES: Use UPCItemDB fallback
            │        ↓
            │    1. Check for images
            │    2. Select best image
            │    3. Map data fields
            │    4. Generate product
            │
            └─→ NO: Skip record, log error
                     Error: "Product not found"
```

---

## Data Requirements

### Required Input Fields

UPCItemDB data must be present in the input file with these fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `upcitemdb_status` | string | Status of UPCItemDB lookup | `"Match found"` or `"Lookup failed"` |
| `description_1` | string | Primary product description | `"PURINA® AMPLIFY® HIGH-FAT HORSE SUPPLEMENT"` |
| `upcitemdb_description` | string | UPCItemDB product description | `"Purina Animal Nutrition Amplify Equine Supplements 50lb Bag"` |
| `upcitemdb_images` | array/string | List of image URLs | `["https://..."]` or `'["https://..."]'` |

**Note:** `upcitemdb_images` may be stored as:
- JSON array (if from JSON file)
- String representation of array (if from Excel file)

Both formats must be supported.

---

## Image Selection Criteria

### Quality Metrics

Use the following criteria to select the best image from UPCItemDB:

#### 1. **Download & Validate**
- Successfully download image
- Verify content type is `image/*`
- Handle HTTP errors (403, 404)

#### 2. **Placeholder Detection**
- Load known placeholder images for comparison
- Use perceptual hashing (pHash) to detect placeholders
- Reject images with Hamming distance ≤ threshold (default: 10)

#### 3. **Whitespace Cropping**
- Crop whitespace borders before evaluation
- Ensures dimensions reflect actual content

#### 4. **Sharpness Check (Laplacian Variance)**
- Calculate Laplacian variance score
- Reject images below threshold (default: 100)
- Higher scores indicate sharper images

#### 5. **Dimension Priority**
- Prefer larger images (width × height)
- Larger dimensions = better quality potential

#### 6. **Sharpness Tiebreaker**
- If dimensions equal, choose sharper image

### Selection Algorithm

```python
best_image = None
best_score = 0
best_dim = 0

for url in upcitemdb_images:
    img = download_image(url)
    if img is None or is_placeholder(img):
        continue

    cropped = crop_whitespace(img)
    sharpness = calculate_laplacian_score(cropped)

    if sharpness < LAPLACIAN_THRESHOLD:
        continue

    dimensions = cropped.width * cropped.height

    if dimensions > best_dim or (dimensions == best_dim and sharpness > best_score):
        best_image = cropped
        best_score = sharpness
        best_dim = dimensions
```

---

## Field Mapping

### Shopify Product Structure (GraphQL 2025-10)

When using UPCItemDB fallback, map data as follows:

| Shopify Field | Source | Example |
|---------------|--------|---------|
| `title` | `description_1` | Input file field |
| `descriptionHtml` | `upcitemdb_description` | Plain text from UPCItemDB |
| `vendor` | Manufacturer name | `"Purina"`, `"Kong"`, etc. |
| `media` | Selected best image | Single image after quality check |
| `variants` | Input data | Generated from input file variants |
| `status` | `"ACTIVE"` | Always active for new products |

### Excluded Fields

**DO NOT** populate these fields for UPCItemDB fallback:

- `features` (metafield) - Not available in UPCItemDB
- `nutritional_information` (metafield) - Not available in UPCItemDB
- `directions` (metafield) - Not available in UPCItemDB
- `documentation` (metafield) - Not available in UPCItemDB

**Why:** UPCItemDB provides only basic product information. Including empty metafields creates incomplete product data.

---

## Content Restrictions

### What to Include

✅ Basic product information:
- Title (from input file)
- Description (from UPCItemDB)
- Vendor/Manufacturer
- UPC code
- Variants (from input file)
- Best quality image

### What to Exclude

❌ Rich content metafields:
- Features & Benefits
- Nutritional Information
- Feeding Directions
- Documentation/PDFs
- Videos

**Rationale:** Only populate fields where high-quality data is available. UPCItemDB fallback creates minimal but accurate product data.

---

## Error Handling

### Error Scenarios and Messages

| Scenario | Error Message | Action |
|----------|---------------|--------|
| Product not found + UPCItemDB lookup failed | `"Product not found and UPCItemDB lookup failed"` | Skip record, add to error log |
| Product not found + No images in UPCItemDB | `"No UPCItemDB images available"` | Skip record, add to error log |
| Product not found + All images fail quality check | `"No suitable UPCItemDB images (failed quality check)"` | Skip record, add to error log |
| Product not found + No UPCItemDB status | `"Product not found"` | Skip record, add to error log |

### Error Logging

All failed records must be logged with:
- Original record data (all fields)
- `error_reason` field with descriptive message
- Written to Excel error log (`*_errors.xlsx`)

---

## GUI Requirements

### Laplacian Threshold Field

**Required GUI Field:**
- **Label:** "Laplacian Threshold"
- **Type:** IntVar + Spinbox
- **Default:** 100 (match upscaler config)
- **Range:** 0-500
- **Increment:** 10
- **Width:** 10 characters
- **Tooltip:** "Minimum image sharpness score for UPCItemDB fallback images.\n\nImages below this threshold will be rejected as low quality.\nDefault: 100\n\nHigher values = stricter quality requirements.\nLower values = accept more images (including slightly blurry ones)."

### Placeholder Images

**Required Files:**
- Copy `placeholder_images/` directory to project root
- Load placeholder images at startup
- Use for perceptual hash comparison

---

## Implementation Example

### Minimal Implementation

```python
# 1. Check for UPCItemDB fallback
if not product_url:
    upcitemdb_status = product.get('upcitemdb_status', '')

    if upcitemdb_status == "Lookup failed":
        # Skip and log
        failed_records.append({
            **product,
            'error_reason': "Product not found and UPCItemDB lookup failed"
        })
        continue

    elif upcitemdb_status == "Match found":
        # 2. Load placeholder images
        from shared.src.image_quality import (
            load_placeholder_images,
            select_best_image
        )
        placeholders = load_placeholder_images("placeholder_images/")

        # 3. Get and parse image URLs
        import ast
        image_urls_raw = product.get('upcitemdb_images', [])

        if isinstance(image_urls_raw, str):
            image_urls = ast.literal_eval(image_urls_raw)
        else:
            image_urls = image_urls_raw

        if not image_urls:
            failed_records.append({
                **product,
                'error_reason': "No UPCItemDB images available"
            })
            continue

        # 4. Select best image
        best_image, best_url = select_best_image(
            image_urls=image_urls,
            placeholders=placeholders,
            laplacian_threshold=laplacian_threshold,
            hamming_threshold=10,
            log=print
        )

        if not best_image:
            failed_records.append({
                **product,
                'error_reason': "No suitable UPCItemDB images (failed quality check)"
            })
            continue

        # 5. Save image
        image_filename = f"{upc}_upcitemdb.jpg"
        best_image.save(f"output/images/{image_filename}", "JPEG", quality=95)

        # 6. Create fallback product data
        parsed_data = {
            'title': product.get('description_1', ''),
            'description': product.get('upcitemdb_description', ''),
            'vendor': 'YourManufacturer',  # Replace with actual
            'gallery_images': [image_filename],
            'site_source': 'upcitemdb',
            'variants': [],
            'features_benefits': None,
            'nutrients': None,
            'feeding_directions': None,
            'documents': []
        }

        # 7. Generate Shopify product
        shopify_product = generate_shopify_product(
            parsed_data=parsed_data,
            input_data=product,
            variant_data=variants
        )
```

---

## Shared Library Structure

### Recommended Organization

```
collectors/
├── shared/
│   ├── __init__.py
│   └── src/
│       ├── __init__.py
│       ├── image_quality.py       # NEW: Image quality assessment
│       ├── text_utils.py          # Existing
│       ├── image_utils.py         # Existing
│       └── excel_utils.py         # Existing
├── placeholder_images/            # NEW: Shared placeholder images
│   └── *.jpg
└── shared-docs/
    ├── UPCITEMDB_FALLBACK_REQUIREMENTS.md  # This file
    └── ...
```

### Dependencies

Required packages in `requirements.txt`:

```txt
Pillow>=10.0.0          # Image processing
opencv-python>=4.8.0    # Laplacian variance calculation
numpy>=1.24.0           # Required by OpenCV
imagehash>=4.3.0        # Perceptual hashing
```

---

## Best Practices

### ✅ Do

- Use Context7 for latest library documentation
- Load placeholder images once at startup
- Log all fallback attempts (success and failure)
- Include original record data in error logs
- Use descriptive error messages
- Test with various image qualities
- Document Laplacian threshold in GUI tooltip

### ❌ Don't

- Populate empty metafields for UPCItemDB data
- Accept blurry images (respect Laplacian threshold)
- Skip placeholder detection
- Hardcode image URLs
- Forget to crop whitespace before dimension check
- Use UPCItemDB data when primary source is available

---

## Testing Checklist

- [ ] Product not found → UPCItemDB lookup failed: Properly skipped and logged
- [ ] Product not found → UPCItemDB match found: Fallback executed
- [ ] Placeholder images detected and rejected
- [ ] Blurry images rejected (below Laplacian threshold)
- [ ] Best image selected based on dimensions and sharpness
- [ ] Image saved with correct filename format
- [ ] Fallback product created with correct field mapping
- [ ] Rich content metafields excluded
- [ ] Error log contains all original fields
- [ ] GUI Laplacian threshold control works
- [ ] Excel file parsing handles string array format
- [ ] Failed records summary prints correctly

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-05 | Initial release - Based on Purinamills collector implementation |

---

## References

- [Shopify GraphQL Admin API 2025-10](https://shopify.dev/docs/api/admin-graphql)
- [GRAPHQL_OUTPUT_REQUIREMENTS.md](./GRAPHQL_OUTPUT_REQUIREMENTS.md)
- [GUI_DESIGN_REQUIREMENTS.md](../../shared-docs/python/GUI_DESIGN_REQUIREMENTS.md)
- [PROJECT_STRUCTURE_REQUIREMENTS.md](../../shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md)
