# Pyraview API Reference

## C/C++ API (`src/c/pyraview.cpp`, `include/pyraview_header.h`)

The core implementation is written in C++11 for efficient multi-threading, but exposes a C-compatible API for easy integration with other languages.

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
- `numThreads`: Number of worker threads (0 for auto).

Returns:
- 0 on success.
- Negative values on error (e.g., -2 mismatch, -1 I/O error).

---

## Python API (`src/python/pyraview/__init__.py`)

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

### `read_file(filename, s0, s1)`
Reads a specific range of samples from a level file.

Arguments:
- `filename`: String path to the file.
- `s0`: Start sample index (int or float). Use `float('-inf')` for beginning.
- `s1`: End sample index (int or float). Use `float('inf')` for end.

Returns:
- Numpy array of shape `(Samples, Channels, 2)`.
    - `[:, :, 0]`: Minimum values.
    - `[:, :, 1]`: Maximum values.

---

## Matlab API (`src/matlab/+pyraview/`)

### `status = pyraview.pyraview(data, prefix, steps, nativeRate, [append], [numThreads])`
Processes raw data into multi-resolution pyramid files.

Arguments:
- `data`: (Samples x Channels) matrix.
    - Supported types: `int8`, `uint8`, `int16`, `uint16`, `int32`, `uint32`, `int64`, `uint64`, `single`, `double`.
- `prefix`: String specifying the base path and name for the output files.
    - Generates files named `<prefix>_L1.bin`, `<prefix>_L2.bin`, etc.
- `steps`: Vector of integers specifying decimation factors for each level (relative to previous level).
- `nativeRate`: Scalar double (Hz). Original sampling rate of the raw data.
- `append`: (Optional) Logical/Scalar. Default `false`. If true, appends to existing files.
- `numThreads`: (Optional) Scalar integer. Default `0` (Auto). Number of worker threads.

Returns:
- `status`: 0 on success. Negative values indicate errors.

### `D = pyraview.readFile(filename, s0, s1)`
Reads a specific range of samples from a level file.

Arguments:
- `filename`: String path to the `.bin` level file.
- `s0`: Start sample index (0-based). Can be `-Inf`.
- `s1`: End sample index (0-based). Can be `Inf`.

Returns:
- `D`: A 3D matrix of size `(Samples x Channels x 2)`.
    - `D(:, :, 1)`: Minimum values.
    - `D(:, :, 2)`: Maximum values.

### `HEADER = pyraview.get_header(filename)`
Reads the binary header from a Pyraview level file.

Arguments:
- `filename`: String path to the file.

Returns:
- `HEADER`: Struct containing metadata fields (`magic`, `version`, `dataType`, `channelCount`, `sampleRate`, `nativeRate`, `startTime`, `decimationFactor`).

### `obj = pyraview.Dataset(folderPath, [Name, Value...])`
Class representing a dataset of multi-resolution files.

Arguments:
- `folderPath`: (Optional) String path to the folder containing level files.
- `NativeRate`: (Optional) Original sampling rate.
- `NativeStartTime`: (Optional) Start time.
- `Channels`: (Optional) Number of channels.
- `DataType`: (Optional) Data type string (e.g., 'int16').
- `decimationLevels`: (Optional) Vector of decimation factors.
- `Files`: (Optional) Cell array of filenames.

Methods:
- `[tVec, decimationLevel, sampleStart, sampleEnd] = obj.getLevelForReading(tStart, tEnd, pixels)`
- `[tVec, dataOut] = obj.getData(tStart, tEnd, pixels)`
