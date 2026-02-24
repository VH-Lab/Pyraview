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

        # Required sample rate to satisfy pixels
        # We want approx 'pixels' samples in 'duration'
        # target_rate = pixels / duration
        # But we actually have min/max pairs. So we need pixels/2 pairs?
        # Standard approach: We want 'pixels' data points.
        # Since each sample is min/max (2 values), we need 'pixels/2' effective source samples?
        # Or does 'pixels' mean screen pixels? Usually 1 sample per pixel column.
        # Let's assume we want at least 'pixels' aggregated samples.

        target_rate = pixels / duration

        # Find best level
        selected_file = self.files[0] # Default to highest res
        for f in self.files:
            # If this file's rate is sufficient (>= target), pick it.
            # We iterate from high res (low decimation) to low res.
            # Actually we want the *lowest* res that is still sufficient.
            # So we should iterate from low res (high decimation) to high res?
            pass

        # Better: Filter for files with rate >= target_rate, then pick the one with lowest rate (highest decimation)
        candidates = [f for f in self.files if f['rate'] >= target_rate]
        if candidates:
            # Pick the one with the lowest rate (highest decimation) among candidates
            # This gives us the coarsest level that still meets the requirement
            selected_file = min(candidates, key=lambda x: x['rate'])
        else:
            # If none meet requirement (zoomed in too far), pick highest res (index 0)
            selected_file = self.files[0]

        # Calculate aperture (3x window)
        window = duration
        t_center = (t_start + t_end) / 2
        aperture_start = t_center - 1.5 * window
        aperture_end = t_center + 1.5 * window

        # Clamp to file bounds?
        # We don't know file duration from header easily without file size.
        # But start_time is known.
        if aperture_start < self.start_time:
            aperture_start = self.start_time

        # Convert time to sample indices
        # Index = (t - start_time) * sample_rate
        rel_start = aperture_start - self.start_time
        rel_end = aperture_end - self.start_time

        idx_start = int(rel_start * selected_file['rate'])
        idx_end = int(rel_end * selected_file['rate'])

        if idx_start < 0: idx_start = 0
        if idx_end <= idx_start: return np.array([]), np.array([])

        num_samples_to_read = idx_end - idx_start

        # Map file
        # Header is 1024 bytes.
        # Data size depends on type.
        dtype_map_rev = {
            0: np.int8, 1: np.uint8,
            2: np.int16, 3: np.uint16,
            4: np.int32, 5: np.uint32,
            6: np.int64, 7: np.uint64,
            8: np.float32, 9: np.float64
        }
        dt = dtype_map_rev.get(self.data_type, np.float64)
        item_size = np.dtype(dt).itemsize

        # Layout is CxS (1) or SxC (0)?
        # The writer usually does CxS for MATLAB compatibility, but let's check.
        # Wait, the writer code shows logic for both. But `pyraview.c` usually writes contiguous blocks per channel?
        # Actually `pyraview_process_chunk` writes `fwrite(buffers[i], ...)` inside a loop over channels:
        # `for (ch = 0; ch < C; ch++) ... fwrite(...)`.
        # This implies the file format is Channel-Major (blocks of channel data).
        # Channel 0 [all samples], Channel 1 [all samples]...
        # Wait, the `fwrite` is per channel, per level.
        # If we have multiple chunks appended, the file structure becomes:
        # [Header]
        # [Ch0_Chunk1][Ch1_Chunk1]...
        # [Ch0_Chunk2][Ch1_Chunk2]...
        # This is strictly not purely Channel-Major if appended. It's Chunk-Interleaved.
        # BUT, the `pyraview_process_chunk` function is usually called once for the whole file in offline processing,
        # OR if appending, it's appended in chunks.
        # If it's chunked, random access by time is hard without an index.
        # HOWEVER, the prompt implies "Time-to-sample-index conversion".
        # If the file is just one big chunk (offline conversion), then it's:
        # [Ch0 L1][Ch1 L1]...

        # If we assume standard "One Big Write" (no append loops in valid use case for random access):
        # The file is Ch0_All, Ch1_All...
        # We need to know total samples per channel to jump to Ch1.
        # File size = 1024 + Channels * Samples * 2 * ItemSize.
        # Samples = (FileSize - 1024) / (Channels * 2 * ItemSize).

        file_size = os.path.getsize(selected_file['path'])
        data_area = file_size - 1024
        frame_size = self.channels * 2 * item_size # 2 for min/max
        total_samples = data_area // frame_size # This assumes interleaved SxC or Blocked CxS?

        # Re-reading `pyraview.c`:
        # `for (ch = 0; ch < C; ch++) { ... fwrite(...) }`
        # It writes ALL data for Channel 0, then ALL data for Channel 1.
        # So it is Channel-Major Planar.
        # [Header][Ch0 MinMax...][Ch1 MinMax...]

        samples_per_channel = data_area // (self.channels * 2 * item_size)

        if idx_start >= samples_per_channel:
             return np.array([]), np.array([])

        if idx_end > samples_per_channel:
            idx_end = samples_per_channel
            num_samples_to_read = idx_end - idx_start

        # We need to read 'num_samples_to_read' from EACH channel.
        # Ch0 Offset = 1024 + idx_start * 2 * item_size
        # Ch1 Offset = 1024 + (samples_per_channel * 2 * item_size) + (idx_start * 2 * item_size)

        # Read logic
        data_out = np.zeros((num_samples_to_read, self.channels * 2), dtype=dt)

        with open(selected_file['path'], 'rb') as f:
            for ch in range(self.channels):
                # Calculate offset
                ch_start_offset = 1024 + (ch * samples_per_channel * 2 * item_size)
                read_offset = ch_start_offset + (idx_start * 2 * item_size)

                f.seek(read_offset)
                raw = f.read(num_samples_to_read * 2 * item_size)
                # Parse
                ch_data = np.frombuffer(raw, dtype=dt)

                # Interleave into output?
                # Output format: Rows=Samples, Cols=Channels*2 (Min,Max,Min,Max...)
                # data_out[:, 2*ch] = ch_data[0::2]
                # data_out[:, 2*ch+1] = ch_data[1::2]
                # Or just keep it separate?
                # Let's return (Samples x Channels*2)

                # Check bounds (short read?)
                read_len = len(ch_data)
                if read_len > 0:
                    # Direct assign might fail if shapes mismatch due to short read
                    # Reshape ch_data to (N, 2)?
                    # ch_data is flat Min0, Max0, Min1, Max1...
                    # We want to place it in data_out

                    # Ensure alignment
                    limit = min(num_samples_to_read * 2, read_len)
                    # We have 'limit' values.
                    # We need to distribute them.
                    # data_out is (N, C*2).
                    # We want data_out[:, 2*ch] and data_out[:, 2*ch+1]

                    # Reshape ch_data to (-1, 2)
                    pairs = ch_data[:limit].reshape(-1, 2)
                    rows = pairs.shape[0]
                    data_out[:rows, 2*ch] = pairs[:, 0]
                    data_out[:rows, 2*ch+1] = pairs[:, 1]

        # Time vector
        # t = start_time + (idx_start + i) / rate
        t_vec = self.start_time + (idx_start + np.arange(num_samples_to_read)) / selected_file['rate']

        return t_vec, data_out

