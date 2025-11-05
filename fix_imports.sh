#!/bin/bash
# Fix broken imports from migration script

echo "Fixing import statements in all collectors..."

# Fix imports in all Python files in src/ directories
for collector in */src/*.py; do
    if [ -f "$collector" ]; then
        # Fix broken "from ." imports that got mangled
        # These should be "from src."
        sed -i.bak 's/^from \.$/from src./g' "$collector"
        sed -i.bak 's/^import \.$/import src./g' "$collector"
        
        # Fix lines like "catalog import" -> "from src.catalog import"  
        sed -i.bak 's/^catalog import /from src.catalog import /g' "$collector"
        sed -i.bak 's/^enricher import /from src.enricher import /g' "$collector"
        sed -i.bak 's/^parser import /from src.parser import /g' "$collector"
        sed -i.bak 's/^search import /from src.search import /g' "$collector"
        sed -i.bak 's/^image_processor import /from src.image_processor import /g' "$collector"
        sed -i.bak 's/^auth import /from src.auth import /g' "$collector"
        sed -i.bak 's/^variant_handler import /from src.variant_handler import /g' "$collector"
        sed -i.bak 's/^size_matching import /from src.size_matching import /g' "$collector"
        sed -i.bak 's/^text_matching import /from src.text_matching import /g' "$collector"
        
        # Remove backup files
        rm -f "${collector}.bak"
    fi
done

echo "✓ Fixed all import statements"
