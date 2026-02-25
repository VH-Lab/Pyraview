import os
import ctypes
import numpy as np
import sys

# Try to find the shared library
def _find_library():
    # Priority:
    # 1. Environment variable PYRAVIEW_LIB
    # 2. Relative to this file: ../../c/libpyraview.so (dev structure)
    # 3. Current working directory: ./libpyraview.so

    lib_name = "libpyraview.so"
    if sys.platform == "win32":
        lib_name = "pyraview.dll"
    elif sys.platform == "darwin":
        lib_name = "libpyraview.dylib"

    env_path = os.environ.get("PYRAVIEW_LIB")
    if env_path and os.path.exists(env_path):
        return env_path

    # Relative to this file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    rel_path = os.path.join(this_dir, "..", "..", "c", lib_name)
    if os.path.exists(rel_path):
        return rel_path

    cwd_path = os.path.join(os.getcwd(), lib_name)
    if os.path.exists(cwd_path):
        return cwd_path

    # If not found, try loading by name (if in system path)
    return lib_name

_lib_path = _find_library()
try:
    _lib = ctypes.CDLL(_lib_path)
except OSError:
    raise ImportError(f"Could not load Pyraview library at {_lib_path}")

# Define types
_lib.pyraview_process_chunk.argtypes = [
    ctypes.c_void_p,                # dataArray
    ctypes.c_int64,                 # numRows
    ctypes.c_int64,                 # numCols
    ctypes.c_int,                   # dataType
    ctypes.c_int,                   # layout
    ctypes.c_char_p,                # filePrefix
    ctypes.c_int,                   # append
    ctypes.POINTER(ctypes.c_int),   # levelSteps
    ctypes.c_int,                   # numLevels
    ctypes.c_double,                # nativeRate
    ctypes.c_double,                # startTime
    ctypes.c_int                    # numThreads
]
_lib.pyraview_process_chunk.restype = ctypes.c_int

# Define Header Struct
class PyraviewHeader(ctypes.Structure):
    _pack_ = 64
    _fields_ = [
        ("magic", ctypes.c_char * 4),
        ("version", ctypes.c_uint32),
        ("dataType", ctypes.c_uint32),
        ("channelCount", ctypes.c_uint32),
        ("sampleRate", ctypes.c_double),
        ("nativeRate", ctypes.c_double),
        ("startTime", ctypes.c_double),
        ("decimationFactor", ctypes.c_uint32),
        ("reserved", ctypes.c_uint8 * 980)
    ]

_lib.pyraview_get_header.argtypes = [ctypes.c_char_p, ctypes.POINTER(PyraviewHeader)]
_lib.pyraview_get_header.restype = ctypes.c_int

def process_chunk(data, file_prefix, level_steps, native_rate, start_time=0.0, append=False, layout='SxC', num_threads=0):
    """
    Process a chunk of data and append to pyramid files.

    Args:
        data (np.ndarray): Input data (2D). Rows=Samples, Cols=Channels (if SxC).
        file_prefix (str): Base name for output files (e.g. "data/myfile").
        level_steps (list[int]): Decimation factors for each level (e.g. [100, 10, 10]).
        native_rate (float): Original sampling rate.
        start_time (float): Start time of the recording.
        append (bool): If True, append to existing files. If False, create new.
        layout (str): 'SxC' (Sample-Major) or 'CxS' (Channel-Major). Default 'SxC'.
        num_threads (int): Number of threads (0 for auto).

    Returns:
        int: 0 on success, negative on error.
    """
    if not isinstance(data, np.ndarray):
        raise TypeError("Data must be a numpy array")

    if data.ndim != 2:
        raise ValueError("Data must be 2D")

    # Determine layout
    layout_code = 0
    if layout == 'SxC':
        layout_code = 0
        num_rows, num_cols = data.shape
    elif layout == 'CxS':
        layout_code = 1
        num_cols, num_rows = data.shape
    else:
        raise ValueError("Layout must be 'SxC' or 'CxS'")

    # Determine data type code
    dtype_map = {
        np.dtype('int8'): 0,
        np.dtype('uint8'): 1,
        np.dtype('int16'): 2,
        np.dtype('uint16'): 3,
        np.dtype('int32'): 4,
        np.dtype('uint32'): 5,
        np.dtype('int64'): 6,
        np.dtype('uint64'): 7,
        np.dtype('float32'): 8,
        np.dtype('float64'): 9
    }

    if data.dtype not in dtype_map:
        raise TypeError(f"Unsupported data type: {data.dtype}. Supported: int8, uint8, int16, uint16, int32, uint32, int64, uint64, float32, float64")

    data_type_code = dtype_map[data.dtype]

    # Prepare C arguments
    c_level_steps = (ctypes.c_int * len(level_steps))(*level_steps)
    c_prefix = file_prefix.encode('utf-8')

    # Ensure data is contiguous in memory
    if not data.flags['C_CONTIGUOUS']:
        data = np.ascontiguousarray(data)

    data_ptr = data.ctypes.data_as(ctypes.c_void_p)

    ret = _lib.pyraview_process_chunk(
        data_ptr,
        ctypes.c_int64(num_rows),
        ctypes.c_int64(num_cols),
        ctypes.c_int(data_type_code),
        ctypes.c_int(layout_code),
        c_prefix,
        ctypes.c_int(1 if append else 0),
        c_level_steps,
        ctypes.c_int(len(level_steps)),
        ctypes.c_double(native_rate),
        ctypes.c_double(start_time),
        ctypes.c_int(num_threads)
    )

    if ret < 0:
        raise RuntimeError(f"Pyraview processing failed with code {ret}")

    return ret

