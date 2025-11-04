#!/bin/bash
# Script to migrate a collector to standard Python structure

set -e  # Exit on error

COLLECTOR=$1

if [ -z "$COLLECTOR" ]; then
    echo "Usage: $0 <collector_name>"
    exit 1
fi

echo "Migrating $COLLECTOR..."

cd "$COLLECTOR"

# Create directories
mkdir -p src tests docs logs utils

# Move Python files to src
if ls *.py 1> /dev/null 2>&1; then
    for file in *.py; do
        if [ "$file" != "setup.py" ]; then
            git mv "$file" "src/$file"
        fi
    done
fi

# Move CLAUDE.md to docs if it exists
if [ -f "CLAUDE.md" ]; then
    git mv "CLAUDE.md" "docs/CLAUDE.md"
fi

# Move README.md to docs if it exists
if [ -f "README.md" ]; then
    git mv "README.md" "docs/README.md"
fi

# Create .gitkeep files
touch logs/.gitkeep tests/.gitkeep

# Ensure output directory exists and has .gitkeep
if [ ! -d "output" ]; then
    mkdir output
fi
touch output/.gitkeep

# Ensure input directory exists and has .gitkeep
if [ ! -d "input" ]; then
    mkdir input
fi
touch input/.gitkeep

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# Project-specific
/output/*
!/output/.gitkeep
config.json
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
/logs/*
!/logs/.gitkeep

# Testing
.pytest_cache/
.coverage
htmlcov/

# Claude
.claude/
EOF

# Update imports in all Python files in src/
find src -name "*.py" -type f -exec sed -i.bak 's|sys.path.insert(0, os.path.join(os.path.dirname(__file__), '"'"'..'"'"'))|sys.path.insert(0, os.path.join(os.path.dirname(__file__), '"'"'../..'"'"'))|g' {} \;
find src -name "*.py" -type f -exec sed -i.bak 's|from shared import|from shared.src import|g' {} \;
find src -name "*.py" -type f -exec sed -i.bak 's|from \.||g' {} \;
find src -name "*.py" -type f -exec sed -i.bak 's|import \.|import src.|g' {} \;

# Remove backup files
find src -name "*.bak" -delete

# Stage all changes
git add .

cd ..

echo "$COLLECTOR migration complete!"
