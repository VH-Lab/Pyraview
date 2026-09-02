import os
import ctypes
import glob
import math
import warnings
import numpy as np
import sys

# Try to find the shared library
def _find_library():
    # Priority:
    # 1. Environment variable PYRAVIEW_LIB
    # 2. Inside this package, which is how the wheels ship it
    # 3. Relative to this file: ../../c/libpyraview.so (dev structure)
    # 4. Current working directory: ./libpyraview.so

    # MSVC and MinGW disagree about the "lib" prefix on Windows, so accept both.
    if sys.platform == "win32":
        lib_names = ["pyraview.dll", "libpyraview.dll"]
    elif sys.platform == "darwin":
        lib_names = ["libpyraview.dylib"]
    else:
        lib_names = ["libpyraview.so"]

    env_path = os.environ.get("PYRAVIEW_LIB")
    if env_path and os.path.exists(env_path):
        return env_path

    this_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        this_dir,                                   # bundled in the wheel
        os.path.join(this_dir, "..", "..", "c"),    # dev structure
        os.getcwd(),
    ]

    for directory in search_dirs:
        for lib_name in lib_names:
            candidate = os.path.join(directory, lib_name)
            if os.path.exists(candidate):
                return candidate

    # If not found, try loading by name (if in system path)
    return lib_names[0]

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

# Data type codes as they appear in the file header. The MATLAB spellings
# ("single"/"double") are accepted alongside the numpy ones so that code ported
# between the two bindings keeps working.
_TYPE_CODE_TO_NAME = {
    0: 'int8', 1: 'uint8',
    2: 'int16', 3: 'uint16',
    4: 'int32', 5: 'uint32',
    6: 'int64', 7: 'uint64',
    8: 'float32', 9: 'float64',
}

_TYPE_NAME_TO_CODE = dict((name, code) for code, name in _TYPE_CODE_TO_NAME.items())
_TYPE_NAME_TO_CODE['single'] = 8
_TYPE_NAME_TO_CODE['double'] = 9


def _coerce_data_type(value):
    """Accept a header code, a numpy dtype, or a type name; return the code."""
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        if int(value) not in _TYPE_CODE_TO_NAME:
            raise ValueError("Unknown data type code: %r" % (value,))
        return int(value)

    name = np.dtype(value).name if not isinstance(value, str) else value
    if name not in _TYPE_NAME_TO_CODE:
        raise ValueError("Unknown data type: %r" % (value,))
    return _TYPE_NAME_TO_CODE[name]


