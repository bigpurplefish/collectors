"""
Unit tests for SKU Generator utility.

Tests:
- SKU generation uniqueness
- Registry persistence
- Thread safety
- Cross-collector uniqueness
"""

import os
import json
import tempfile
import threading
import unittest
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sku_generator import SKUGenerator


class TestSKUGenerator(unittest.TestCase):
    """Test suite for SKUGenerator class."""

    def test_initialization_creates_registry_file(self):
        """Test that initialization creates registry file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            self.assertTrue(registry_file.exists())
            self.assertEqual(generator.next_auto_sku, SKUGenerator.DEFAULT_START_SKU)

    def test_generate_unique_sku_starts_at_50000(self):
        """Test that SKU generation starts at 50000."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            sku = generator.generate_unique_sku()
            self.assertEqual(sku, "50000")

    def test_generate_unique_sku_increments(self):
        """Test that SKUs increment sequentially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            sku1 = generator.generate_unique_sku()
            sku2 = generator.generate_unique_sku()
            sku3 = generator.generate_unique_sku()

            self.assertEqual(sku1, "50000")
            self.assertEqual(sku2, "50001")
            self.assertEqual(sku3, "50002")

    def test_generate_unique_sku_never_repeats(self):
        """Test that generated SKUs are always unique."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            skus = set()
            for _ in range(100):
                sku = generator.generate_unique_sku()
                self.assertNotIn(sku, skus, f"SKU {sku} was generated twice!")
                skus.add(sku)

            self.assertEqual(len(skus), 100)

    def test_registry_persistence(self):
        """Test that registry persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"

            # First instance generates some SKUs
            generator1 = SKUGenerator(registry_file=registry_file)
            sku1 = generator1.generate_unique_sku()
            sku2 = generator1.generate_unique_sku()

            # Second instance should continue from where first left off
            generator2 = SKUGenerator(registry_file=registry_file)
            sku3 = generator2.generate_unique_sku()

            self.assertEqual(sku1, "50000")
            self.assertEqual(sku2, "50001")
            self.assertEqual(sku3, "50002")

    def test_mark_sku_used(self):
        """Test marking existing SKUs as used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            # Mark a SKU as used
            result = generator.mark_sku_used("12345")
            self.assertTrue(result)

            # Marking same SKU again returns False
            result = generator.mark_sku_used("12345")
            self.assertFalse(result)

            # Verify it's in the registry
            self.assertTrue(generator.is_sku_used("12345"))

    def test_mark_sku_used_updates_next_auto_sku(self):
        """Test that marking a high SKU updates next_auto_sku."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            # Mark a high SKU as used
            generator.mark_sku_used("60000")

            # Next generated SKU should be higher
            sku = generator.generate_unique_sku()
            self.assertGreater(int(sku), 60000)

    def test_is_sku_used(self):
        """Test checking if a SKU is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            # Initially not used
            self.assertFalse(generator.is_sku_used("12345"))

            # After marking
            generator.mark_sku_used("12345")
            self.assertTrue(generator.is_sku_used("12345"))

            # After generating
            sku = generator.generate_unique_sku()
            self.assertTrue(generator.is_sku_used(sku))

    def test_get_stats(self):
        """Test getting registry statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            # Initial stats
            stats = generator.get_stats()
            self.assertEqual(stats['total_skus_used'], 0)
            self.assertEqual(stats['next_auto_sku'], 50000)

            # After generating some SKUs
            generator.generate_unique_sku()
            generator.generate_unique_sku()
            generator.mark_sku_used("12345")

            stats = generator.get_stats()
            self.assertEqual(stats['total_skus_used'], 3)
            self.assertEqual(stats['next_auto_sku'], 50002)

    def test_thread_safety(self):
        """Test that SKU generation is thread-safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            skus = []
            lock = threading.Lock()

            def generate_skus(count):
                for _ in range(count):
                    sku = generator.generate_unique_sku()
                    with lock:
                        skus.append(sku)

            # Create multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=generate_skus, args=(20,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify all SKUs are unique
            self.assertEqual(len(skus), 100)
            self.assertEqual(len(set(skus)), 100, "Duplicate SKUs generated in multi-threaded environment!")

    def test_custom_start_sku(self):
        """Test using custom starting SKU."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file, start_sku=70000)

            sku = generator.generate_unique_sku()
            self.assertEqual(sku, "70000")

    def test_registry_file_corruption_recovery(self):
        """Test recovery from corrupted registry file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"

            # Create corrupted registry
            with open(registry_file, 'w') as f:
                f.write("this is not valid json{{{")

            # Should recover gracefully
            generator = SKUGenerator(registry_file=registry_file)
            sku = generator.generate_unique_sku()
            self.assertEqual(sku, "50000")

    def test_registry_preserves_format(self):
        """Test that registry file has correct format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            generator.generate_unique_sku()
            generator.generate_unique_sku()
            generator.mark_sku_used("99999")

            # Read registry file
            with open(registry_file, 'r') as f:
                data = json.load(f)

            # Verify structure
            self.assertIn('used_skus', data)
            self.assertIn('next_auto_sku', data)
            self.assertIsInstance(data['used_skus'], list)
            self.assertIsInstance(data['next_auto_sku'], int)
            self.assertIn('50000', data['used_skus'])
            self.assertIn('50001', data['used_skus'])
            self.assertIn('99999', data['used_skus'])

    def test_cross_collector_uniqueness(self):
        """Test that SKUs are unique across multiple collector instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "shared_registry.json"

            # Simulate first collector
            collector1 = SKUGenerator(registry_file=registry_file)
            skus_collector1 = [collector1.generate_unique_sku() for _ in range(10)]

            # Simulate second collector (new instance, same registry)
            collector2 = SKUGenerator(registry_file=registry_file)
            skus_collector2 = [collector2.generate_unique_sku() for _ in range(10)]

            # Simulate third collector (new instance, same registry)
            collector3 = SKUGenerator(registry_file=registry_file)
            skus_collector3 = [collector3.generate_unique_sku() for _ in range(10)]

            # Verify all SKUs are unique across collectors
            all_skus = skus_collector1 + skus_collector2 + skus_collector3
            self.assertEqual(len(all_skus), 30)
            self.assertEqual(len(set(all_skus)), 30, "SKUs not unique across collectors!")

    def test_empty_registry_initialization(self):
        """Test initialization with empty registry file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"

            # Create empty registry
            with open(registry_file, 'w') as f:
                json.dump({}, f)

            generator = SKUGenerator(registry_file=registry_file)
            sku = generator.generate_unique_sku()
            self.assertEqual(sku, "50000")

    def test_registry_with_gaps(self):
        """Test that generator works correctly with gaps in SKU sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "test_registry.json"
            generator = SKUGenerator(registry_file=registry_file)

            # Create gaps by marking non-sequential SKUs
            generator.mark_sku_used("50000")
            generator.mark_sku_used("50005")
            generator.mark_sku_used("50010")

            # Generator should start after highest
            sku = generator.generate_unique_sku()
            self.assertGreater(int(sku), 50010)


if __name__ == "__main__":
    unittest.main(verbosity=2)