def read_file(filename, s0, s1):
    """
    Reads a chunk of data from a Pyraview level file.

    Args:
        filename (str): Path to the file.
        s0 (int or float): Start sample index (0-based). Can be float('-inf').
        s1 (int or float): End sample index (0-based). Can be float('inf').

    Returns:
        np.ndarray: 3D array of shape (samples, channels, 2).
                    d[:, :, 0] is min values, d[:, :, 1] is max values.
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

    # Planar layout: [Header][Ch0][Ch1]...
    # Each channel block: TotalSamples * 2 * ItemSize
    total_samples = data_area // (num_channels * 2 * item_size)

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

    # Allocate output
    d = np.zeros((num_samples_to_read, num_channels, 2), dtype=dt)

    with open(filename, 'rb') as f:
        samples_per_channel_in_file = total_samples

        for ch in range(num_channels):
            ch_start_offset = header_size + (ch * samples_per_channel_in_file * 2 * item_size)
            read_offset = ch_start_offset + (start_sample * 2 * item_size)

            f.seek(read_offset)
            raw_bytes = f.read(num_samples_to_read * 2 * item_size)

            raw_data = np.frombuffer(raw_bytes, dtype=dt)

            # Handle short read
            n_read = len(raw_data) // 2
            if n_read > 0:
                d[:n_read, ch, 0] = raw_data[0 : 2*n_read : 2]
                d[:n_read, ch, 1] = raw_data[1 : 2*n_read : 2]

    return d