class PyraviewDataset:
    def __init__(self, folder_path):
        """
        Initialize dataset by scanning the folder for pyramid files.
        """
        self.folder_path = folder_path
        self.files = [] # list of dicts: {level, decimation, rate, path, start_time}
        self.native_rate = None
        self.start_time = None
        self.channels = None
        self.data_type = None

        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Scan for _L*.bin files
        for f in os.listdir(folder_path):
            if f.endswith(".bin") and "_L" in f:
                full_path = os.path.join(folder_path, f)
                h = PyraviewHeader()
                if _lib.pyraview_get_header(full_path.encode('utf-8'), ctypes.byref(h)) == 0:
                    # Parse level from filename? Or rely on decimation?
                    # Filename format: prefix_L{level}.bin
                    # We can use decimationFactor to order them.

                    if self.native_rate is None:
                        self.native_rate = h.nativeRate
                        self.start_time = h.startTime
                        self.channels = h.channelCount
                        self.data_type = h.dataType

                    # Store info
                    self.files.append({
                        'decimation': h.decimationFactor,
                        'rate': h.sampleRate,
                        'path': full_path,
                        'start_time': h.startTime
                    })

        if not self.files:
            raise RuntimeError("No valid Pyraview files found in folder.")

        # Sort by decimation (ascending) -> High res to low res
        self.files.sort(key=lambda x: x['decimation'])

    def get_view_data(self, t_start, t_end, pixels):
        """
        Get data for a time range, optimizing for pixel width.
        Returns (time_vector, data_matrix).
        """
        duration = t_end - t_start
        if duration <= 0:
            return np.array([]), np.array([])

        target_rate = pixels / duration

        # Find best level
        selected_file = self.files[0] # Default to highest res

        # Filter for files with rate >= target_rate, then pick the one with lowest rate (highest decimation)
        candidates = [f for f in self.files if f['rate'] >= target_rate]
        if candidates:
            # Pick the one with the lowest rate (highest decimation) among candidates
            selected_file = min(candidates, key=lambda x: x['rate'])
        else:
            # If none meet requirement (zoomed in too far), pick highest res (index 0)
            selected_file = self.files[0]

        # Calculate range
        if t_start < self.start_time: t_start = self.start_time
        if t_end < self.start_time: return np.array([]), np.array([])

        rel_start = t_start - self.start_time
        rel_end = t_end - self.start_time

        idx_start = int(rel_start * selected_file['rate'])
        idx_end = int(rel_end * selected_file['rate'])

        if idx_start < 0: idx_start = 0
        if idx_end <= idx_start: return np.array([]), np.array([])

        num_samples_to_read = idx_end - idx_start

        # Map type
        dtype_map_rev = {
            0: np.int8, 1: np.uint8,
            2: np.int16, 3: np.uint16,
            4: np.int32, 5: np.uint32,
            6: np.int64, 7: np.uint64,
            8: np.float32, 9: np.float64
        }
        dt = dtype_map_rev.get(self.data_type, np.float64)
        item_size = np.dtype(dt).itemsize

        # Interleaved (Sample-Major) format
        # [Header]
        # [Sample 0 (C0m C0M C1m C1M ...)]
        # [Sample 1 (C0m C0M C1m C1M ...)]

        read_start_offset = 1024 + idx_start * (self.channels * 2 * item_size)
        bytes_to_read = num_samples_to_read * (self.channels * 2 * item_size)

        with open(selected_file['path'], 'rb') as f:
            f.seek(read_start_offset)
            raw = f.read(bytes_to_read)

        data_flat = np.frombuffer(raw, dtype=dt)

        # Output is (Samples x Channels*2)
        # Flat: [S0C0m S0C0M S0C1m ... S1C0m ...]
        # Reshape to (Samples, Channels*2)
        # Check size (short read)
        num_read_samples = len(data_flat) // (self.channels * 2)
        if num_read_samples == 0:
            return np.array([]), np.array([])

        data_flat = data_flat[:num_read_samples * self.channels * 2]
        data_out = data_flat.reshape(num_read_samples, self.channels * 2)

        # Time vector
        t_vec = self.start_time + (idx_start + np.arange(num_read_samples)) / selected_file['rate']

        return t_vec, data_out

