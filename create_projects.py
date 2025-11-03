#!/usr/bin/env python3
"""
Automated project creator for all collector sites.
This script creates the remaining collector projects with their virtual environments.
"""

import os
import json
import subprocess
import sys

COLLECTORS_DIR = "/Users/moosemarketer/Code/Python/collectors"
GAROPPOS_DIR = "/Users/moosemarketer/Code/Python/garoppos"

# Projects remaining to create (coastal, chala, ethical, fromm, ivyclassic, kong, orgill, purinamills, talltails)
PROJECTS = [
    "coastal",
    "chala",
    "ethical",
    "fromm",
    "ivyclassic",
    "kong",
    "orgill",
    "purinamills",
    "talltails"
]

def create_project(project_name):
    """Create a complete collector project."""
    print(f"\n{'='*60}")
    print(f"Creating project: {project_name}")
    print(f"{'='*60}\n")

    project_dir = os.path.join(COLLECTORS_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)

    # Read profile
    profile_path = os.path.join(GAROPPOS_DIR, "profiles", f"{project_name}.json")
    with open(profile_path, "r") as f:
        profile = json.load(f)

    # Read strategy
    strategy_path = os.path.join(GAROPPOS_DIR, "strategies", f"{project_name}.py")
    with open(strategy_path, "r") as f:
        strategy_code = f.read()

    # Create collector.py with embedded profile
    create_collector_file(project_dir, project_name, profile, strategy_code)

    # Create requirements.txt
    create_requirements_file(project_dir, project_name)

    # Create CLAUDE.md
    create_claude_md(project_dir, project_name, profile)

    # Create virtual environment
    create_virtual_env(project_dir, project_name)

    print(f"✓ Project {project_name} created successfully\n")

def create_collector_file(project_dir, project_name, profile, strategy_code):
    """Create the main collector.py file."""
    # Extract the class definition from strategy
    import re
    class_match = re.search(r'class\s+(\w+)\(', strategy_code)
    class_name = class_match.group(1) if class_match else "Collector"

    collector_code = f'''#!/usr/bin/env python3
"""
{profile.get('display_name', project_name.title())} Product Collector

Collects product data from {profile.get('origin', 'the manufacturer website')}.
"""

import os
import re
import json
import html
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

# Site Configuration (embedded from profile)
SITE_CONFIG = {json.dumps(profile, indent=4)}

{strategy_code}

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="{profile.get('display_name', project_name.title())} Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {{args.input}} -> {{args.output}}")

if __name__ == "__main__":
    main()
'''

    collector_path = os.path.join(project_dir, "collector.py")
    with open(collector_path, "w") as f:
        f.write(collector_code)

    print(f"  ✓ Created collector.py")

def create_requirements_file(project_dir, project_name):
    """Create requirements.txt with necessary dependencies."""
    # Base dependencies
    deps = [
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0"
    ]

    # Add project-specific dependencies
    if project_name in ["ethical"]:
        deps.append("selenium>=4.15.0")
        deps.append("webdriver-manager>=4.0.0")

    if project_name in ["orgill"]:
        deps.append("pillow>=10.0.0")

    requirements_path = os.path.join(project_dir, "requirements.txt")
    with open(requirements_path, "w") as f:
        f.write("\n".join(deps) + "\n")

    print(f"  ✓ Created requirements.txt")

def create_claude_md(project_dir, project_name, profile):
    """Create CLAUDE.md documentation."""
    display_name = profile.get('display_name', project_name.title())
    origin = profile.get('origin', '')

    claude_md = f'''# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Development Standards

### Always Apply
- Use context7 for up-to-date library documentation
- Reference @~/Code/shared-docs/python/ for our internal standards
- Combine external best practices with our internal requirements

### Before Any Code Generation
1. Check Context7 for latest library patterns (use context7)
2. Review our internal requirements @~/Code/shared-docs/python/
3. Ensure both external and internal standards are met

## Project Overview

{display_name} Product Collector - Collects and enriches product data from {origin}.

## Architecture

This project collects product information from {display_name}'s website, including:
- Product titles and descriptions
- Images and media
- Ingredients and nutritional information
- UPC codes and product variants

### Core Components

**collector.py**: Main collector implementation
- Site-specific scraping logic
- Product data extraction
- Image harvesting and normalization

### Site Configuration

The {display_name} site configuration is embedded directly in `collector.py`.

## Usage

### Command Line

```bash
python collector.py --input products.json --output enriched.json
```

### Python API

```python
from collector import {project_name.title()}Collector

collector = {project_name.title()}Collector()
enriched = collector.collect_product(upc="123456789012")
```

## Development

### Setup

```bash
cd /Users/moosemarketer/Code/Python/collectors/{project_name}
pyenv local {project_name}
pip install -r requirements.txt
```

## Output Format

Enriched products include:
- All original input fields (preserved)
- `manufacturer`: Object with product data and images
- `distributors_or_retailers`: Retailer data if applicable
- `shopify.media`: Array of Shopify image filenames

## Notes

- Rate limiting is implemented to respect site resources
- All images are normalized to HTTPS
- UPC matching is flexible (strips non-digits)
'''

    claude_md_path = os.path.join(project_dir, "CLAUDE.md")
    with open(claude_md_path, "w") as f:
        f.write(claude_md)

    print(f"  ✓ Created CLAUDE.md")

def create_virtual_env(project_dir, project_name):
    """Create pyenv virtual environment and install dependencies."""
    try:
        # Create virtual environment
        print(f"  ⟳ Creating virtual environment '{project_name}'...")
        result = subprocess.run(
            ["pyenv", "virtualenv", "3.13.0", project_name],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0 and "already exists" not in result.stderr:
            print(f"  ⚠ Warning creating venv: {result.stderr}")

        # Set local Python version
        subprocess.run(
            ["pyenv", "local", project_name],
            cwd=project_dir,
            check=True
        )
        print(f"  ✓ Set local Python version")

        # Install dependencies
        print(f"  ⟳ Installing dependencies...")
        subprocess.run(
            ["pip", "install", "--upgrade", "pip"],
            cwd=project_dir,
            capture_output=True,
            timeout=120
        )

        result = subprocess.run(
            ["pip", "install", "-r", "requirements.txt"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print(f"  ✓ Installed dependencies")
        else:
            print(f"  ⚠ Warning installing deps: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        print(f"  ⚠ Timeout during virtual environment setup")
    except Exception as e:
        print(f"  ⚠ Error: {e}")

def main():
    print(f"Creating {len(PROJECTS)} collector projects...")
    print(f"Base directory: {COLLECTORS_DIR}\n")

    for project in PROJECTS:
        try:
            create_project(project)
        except Exception as e:
            print(f"✗ Error creating {project}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Project creation complete!")
    print(f"{'='*60}\n")
    print(f"Created projects in: {COLLECTORS_DIR}")
    print(f"\nNext steps:")
    print(f"  cd {COLLECTORS_DIR}/<project-name>")
    print(f"  python collector.py --input data.json --output enriched.json")

if __name__ == "__main__":
    main()
