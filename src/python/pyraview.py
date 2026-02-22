import os
import ctypes
import numpy as np
import sys

# Try to find the shared library
def _find_library():
    # Priority:
    # 1. Environment variable PYRAVIEW_LIB
    # 2. Relative to this file: ../c/libpyraview.so (dev structure)
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
    rel_path = os.path.join(this_dir, "..", "c", lib_name)
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
    ctypes.c_int                    # numThreads
]
_lib.pyraview_process_chunk.restype = ctypes.c_int

def process_chunk(data, file_prefix, level_steps, native_rate, append=False, layout='SxC', num_threads=0):
    """
    Process a chunk of data and append to pyramid files.

    Args:
        data (np.ndarray): Input data (2D). Rows=Samples, Cols=Channels (if SxC).
        file_prefix (str): Base name for output files (e.g. "data/myfile").
        level_steps (list[int]): Decimation factors for each level (e.g. [100, 10, 10]).
        native_rate (float): Original sampling rate.
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
        np.dtype('uint8'): 0,
        np.dtype('int16'): 1,
        np.dtype('float32'): 2,
        np.dtype('float64'): 3
    }

    if data.dtype not in dtype_map:
        raise TypeError(f"Unsupported data type: {data.dtype}. Supported: uint8, int16, float32, float64")

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
        ctypes.c_int(num_threads)
    )

    if ret < 0:
        raise RuntimeError(f"Pyraview processing failed with code {ret}")

    return ret