def read_file(filename, s0, s1):
    """
    Reads a specific range of samples from a Pyraview level file.

    This function reads Min/Max pairs for each sample in the specified range.
    Pyraview level files store data in an Interleaved (Sample-Major) format.

    Args:
        filename (str): Path to the Pyraview level file.
        s0 (int or float): Start sample index (0-based).
                           Use float('-inf') to start from the beginning of the file.
        s1 (int or float): End sample index (0-based, inclusive).
                           Use float('inf') to read until the end of the file.

    Returns:
        np.ndarray: A 3D numpy array with shape (Samples, Channels, 2).
                    - result[:, :, 0] contains the Minimum values.
                    - result[:, :, 1] contains the Maximum values.
                    The data type of the array corresponds to the file's internal data type.

    Examples:
        >>> # Read samples 0 to 99
        >>> data = pyraview.read_file('my_data_L1.bin', 0, 99)
        >>> # Read everything from sample 1000 onwards
        >>> data = pyraview.read_file('my_data_L1.bin', 1000, float('inf'))
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    # Read header
    h = PyraviewHeader()
    if _lib.pyraview_get_header(filename.encode('utf-8'), ctypes.byref(h)) != 0:
        raise RuntimeError("Failed to read Pyraview header")

    num_channels = h.channelCount

    # Map type
    dtype_map_rev = {
        0: np.int8, 1: np.uint8,
        2: np.int16, 3: np.uint16,
        4: np.int32, 5: np.uint32,
        6: np.int64, 7: np.uint64,
        8: np.float32, 9: np.float64
    }
    if h.dataType not in dtype_map_rev:
        raise ValueError(f"Unknown data type: {h.dataType}")

    dt = dtype_map_rev[h.dataType]
    item_size = np.dtype(dt).itemsize

    # Calculate file structure
    file_size = os.path.getsize(filename)
    header_size = 1024
    data_area = file_size - header_size

    # Check if data area is valid
    if data_area < 0:
        return np.zeros((0, num_channels, 2), dtype=dt)

    # Interleaved layout: [Header][S0_AllCh][S1_AllCh]...
    # Each sample block: NumChannels * 2 * ItemSize
    frame_size = num_channels * 2 * item_size
    total_samples = data_area // frame_size

    # Handle indices
    start_sample = 0 if (s0 == float('-inf') or s0 < 0) else int(s0)

    if s1 == float('inf'):
        end_sample = total_samples - 1
    else:
        end_sample = int(s1)

    if end_sample >= total_samples:
        end_sample = total_samples - 1

    if start_sample > end_sample:
        return np.zeros((0, num_channels, 2), dtype=dt)

    num_samples_to_read = end_sample - start_sample + 1

    # Seek and Read Block
    read_start_offset = header_size + start_sample * frame_size
    bytes_to_read = num_samples_to_read * frame_size

    with open(filename, 'rb') as f:
        f.seek(read_start_offset)
        raw_bytes = f.read(bytes_to_read)

    raw_data = np.frombuffer(raw_bytes, dtype=dt)

    # Reshape
    # Raw is [S0C0m S0C0M S0C1m ... S1C0m ...]
    # Length check
    read_items = len(raw_data)
    actual_samples = read_items // (num_channels * 2)

    if actual_samples == 0:
        return np.zeros((0, num_channels, 2), dtype=dt)

    raw_data = raw_data[:actual_samples * num_channels * 2]

    # Reshape to (Samples, Channels, 2)
    # raw_data sequence: Sample0(Ch0m,Ch0M, Ch1m,Ch1M...), Sample1...
    # Reshape to (Samples, Channels*2)
    reshaped_flat = raw_data.reshape(actual_samples, num_channels * 2)

    # Now separate Min/Max
    # reshaped_flat[:, 0] is S_C0_m
    # reshaped_flat[:, 1] is S_C0_M
    # reshaped_flat[:, 2] is S_C1_m ...

    d = np.zeros((actual_samples, num_channels, 2), dtype=dt)

    # Vectorized assignment
    # d[:, :, 0] (Mins) -> columns 0, 2, 4...
    # d[:, :, 1] (Maxs) -> columns 1, 3, 5...

    d[:, :, 0] = reshaped_flat[:, 0::2]
    d[:, :, 1] = reshaped_flat[:, 1::2]

    return d
