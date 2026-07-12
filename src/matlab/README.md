# Pyraview Matlab MEX

## The MEX binary

The core of `pyraview.pyraview` is a compiled MEX binary
(`pyraview.mexa64`, `pyraview.mexw64`, `pyraview.mexmaca64`, etc.). When that
binary is present in the `+pyraview` folder, MATLAB calls it directly.

If the binary for your platform is **not** present, `pyraview.m` acts as a
fallback: the first time you call `pyraview.pyraview(...)` it will
automatically download the correct binary from the latest
[GitHub release](https://github.com/VH-Lab/Pyraview/releases/latest) (using
`websave`, falling back to `curl`) and then run your command. On macOS it also
clears the Gatekeeper quarantine flag so the binary can load. If the download
fails (no network, no binary for your platform, no write permission, etc.) it
raises a clear error telling you how to fix it.

This replaces the old confusing failure mode where a missing MEX binary
produced *"Execution of script pyraview as a function is not supported."*

## Compilation
To compile the MEX file (`pyraview.mex`) yourself:
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
