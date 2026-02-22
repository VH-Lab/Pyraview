import numpy as np
import os
import sys
import struct

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import pyraview

def test_header_type():
    prefix = "test_header"

    # Test cases: (numpy_dtype, expected_enum_value)
    cases = [
        (np.int8, 0),
        (np.uint8, 1),
        (np.int16, 2),
        (np.uint16, 3),
        (np.int32, 4),
        (np.uint32, 5),
        (np.int64, 6),
        (np.uint64, 7),
        (np.float32, 8),
        (np.float64, 9),
    ]

    for dtype, expected_code in cases:
        print(f"Testing {dtype} -> {expected_code}")
        data = np.zeros((100, 1), dtype=dtype)
        # Cleanup
        outfile = f"{prefix}_L1.bin"
        if os.path.exists(outfile):
            os.remove(outfile)

        pyraview.process_chunk(data, prefix, [10], 100.0)

        with open(outfile, 'rb') as f:
            # magic: 4, version: 4, dataType: 4
            f.seek(8)
            code_bytes = f.read(4)
            code = struct.unpack('<I', code_bytes)[0]
            if code != expected_code:
                print(f"FAILED: Expected {expected_code}, got {code}")
                sys.exit(1)
            else:
                print("OK")

        os.remove(outfile)

if __name__ == "__main__":
    test_header_type()
