# Pyraview API Reference

## C API (`src/c/pyraview.c`, `include/pyraview_header.h`)

### `pyraview_process_chunk`
Processes a chunk of raw data and updates decimation pyramids.

Arguments:
- `dataArray`: Pointer to raw data.
- `numRows`: Number of samples per channel.
- `numCols`: Number of channels.
- `dataType`:
    - 0: `int8`
    - 1: `uint8`
    - 2: `int16`
    - 3: `uint16`
    - 4: `int32`
    - 5: `uint32`
    - 6: `int64`
    - 7: `uint64`
    - 8: `float32` (Single)
    - 9: `float64` (Double)
- `layout`: 0=SxC (Sample-Major), 1=CxS (Channel-Major).
- `filePrefix`: Base name for output files (e.g., `data/myrecording`).
- `append`: 1=Append, 0=Create/Overwrite.
- `levelSteps`: Pointer to array of decimation factors (e.g., `[100, 10, 10]`).
- `numLevels`: Number of elements in `levelSteps`.
- `nativeRate`: Original sampling rate (Hz).
- `numThreads`: Number of OpenMP threads (0 for auto).

Returns:
- 0 on success.
- Negative values on error (e.g., -2 mismatch, -1 I/O error).

---

## Python API (`src/python/pyraview.py`)

### `process_chunk(data, file_prefix, level_steps, native_rate, append=False, layout='SxC', num_threads=0)`
Wrapper for the C function.

Arguments:
- `data`: Numpy array (2D). Rows=Samples (if SxC), Rows=Channels (if CxS).
    - Supported dtypes: `int8`, `uint8`, `int16`, `uint16`, `int32`, `uint32`, `int64`, `uint64`, `float32`, `float64`.
- `file_prefix`: String path prefix.
- `level_steps`: List of integers.
- `native_rate`: Float.
- `append`: Boolean.
- `layout`: 'SxC' or 'CxS'.
- `num_threads`: Int.

Returns:
- 0 on success. Raises `RuntimeError` on failure.

---

## Matlab API (`src/matlab/pyraview_mex.c`)

### `status = pyraview_mex(data, prefix, steps, nativeRate, [append], [numThreads])`

Arguments:
- `data`: Numeric matrix. Supports: `int8`, `uint8`, `int16`, `uint16`, `int32`, `uint32`, `int64`, `uint64`, `single`, `double`.
- `prefix`: String.
- `steps`: Vector of integers.
- `nativeRate`: Scalar double.
- `append`: Logical/Scalar (optional).
- `numThreads`: Scalar (optional).

Returns:
- `status`: 0 on success. Throws error on failure.
