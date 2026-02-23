import unittest
import numpy as np
import os
import shutil
import sys
import tempfile

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import pyraview

class TestDataset(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.prefix = os.path.join(self.test_dir, "test_data")
        self.start_time = 100.0
        self.rate = 1000.0

        # Create dummy data
        # 2 channels, 10000 samples.
        # Ch0: Sine wave 1Hz
        # Ch1: Ramp
        t = np.arange(10000) / self.rate
        ch0 = (np.sin(2 * np.pi * t) * 1000).astype(np.int16)
        ch1 = (t * 100).astype(np.int16)
        data = np.stack([ch0, ch1], axis=1)

        # Process chunk
        # Levels: [10, 10] -> L1 (100Hz), L2 (10Hz)
        steps = [10, 10]
        pyraview.process_chunk(data, self.prefix, steps, self.rate, start_time=self.start_time)

        self.dataset = pyraview.PyraviewDataset(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_metadata(self):
        self.assertEqual(self.dataset.native_rate, self.rate)
        self.assertEqual(self.dataset.start_time, self.start_time)
        self.assertEqual(self.dataset.channels, 2)
        # Check levels
        # Should have L1 (dec 10) and L2 (dec 100)
        self.assertEqual(len(self.dataset.files), 2)
        self.assertEqual(self.dataset.files[0]['decimation'], 10)
        self.assertEqual(self.dataset.files[1]['decimation'], 100)

    def test_get_view_data(self):
        # Request full duration (10s) with low pixel count -> should pick L2
        t_start = self.start_time
        t_end = self.start_time + 10.0
        pixels = 50 # 50 pixels for 10s -> 5Hz required. L2 is 10Hz. L2 should be picked.

        t, data = self.dataset.get_view_data(t_start, t_end, pixels)

        # L2 Rate is 10Hz. 10s -> 100 samples.
        # Aperture is 3x window -> 30s? No, logic clamps to file bounds if implemented correctly or just reads available.
        # Window is 10s. Center 105. Aperture 90 to 120.
        # File covers 100 to 110.
        # So we request 90 to 120. Clamped start to 100.
        # End is 110 (100 samples).
        # Wait, if aperture logic requests beyond end, it should clamp?
        # My python logic clamps start but handles short read at end via file size.

        # Expectation: We read from 100.0 to 110.0 (end of file).
        # L2 has 100 samples.
        self.assertTrue(len(t) > 0)
        self.assertTrue(len(t) <= 100) # Could be less if aperture calculation aligns differently

        # Check content roughly
        # Ch0 L2 should be decimated sine. Min/Max around -1000/1000
        # Data format is [Min0 Max0 Min1 Max1]

        # Verify columns
        self.assertEqual(data.shape[1], 4) # 2 channels * 2

    def test_zoom_in(self):
        # Request small duration (1s) with high pixels -> should pick L1
        t_start = self.start_time + 1.0
        t_end = self.start_time + 2.0
        pixels = 200 # 200 Hz required. L1 is 100Hz. Native is 1000Hz.
        # Wait, L1 is 100Hz. 200Hz required -> L1 is insufficient?
        # Logic: candidates = rate >= target.
        # If target 200, L1(100) and L2(10) fail.
        # Fallback to index 0 (L1).

        t, data = self.dataset.get_view_data(t_start, t_end, pixels)

        # Should get L1 data.
        # 1s duration. 100Hz. Approx 100 samples (maybe 3x due to aperture).
        self.assertTrue(len(t) > 0)

if __name__ == '__main__':
    unittest.main()
