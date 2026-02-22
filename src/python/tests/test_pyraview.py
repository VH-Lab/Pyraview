import unittest
import numpy as np
import os
import sys

# Add parent dir to path to find pyraview.py
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import pyraview

class TestPyraview(unittest.TestCase):
    def setUp(self):
        self.prefix = "test_output"
        # Cleanup potential leftovers
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        for f in os.listdir("."):
            if f.startswith(self.prefix) and f.endswith(".bin"):
                os.remove(f)

    def test_basic_generation(self):
        # 1000 samples, 2 channels. Step 10.
        # Output should be 100 samples (Min/Max pairs) -> 200 values per channel.
        # Total 400 values in file.
        data = np.random.rand(1000, 2).astype(np.float32)
        steps = [10]
        ret = pyraview.process_chunk(data, self.prefix, steps, 1000.0)
        self.assertEqual(ret, 0)

        outfile = f"{self.prefix}_L1.bin"
        self.assertTrue(os.path.exists(outfile))

        # Verify size
        # Header 1024 + 2 channels * 100 samples * 2 (min/max) * 4 bytes
        # 1024 + 1600 = 2624 bytes.
        size = os.path.getsize(outfile)
        self.assertEqual(size, 2624)

    def test_values_correctness(self):
        # Create predictable data
        # Ch0: 0..99. Min/Max of 0..9 is 0,9. 10..19 is 10,19.
        data = np.zeros((100, 1), dtype=np.int16)
        for i in range(100):
            data[i, 0] = i

        steps = [10]
        pyraview.process_chunk(data, self.prefix, steps, 100.0)

        # Read back
        outfile = f"{self.prefix}_L1.bin"
        with open(outfile, 'rb') as f:
            f.seek(1024)
            raw = f.read()
            arr = np.frombuffer(raw, dtype=np.int16)

        # Should be 10 pairs. Total 20 values.
        self.assertEqual(len(arr), 20)
        # 0: 0, 9
        # 1: 10, 19
        self.assertEqual(arr[0], 0)
        self.assertEqual(arr[1], 9)
        self.assertEqual(arr[2], 10)
        self.assertEqual(arr[3], 19)

    def test_append(self):
        data = np.zeros((100, 1), dtype=np.uint8)
        steps = [10]
        # First chunk
        ret1 = pyraview.process_chunk(data, self.prefix, steps, 100.0, append=False)
        self.assertEqual(ret1, 0)

        # Second chunk
        ret2 = pyraview.process_chunk(data, self.prefix, steps, 100.0, append=True)
        self.assertEqual(ret2, 0)

        outfile = f"{self.prefix}_L1.bin"
        size = os.path.getsize(outfile)
        # Header + 2 chunks * (100/10 * 2 values * 1 byte) = 1024 + 40 = 1064
        self.assertEqual(size, 1064)

if __name__ == '__main__':
    unittest.main()
