# Shared Utilities

This directory contains utilities shared across all collector projects.

## Available Tools

### batcher.py
Split, merge, group, and sort JSON files. Supports Excel ↔ JSON conversion.

**Usage:**
```bash
# Split into batches
python batcher.py split --input records.json --outdir ./batches --size 50 --id-field "item_#"

# Merge batches back
python batcher.py merge --original records.json --batches-dir ./augmented --output merged.json --id-field "item_#"

# GUI mode
python batcher.py
```

### json_to_excel_converter.py
Convert JSON files to Excel format with smart type handling.

**Usage:**
```bash
python json_to_excel_converter.py
```

## Dependencies

See requirements.txt in each collector project for dependencies needed to use these utilities.
