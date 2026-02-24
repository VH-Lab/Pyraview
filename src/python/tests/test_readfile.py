import unittest
import os
import sys
import numpy as np
import struct
import tempfile
import ctypes
from unittest.mock import MagicMock, patch

# Add src/python to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python')))

# Mock ctypes.CDLL globally for this test file
patcher = patch('ctypes.CDLL')
mock_cdll = patcher.start()
mock_lib = MagicMock()
mock_cdll.return_value = mock_lib

try:
    import pyraview
except ImportError:
    # If it fails for some other reason
    pyraview = None

class TestReadFile(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        patcher.stop()

    def setUp(self):
        if pyraview is None:
            self.skipTest("pyraview module could not be imported")

        self.tmp_fd, self.tmp_path = tempfile.mkstemp()
        os.close(self.tmp_fd)

        # Configure mock_lib.pyraview_get_header side effect
        def get_header_side_effect(fname, header_ptr):
            # Read the file to get real header data
            with open(fname, 'rb') as f:
                data = f.read(1024)
                if len(data) < 1024:
                    return -1

                # Unpack
                # magic (4s), ver (I), type (I), ch (I), rate (d), native (d), start (d), dec (I)
                # 4+4+4+4+8+8+8+4 = 44 bytes
                vals = struct.unpack('4sIIIdddI', data[:44])

                # header_ptr is a ctypes.byref object (CArgObject), use _obj to access the structure
                h = header_ptr._obj
                h.magic = vals[0]
                h.version = vals[1]
                h.dataType = vals[2]
                h.channelCount = vals[3]
                h.sampleRate = vals[4]
                h.nativeRate = vals[5]
                h.startTime = vals[6]
                h.decimationFactor = vals[7]

            return 0

        # We need to set side_effect on the mock object that pyraview imported
        # pyraview._lib is mock_lib
        pyraview._lib.pyraview_get_header.side_effect = get_header_side_effect
        pyraview._lib.pyraview_get_header.restype = ctypes.c_int

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def create_dummy_file(self, num_samples, num_channels, data_type_code, data_type_np):
        with open(self.tmp_path, 'wb') as f:
            # Header
            f.write(b'PYRA')
            f.write(struct.pack('I', 1))
            f.write(struct.pack('I', data_type_code))
            f.write(struct.pack('I', num_channels))
            f.write(struct.pack('d', 1000.0))
            f.write(struct.pack('d', 1000.0))
            f.write(struct.pack('d', 0.0))
            f.write(struct.pack('I', 1))
            f.write(b'\x00' * 980)

            # Data
            # Planar: Ch0 [Sample0 Min, Sample0 Max...], Ch1 [...]

            # Generate deterministic data
            data = np.zeros((num_samples, num_channels, 2), dtype=data_type_np)
            for ch in range(num_channels):
                for i in range(num_samples):
                    min_val = (ch * 1000) + (i * 2)
                    max_val = (ch * 1000) + (i * 2) + 1
                    data[i, ch, 0] = min_val
                    data[i, ch, 1] = max_val

            # Write planar
            for ch in range(num_channels):
                # Interleave min/max for channel
                ch_data = np.zeros((num_samples * 2,), dtype=data_type_np)
                ch_data[0::2] = data[:, ch, 0]
                ch_data[1::2] = data[:, ch, 1]
                f.write(ch_data.tobytes())

            return data

    def test_read_int16(self):
        num_samples = 100
        num_channels = 2
        data_type_code = 2 # int16
        data_type_np = np.int16

        expected_data = self.create_dummy_file(num_samples, num_channels, data_type_code, data_type_np)

        # Test full read
        d = pyraview.read_file(self.tmp_path, 0, num_samples-1)
        self.assertEqual(d.shape, (num_samples, num_channels, 2))
        np.testing.assert_array_equal(d, expected_data)

        # Test partial read
        s0 = 10
        s1 = 20
        d_part = pyraview.read_file(self.tmp_path, s0, s1)
        self.assertEqual(d_part.shape, (11, num_channels, 2))
        np.testing.assert_array_equal(d_part, expected_data[s0:s1+1])

        # Test Inf
        d_inf = pyraview.read_file(self.tmp_path, float('-inf'), float('inf'))
        np.testing.assert_array_equal(d_inf, expected_data)

    def test_read_float64(self):
        num_samples = 50
        num_channels = 1
        data_type_code = 9 # float64
        data_type_np = np.float64

        expected_data = self.create_dummy_file(num_samples, num_channels, data_type_code, data_type_np)

        d = pyraview.read_file(self.tmp_path, 0, num_samples-1)
        np.testing.assert_array_equal(d, expected_data)

    def test_empty_read(self):
        self.create_dummy_file(10, 1, 2, np.int16)
        d = pyraview.read_file(self.tmp_path, 5, 4)
        self.assertEqual(d.shape, (0, 1, 2))

if __name__ == '__main__':
    unittest.main()
