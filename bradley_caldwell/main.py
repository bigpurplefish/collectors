#!/usr/bin/env python3
"""
Bradley Caldwell Product Collector - Main Entry Point

Collects product data from Bradley Caldwell product catalog.
"""

import argparse
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.collector import BradleyCaldwellCollector


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Bradley Caldwell Product Collector")
    parser.add_argument("--catalog", required=True, help="Path to product catalog JSON file")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Initialize collector and process
    collector = BradleyCaldwellCollector(catalog_path=args.catalog)
    collector.process_file(args.input, args.output)


if __name__ == "__main__":
    main()
