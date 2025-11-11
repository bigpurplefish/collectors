"""
Shared SKU Generator Utility

Generates unique 5-digit SKUs starting from 50000 for products that don't have SKUs.
Ensures uniqueness across all collectors by maintaining a persistent registry file.

Usage:
    from shared.utils.sku_generator import SKUGenerator

    generator = SKUGenerator()
    sku = generator.generate_unique_sku()
    print(f"Generated SKU: {sku}")
"""

import os
import json
import threading
from pathlib import Path
from typing import Set, Optional


class SKUGenerator:
    """
    Thread-safe SKU generator that maintains uniqueness across all collectors.

    Attributes:
        registry_file (Path): Path to the persistent SKU registry file
        used_skus (Set[str]): Set of all SKUs that have been generated
        next_auto_sku (int): The next SKU number to attempt
        _lock (threading.Lock): Thread lock for concurrent access safety
    """

    # Default starting SKU number
    DEFAULT_START_SKU = 50000

    # Registry file location (shared across all collectors)
    DEFAULT_REGISTRY_PATH = Path(__file__).parent.parent.parent / "cache" / "sku_registry.json"

    def __init__(self, registry_file: Optional[Path] = None, start_sku: Optional[int] = None):
        """
        Initialize the SKU generator.

        Args:
            registry_file: Optional custom path to the registry file
            start_sku: Optional custom starting SKU number (default: 50000)
        """
        self.registry_file = registry_file or self.DEFAULT_REGISTRY_PATH
        self.next_auto_sku = start_sku or self.DEFAULT_START_SKU
        self.used_skus: Set[str] = set()
        self._lock = threading.Lock()

        # Ensure the cache directory exists
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing SKUs from registry
        self._load_registry()

    def _load_registry(self) -> None:
        """
        Load the SKU registry from disk.

        Creates a new registry if one doesn't exist.
        Updates next_auto_sku to be one greater than the highest SKU found.
        """
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    self.used_skus = set(data.get('used_skus', []))
                    stored_next = data.get('next_auto_sku', self.DEFAULT_START_SKU)

                    # Find the highest SKU in the registry
                    highest_sku = max(
                        (int(sku) for sku in self.used_skus if sku.isdigit()),
                        default=self.DEFAULT_START_SKU - 1
                    )

                    # Use the higher of stored next or highest + 1
                    self.next_auto_sku = max(stored_next, highest_sku + 1)
            else:
                # Create new registry file
                self._save_registry()
        except (json.JSONDecodeError, ValueError, IOError) as e:
            # If registry is corrupted or unreadable, start fresh
            print(f"Warning: Could not load SKU registry ({e}). Starting fresh.")
            self.used_skus = set()
            self.next_auto_sku = self.DEFAULT_START_SKU
            self._save_registry()

    def _save_registry(self) -> None:
        """
        Save the current SKU registry to disk.

        Persists the set of used SKUs and the next SKU number.
        """
        try:
            with open(self.registry_file, 'w') as f:
                json.dump({
                    'used_skus': sorted(list(self.used_skus)),
                    'next_auto_sku': self.next_auto_sku
                }, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save SKU registry ({e}).")

    def generate_unique_sku(self) -> str:
        """
        Generate a unique 5-digit SKU starting from 50000.

        Thread-safe method that ensures each generated SKU is unique
        across all collectors by checking against the persistent registry.

        Returns:
            str: A unique SKU as a string (e.g., "50000", "50001", etc.)

        Example:
            >>> generator = SKUGenerator()
            >>> sku1 = generator.generate_unique_sku()
            >>> sku2 = generator.generate_unique_sku()
            >>> sku1 != sku2
            True
        """
        with self._lock:
            while True:
                sku = str(self.next_auto_sku)
                if sku not in self.used_skus:
                    self.used_skus.add(sku)
                    self.next_auto_sku += 1
                    self._save_registry()
                    return sku
                self.next_auto_sku += 1

    def mark_sku_used(self, sku: str) -> bool:
        """
        Mark a SKU as used (for importing existing SKUs into the registry).

        Args:
            sku: The SKU to mark as used

        Returns:
            bool: True if SKU was newly marked, False if already in registry

        Example:
            >>> generator = SKUGenerator()
            >>> generator.mark_sku_used("12345")
            True
            >>> generator.mark_sku_used("12345")
            False
        """
        with self._lock:
            if sku in self.used_skus:
                return False
            self.used_skus.add(sku)

            # Update next_auto_sku if this SKU is higher
            if sku.isdigit():
                sku_int = int(sku)
                if sku_int >= self.next_auto_sku:
                    self.next_auto_sku = sku_int + 1

            self._save_registry()
            return True

    def is_sku_used(self, sku: str) -> bool:
        """
        Check if a SKU has already been used.

        Args:
            sku: The SKU to check

        Returns:
            bool: True if SKU exists in registry, False otherwise

        Example:
            >>> generator = SKUGenerator()
            >>> generator.mark_sku_used("12345")
            True
            >>> generator.is_sku_used("12345")
            True
            >>> generator.is_sku_used("99999")
            False
        """
        with self._lock:
            return sku in self.used_skus

    def get_stats(self) -> dict:
        """
        Get statistics about the SKU registry.

        Returns:
            dict: Dictionary containing registry statistics

        Example:
            >>> generator = SKUGenerator()
            >>> stats = generator.get_stats()
            >>> print(stats['total_skus_used'])
            0
        """
        with self._lock:
            return {
                'total_skus_used': len(self.used_skus),
                'next_auto_sku': self.next_auto_sku,
                'registry_file': str(self.registry_file)
            }
