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

#### Option 1: Pre-built Binaries (Recommended)
You can avoid compiling the C++ library by using the pre-built binaries provided in the releases.

1.  **Download the Library**:
    *   Go to the [Releases](../../releases) page.
    *   Download the zip file for your OS (e.g., `pyraview-Linux-x64.zip`, `pyraview-Windows-x64.zip`).
    *   Extract the contents to a folder of your choice (e.g., `~/libs/pyraview`).

2.  **Install the Python Package**:
    ```bash
    pip install git+https://github.com/VanHooserLab/Pyraview.git#subdirectory=src/python
    ```
    (Or clone the repo and run `pip install .` inside `src/python`).

3.  **Configure Library Path**:
    Set the `PYRAVIEW_LIB` environment variable to point to the extracted shared library file (`libpyraview.so`, `pyraview.dll`, or `libpyraview.dylib`).

    *   **Linux/macOS:**
        ```bash
        export PYRAVIEW_LIB=/path/to/extracted/libpyraview.so
        ```
    *   **Windows (PowerShell):**
        ```powershell
        $env:PYRAVIEW_LIB="C:\path\to\extracted\pyraview.dll"
        ```

#### Option 2: Build from Source
To build the C++ library yourself (requires CMake and a C++ compiler):

1.  **Build the C++ Library**:
    ```bash
    mkdir build && cd build
    cmake ..
    cmake --build .
    ```
    The shared library will be in `build/bin`.

2.  **Install the Python Package**:
    Navigate to `src/python` and run:
    ```bash
    pip install .
    ```

3.  **Configure Library Path**:
    Set `PYRAVIEW_LIB` to point to the built library in `build/bin`.

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
