# Pyraview

Routines for generating different views of data series (e.g., 1:100, 1:1000, 1:10000 views, etc). The project provides a C++ core library with bindings for MATLAB and Python.

## Installation

### MATLAB

#### Option 1: Toolbox (Recommended)
1.  Go to the [Releases](../../releases) page.
2.  Download the `Pyraview.mltbx` file.
3.  Open MATLAB and double-click the `.mltbx` file to install the toolbox.
4.  The `pyraview` functions will be available immediately.

#### Option 2: Build from Source
If you are developing the library or need to modify the source code:
1.  Open MATLAB.
2.  Navigate to the `src/matlab` directory.
3.  Run the build script:
    ```matlab
    build_pyraview
    ```
    This will compile `pyraview.mex` (or `.mexw64`, `.mexmaci64`, etc.) into the `+pyraview` package directory.
4.  Add the `src/matlab` directory to your MATLAB path.

**Usage:**
```matlab
% Example usage
status = pyraview.pyraview(data, prefix, steps, nativeRate);
```
See `src/matlab/README.md` for more details.

### Python

Pyraview is installed from this repository; it is not published on PyPI.

#### Option 1: Install from a Release Wheel (Recommended)

Each [Release](../../releases) carries wheels for Linux, Windows and macOS.
A wheel bundles the compiled library inside the package, so installing one
needs no compiler and no environment variable:

```bash
pip install https://github.com/VH-Lab/Pyraview/releases/download/v0.4.0/<wheel file>
```

Pick the wheel matching your platform and Python version -- for example
`pyraview-0.4.0-cp311-cp311-win_amd64.whl` for Python 3.11 on 64-bit Windows.

#### Option 2: Install from Source

```bash
pip install git+https://github.com/VH-Lab/Pyraview.git
```

This compiles the C++ during the install (CMake and a C++ compiler required)
and bundles the result the same way, so it works on any platform and Python
version. Add `@v0.4.0` to the URL to pin a release.

#### Option 3: Build the Library Separately
Useful when working on the C++ itself, since the Python package then picks up a
library you rebuild without reinstalling:

1.  **Build the C++ Library**:
    ```bash
    mkdir build && cd build
    cmake ..
    cmake --build .
    ```
    The shared library will be in `build/bin`.

2.  **Point the Package at It**:
    Set `PYRAVIEW_LIB` to the built library. It takes priority over the bundled
    copy.

    *   **Linux/macOS:**
        ```bash
        export PYRAVIEW_LIB=/path/to/Pyraview/build/bin/libpyraview.so
        ```
    *   **Windows (PowerShell):**
        ```powershell
        $env:PYRAVIEW_LIB="C:\path\to\Pyraview\build\bin\libpyraview.dll"
        ```

Pre-built libraries for use on their own (outside Python) are attached to each
[Release](../../releases) as per-OS zip files.

**Usage:**
```python
import pyraview
# See src/python/pyraview/__init__.py for API details
```

### C++

Pyraview uses CMake for building the core C++ shared library.

**Prerequisites:**
*   CMake (3.10 or later)
*   C++ Compiler (supporting C++11)

**Steps:**
1.  Clone the repository.
2.  Create a build directory:
    ```bash
    mkdir build
    cd build
    ```
3.  Configure and build the project:
    ```bash
    cmake ..
    cmake --build .
    ```
    On successful build, the shared library and the `run_tests` executable will be placed in `build/bin`.