class PyraviewDataset:
    """A pyramid dataset: the levels available and which one to read at a zoom.

    Mirrors the MATLAB ``pyraview.Dataset`` class, so a port between the two
    bindings picks the same level, rounds sample indices the same way and gets
    the same array back.

    The dataset can be built two ways, and they compose exactly as in MATLAB --
    a folder is scanned first, then any explicitly supplied property overrides
    what the scan found:

    1. From a folder of ``*_L*.bin`` files::

           ds = PyraviewDataset('/path/to/folder')

    2. From explicit properties, for pyramid levels that do not live on disk
       under the scanned naming convention (levels stored in a database
       document, for instance)::

           ds = PyraviewDataset(
               native_rate=30000.0,
               channels=4,
               decimation_levels=[100, 10000],
               decimation_sampling_rates=[300.0, 3.0],
               decimation_start_time=[0.0, 0.0],
               files=['level1.bin', 'level2.bin'],
               folder_path='/path/to/folder')

    Attributes:
        native_rate (float): Sampling rate of the undecimated recording.
        native_start_time (float): Start time of the undecimated recording.
        channels (int): Number of channels.
        data_type (int): Header data type code; see ``_TYPE_CODE_TO_NAME``.
        decimation_levels (list[int]): Cumulative decimation factor per level.
        decimation_sampling_rates (list[float]): Sampling rate per level.
        decimation_start_time (list[float]): Start time per level.
        files (list[str]): File name per level, resolved against folder_path.
        folder_path (str or None): Folder the file names are relative to.

    The four per-level lists are parallel and ordered from finest to coarsest,
    so level ``i`` (1-based, as in MATLAB) is ``files[i - 1]``. Level 0 refers
    to the undecimated data.
    """

    def __init__(self, folder_path=None, native_rate=None, native_start_time=None,
                 channels=None, data_type=None, decimation_levels=None,
                 decimation_sampling_rates=None, decimation_start_time=None,
                 files=None):
        """Initialize from a folder, from explicit properties, or from both.

        Args:
            folder_path (str, optional): Folder to scan for ``*_L*.bin`` files.
            native_rate (float, optional): Overrides the scanned native rate.
            native_start_time (float, optional): Overrides the scanned start time.
            channels (int, optional): Overrides the scanned channel count.
            data_type (int or str or dtype, optional): Overrides the scanned type.
            decimation_levels (sequence[int], optional): Decimation factor per level.
            decimation_sampling_rates (sequence[float], optional): Rate per level.
            decimation_start_time (sequence[float], optional): Start time per level.
            files (sequence[str], optional): File name per level.

        Raises:
            FileNotFoundError: If folder_path is given but is not a folder.
            ValueError: If a supplied property is outside its valid range.
        """
        # Defaults match the MATLAB class's property defaults.
        self.folder_path = None
        self.native_rate = 1.0
        self.native_start_time = 0.0
        self.channels = 1
        self.data_type = 2  # int16
        self.decimation_levels = []
        self.decimation_sampling_rates = []
        self.decimation_start_time = []
        self.files = []

        if folder_path:
            if not os.path.isdir(folder_path):
                raise FileNotFoundError("Folder not found: %s" % (folder_path,))
            self.folder_path = folder_path
            self._scan_folder()

        # Explicit properties override whatever the scan found, as in MATLAB.
        if native_rate is not None:
            if native_rate <= 0:
                raise ValueError("native_rate must be positive, got %r" % (native_rate,))
            self.native_rate = float(native_rate)

        if native_start_time is not None:
            self.native_start_time = float(native_start_time)

        if channels is not None:
            if int(channels) != channels or channels <= 0:
                raise ValueError("channels must be a positive integer, got %r" % (channels,))
            self.channels = int(channels)

        if data_type is not None:
            self.data_type = _coerce_data_type(data_type)

        if decimation_levels is not None:
            levels = [int(v) for v in decimation_levels]
            if any(v < 0 for v in levels):
                raise ValueError("decimation_levels must be non-negative")
            self.decimation_levels = levels

        if decimation_sampling_rates is not None:
            rates = [float(v) for v in decimation_sampling_rates]
            if any(v <= 0 for v in rates):
                raise ValueError("decimation_sampling_rates must be positive")
            self.decimation_sampling_rates = rates

        if decimation_start_time is not None:
            self.decimation_start_time = [float(v) for v in decimation_start_time]

        if files is not None:
            self.files = list(files)

    @property
    def start_time(self):
        """Start time of the undecimated recording (alias of native_start_time)."""
        return self.native_start_time

    def _scan_folder(self):
        """Populate the per-level lists from the ``*_L*.bin`` files in the folder."""
        entries = []
        first_header = True

        for full_path in sorted(glob.glob(os.path.join(self.folder_path, '*_L*.bin'))):
            h = PyraviewHeader()
            if _lib.pyraview_get_header(full_path.encode('utf-8'), ctypes.byref(h)) != 0:
                warnings.warn("Failed to parse %s" % (full_path,))
                continue

            if first_header:
                self.native_rate = h.nativeRate
                self.native_start_time = h.startTime
                self.channels = h.channelCount
                self.data_type = h.dataType
                first_header = False

            entries.append({
                'decimation': int(h.decimationFactor),
                'rate': h.sampleRate,
                'start_time': h.startTime,
                'name': os.path.basename(full_path),
            })

        if not entries:
            return

        # Finest (least decimated) level first.
        entries.sort(key=lambda e: e['decimation'])

        self.decimation_levels = [e['decimation'] for e in entries]
        self.decimation_sampling_rates = [e['rate'] for e in entries]
        self.decimation_start_time = [e['start_time'] for e in entries]
        self.files = [e['name'] for e in entries]

    def _level_start_time(self, level):
        """Start time of a 1-based level, falling back to the native start time."""
        if level - 1 < len(self.decimation_start_time):
            return self.decimation_start_time[level - 1]
        return self.native_start_time

    def _level_path(self, level):
        """Absolute path of a 1-based level's file."""
        name = self.files[level - 1]
        if self.folder_path:
            return os.path.join(self.folder_path, name)
        return name

    def get_level_for_reading(self, t_start, t_end, pixels):
        """Choose the level to read for a time window at a given display width.

        Picks the coarsest level whose sampling rate still resolves ``pixels``
        columns across the window, falling back to the finest available level
        when every level is too coarse. Level 0 -- the undecimated data -- is a
        candidate, so a sufficiently zoomed-in window selects it even though it
        is not one of the files on disk.

        Args:
            t_start (float): Start of the window, in seconds.
            t_end (float): End of the window, in seconds.
            pixels (int): Number of columns available to draw the window.

        Returns:
            tuple: ``(t_vec, level, sample_start, sample_end)`` where ``t_vec``
            is the time of each sample, ``level`` is 0 for the undecimated data
            or a 1-based index into ``files``, and the sample range is 0-based
            with ``sample_end`` EXCLUSIVE. Note that this differs from
            ``read_file``, whose end index is inclusive.
            Returns ``(empty, None, None, None)`` for an empty window.
        """
        empty = (np.array([]), None, None, None)

        duration = t_end - t_start
        if duration <= 0:
            return empty

        target_rate = pixels / duration

        # (level, rate, start time); level 0 is the undecimated data.
        candidates = []
        if self.native_rate:
            candidates.append((0, self.native_rate, self.native_start_time))

        for i, rate in enumerate(self.decimation_sampling_rates, start=1):
            candidates.append((i, rate, self._level_start_time(i)))

        if not candidates:
            return empty

        valid = [c for c in candidates if c[1] >= target_rate]
        if valid:
            # Coarsest level that still resolves the window.
            level, rate, s_time = min(valid, key=lambda c: c[1])
        else:
            # Everything is too coarse; take the finest there is.
            level, rate, s_time = max(candidates, key=lambda c: c[1])

        # Samples are 0-based from the start of the level: idx = (t - s_time) * rate.
        # Rounding outwards keeps the window covered rather than clipped.
        idx_start = math.floor((t_start - s_time) * rate)
        idx_end = math.ceil((t_end - s_time) * rate)

        if idx_start < 0:
            idx_start = 0
        if idx_end < idx_start:
            idx_end = idx_start

        num_samples = idx_end - idx_start
        if num_samples > 0:
            t_vec = s_time + (idx_start + np.arange(num_samples)) / rate
        else:
            t_vec = np.array([])

        return t_vec, level, idx_start, idx_end

    def get_data(self, t_start, t_end, pixels):
        """Read the best level for a time window.

        Args:
            t_start (float): Start of the window, in seconds.
            t_end (float): End of the window, in seconds.
            pixels (int): Number of columns available to draw the window.

        Returns:
            tuple: ``(t_vec, data)`` where ``data`` has shape
            ``(Samples, Channels * 2)`` with columns ordered
            ``[Ch0_Min, Ch0_Max, Ch1_Min, Ch1_Max, ...]``, matching MATLAB's
            ``Dataset.getData``. Both are empty when there is nothing to read.
        """
        empty = (np.array([]), np.array([]))

        t_vec, level, s_start, s_end = self.get_level_for_reading(t_start, t_end, pixels)
        if level is None:
            return empty

        # Level 0 is the undecimated data, which the dataset does not hold, so
        # fall back to the finest level it does have.
        if level == 0:
            if not self.files:
                return empty

            level = 1
            rate = self.decimation_sampling_rates[0]
            s_time = self._level_start_time(level)

            s_start = math.floor((t_start - s_time) * rate)
            s_end = math.ceil((t_end - s_time) * rate)
            if s_start < 0:
                s_start = 0
            if s_end < s_start:
                s_end = s_start

            num_samples = s_end - s_start
            if num_samples <= 0:
                return empty
            t_vec = s_time + (s_start + np.arange(num_samples)) / rate

        if level > len(self.files):
            warnings.warn("Level %d requested but only %d files available."
                          % (level, len(self.files)))
            return empty

        path = self._level_path(level)
        if not os.path.isfile(path):
            warnings.warn("File not found: %s" % (path,))
            return empty

        dt = np.dtype(_TYPE_CODE_TO_NAME[self.data_type])
        # Interleaved (sample-major): [S0_Ch0_MinMax][S0_Ch1_MinMax]...[S1_Ch0...]
        frame_size = self.channels * 2 * dt.itemsize

        data_area = os.path.getsize(path) - 1024
        if data_area <= 0:
            return empty
        total_samples = data_area // frame_size

        if s_start >= total_samples:
            return empty

        read_end = min(s_end, total_samples)
        num_samples = read_end - s_start
        if num_samples <= 0:
            return empty

        # The window ran past the end of the file, so shorten the time vector.
        if read_end < s_end:
            rate = self.decimation_sampling_rates[level - 1]
            s_time = self._level_start_time(level)
            t_vec = s_time + (s_start + np.arange(num_samples)) / rate

        with open(path, 'rb') as f:
            f.seek(1024 + s_start * frame_size)
            raw = f.read(num_samples * frame_size)

        flat = np.frombuffer(raw, dtype=dt)
        actual_samples = len(flat) // (self.channels * 2)
        if actual_samples == 0:
            return empty

        if actual_samples < num_samples:
            flat = flat[:actual_samples * self.channels * 2]
            t_vec = t_vec[:actual_samples]

        return t_vec, flat.reshape(actual_samples, self.channels * 2)

    def get_view_data(self, t_start, t_end, pixels):
        """Deprecated alias of :meth:`get_data`, kept for existing callers."""
        return self.get_data(t_start, t_end, pixels)


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
