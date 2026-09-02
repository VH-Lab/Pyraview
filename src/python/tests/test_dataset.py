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
        self.assertEqual(self.dataset.native_start_time, self.start_time)
        self.assertEqual(self.dataset.start_time, self.start_time)  # alias
        self.assertEqual(self.dataset.channels, 2)
        # Should have L1 (dec 10) and L2 (dec 100), finest first
        self.assertEqual(self.dataset.decimation_levels, [10, 100])
        self.assertEqual(self.dataset.decimation_sampling_rates, [100.0, 10.0])
        self.assertEqual(self.dataset.decimation_start_time,
                         [self.start_time, self.start_time])
        self.assertEqual(len(self.dataset.files), 2)
        self.assertTrue(all(isinstance(f, str) for f in self.dataset.files))

    # --- Level selection, mirroring the MATLAB TestDataset cases ---

    def test_level_for_reading_picks_raw(self):
        """A demand no decimated level can meet selects level 0 (raw)."""
        # Duration 10s, 5000 px -> 500 Hz. Only the native rate (1000) qualifies.
        _, level, _, _ = self.dataset.get_level_for_reading(100, 110, 5000)
        self.assertEqual(level, 0)

    def test_level_for_reading_picks_coarsest_sufficient(self):
        # 500 px over 10s -> 50 Hz. Native (1000) and L1 (100) qualify; the
        # coarsest sufficient one wins.
        _, level, _, _ = self.dataset.get_level_for_reading(100, 110, 500)
        self.assertEqual(level, 1)

        # 50 px over 10s -> 5 Hz. All qualify, so L2 (10 Hz) wins.
        _, level, _, _ = self.dataset.get_level_for_reading(100, 110, 50)
        self.assertEqual(level, 2)

    def test_level_for_reading_empty_window(self):
        t, level, s0, s1 = self.dataset.get_level_for_reading(110, 100, 500)
        self.assertIsNone(level)
        self.assertEqual(len(t), 0)

    def test_sample_indices_round_outwards(self):
        """floor at the start and ceil at the end, as MATLAB does."""
        # A 0.01 s window at 1 px demands 100 Hz, which selects L1 (100 Hz,
        # start 100.0). The window spans samples 1.5 .. 2.5, which must widen
        # to 1 .. 3 rather than truncate to 1 .. 2 and clip the edges.
        t_vec, level, s_start, s_end = self.dataset.get_level_for_reading(
            100.015, 100.025, pixels=1)
        self.assertEqual(level, 1)
        self.assertEqual(s_start, 1)   # floor(1.5)
        self.assertEqual(s_end, 3)     # ceil(2.5), exclusive

        # Truncating both ends, as the old code did, would have read samples
        # 1 .. 2 -- one sample, with the right-hand edge of the window lost.
        self.assertEqual(len(t_vec), 2)

    def test_negative_start_clamped(self):
        _, _, s_start, _ = self.dataset.get_level_for_reading(0.0, 105.0, 100)
        self.assertEqual(s_start, 0)

    # --- Property-based construction ---

    def test_property_construction(self):
        """Levels that do not live on disk under the scanned naming scheme."""
        ds = pyraview.PyraviewDataset(
            native_rate=30000.0,
            native_start_time=5.0,
            channels=4,
            data_type='int16',
            decimation_levels=[100, 10000],
            decimation_sampling_rates=[300.0, 3.0],
            decimation_start_time=[5.0, 5.0],
            files=['level1.bin', 'level2.bin'])

        self.assertEqual(ds.native_rate, 30000.0)
        self.assertEqual(ds.channels, 4)
        self.assertEqual(ds.files, ['level1.bin', 'level2.bin'])
        self.assertIsNone(ds.folder_path)

        # 1000 px over 10s -> 100 Hz: native (30000) and L1 (300) qualify.
        _, level, _, _ = ds.get_level_for_reading(5.0, 15.0, 1000)
        self.assertEqual(level, 1)

    def test_properties_override_folder_scan(self):
        """A folder scan runs first, then explicit properties override it."""
        ds = pyraview.PyraviewDataset(self.test_dir, channels=7)
        self.assertEqual(ds.channels, 7)
        self.assertEqual(ds.native_rate, self.rate)  # still from the scan
        self.assertEqual(len(ds.files), 2)

    def test_no_levels_only_raw(self):
        """With no files, every demand resolves to level 0."""
        ds = pyraview.PyraviewDataset(native_rate=2000.0, native_start_time=0.0)
        _, level, _, _ = ds.get_level_for_reading(0, 10, 100)
        self.assertEqual(level, 0)
        # ...and there is nothing to read.
        t, d = ds.get_data(0, 10, 100)
        self.assertEqual(len(t), 0)
        self.assertEqual(len(d), 0)

    def test_per_level_start_times(self):
        """Each level's own start time drives its sample indices."""
        ds = pyraview.PyraviewDataset(
            native_rate=1000.0, native_start_time=0.0,
            decimation_sampling_rates=[100.0, 10.0],
            decimation_start_time=[50.0, 70.0],
            files=['a.bin', 'b.bin'])

        # 10 px over 10s -> 1 Hz, so L2 (10 Hz, start 70.0) wins.
        t_vec, level, s_start, _ = ds.get_level_for_reading(80.0, 90.0, 10)
        self.assertEqual(level, 2)
        self.assertEqual(s_start, 100)          # (80 - 70) * 10
        self.assertAlmostEqual(t_vec[0], 80.0)  # not measured from level 1

    def test_validation(self):
        with self.assertRaises(ValueError):
            pyraview.PyraviewDataset(native_rate=-5)
        with self.assertRaises(ValueError):
            pyraview.PyraviewDataset(channels=1.5)
        with self.assertRaises(ValueError):
            pyraview.PyraviewDataset(data_type='invalid')
        with self.assertRaises(ValueError):
            pyraview.PyraviewDataset(decimation_sampling_rates=[100.0, -1.0])
        with self.assertRaises(FileNotFoundError):
            pyraview.PyraviewDataset('/no/such/folder')

    def test_data_type_spellings(self):
        """MATLAB's names, numpy's names and the raw codes all work."""
        for spelling in ('double', 'float64', np.float64, 9):
            ds = pyraview.PyraviewDataset(data_type=spelling)
            self.assertEqual(ds.data_type, 9)

    # --- Reading ---

    def test_get_data_shape_and_columns(self):
        t, data = self.dataset.get_data(self.start_time, self.start_time + 10.0, 50)
        self.assertTrue(len(t) > 0)
        self.assertEqual(data.shape[1], 4)  # 2 channels * 2
        self.assertEqual(data.shape[0], len(t))

        # Ch0 is the sine, so its max column reaches near +1000.
        self.assertGreater(data[:, 1].max(), 900)
        # Ch1 is a ramp, so its max column is non-decreasing.
        self.assertTrue(np.all(np.diff(data[:, 3].astype(np.int32)) >= 0))

    def test_get_data_agrees_with_read_file(self):
        """get_data must return exactly what read_file returns for that level.

        This pins the two read paths together: get_data reads the file
        directly, and reading it as planar rather than interleaved would put
        channel 1's values in channel 0's columns.
        """
        t_start, t_end, pixels = self.start_time + 1.0, self.start_time + 5.0, 50

        t_vec, level, s_start, s_end = self.dataset.get_level_for_reading(
            t_start, t_end, pixels)
        # 50 px over 4 s demands 12.5 Hz, which L2 (10 Hz) cannot meet.
        self.assertEqual(level, 1)

        _, data = self.dataset.get_data(t_start, t_end, pixels)

        path = os.path.join(self.test_dir, self.dataset.files[level - 1])
        # read_file's end index is inclusive; get_level_for_reading's is not.
        expected = pyraview.read_file(path, s_start, s_end - 1)

        self.assertEqual(data.shape, (expected.shape[0], expected.shape[1] * 2))
        np.testing.assert_array_equal(data.reshape(expected.shape), expected)

    def test_get_data_clamps_past_end_of_file(self):
        t, data = self.dataset.get_data(self.start_time + 5.0,
                                        self.start_time + 500.0, 50)
        # The file ends at 110.0, so the read stops there.
        self.assertEqual(len(t), data.shape[0])
        self.assertLess(t[-1], self.start_time + 10.0 + 1e-9)

    def test_get_data_starting_past_end_of_file(self):
        t, data = self.dataset.get_data(self.start_time + 500.0,
                                        self.start_time + 510.0, 50)
        self.assertEqual(len(t), 0)
        self.assertEqual(len(data), 0)

    def test_level_zero_falls_back_to_finest_file(self):
        """Level 0 has no file, so reading it uses level 1."""
        _, level, _, _ = self.dataset.get_level_for_reading(
            self.start_time, self.start_time + 10.0, 5000)
        self.assertEqual(level, 0)

        t, data = self.dataset.get_data(self.start_time, self.start_time + 10.0, 5000)
        # L1 is 100 Hz over 10 s -> 1000 samples.
        self.assertEqual(data.shape[0], 1000)
        self.assertEqual(data.shape[1], 4)

    def test_get_view_data_alias(self):
        args = (self.start_time, self.start_time + 10.0, 50)
        t1, d1 = self.dataset.get_view_data(*args)
        t2, d2 = self.dataset.get_data(*args)
        np.testing.assert_array_equal(t1, t2)
        np.testing.assert_array_equal(d1, d2)

if __name__ == '__main__':
    unittest.main()
