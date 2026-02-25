# Pyraview Matlab MEX

## Compilation
To compile the MEX file (`pyraview.mex`):
1. Open Matlab and `cd` to this directory.
2. Run `build_pyraview`.

## Usage
`status = pyraview.pyraview(data, prefix, steps, nativeRate, [append], [numThreads])`

* `data`: Samples x Channels matrix (Single, Double, Int16, Uint8).
* `prefix`: Base file name (e.g. 'data/mydata').
* `steps`: Vector of decimation factors (e.g. [100, 10, 10]).
* `nativeRate`: Original sampling rate.
* `append`: (Optional) Append to existing files.

## Testing
Run `test_pyraview` to verify functionality.
