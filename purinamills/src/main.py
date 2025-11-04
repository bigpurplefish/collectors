#!/usr/bin/env python3
"""
Purinamills Product Collector - Main Entry Point

Collects product data from https://shop.purinamills.com.
"""

import argparse
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.collector import PurinamillsCollector


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Purinamills Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

    # TODO: Implement actual collection logic
    collector = PurinamillsCollector()
    print(f"Collector initialized with config: {collector.config['origin']}")


if __name__ == "__main__":
    main()
