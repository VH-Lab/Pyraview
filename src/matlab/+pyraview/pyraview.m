%PYRAVIEW Process raw data into multi-resolution pyramid files.
%
%   STATUS = pyraview.pyraview(DATA, PREFIX, STEPS, NATIVERATE, STARTTIME)
%   STATUS = pyraview.pyraview(DATA, PREFIX, STEPS, NATIVERATE, STARTTIME, APPEND)
%   STATUS = pyraview.pyraview(DATA, PREFIX, STEPS, NATIVERATE, STARTTIME, APPEND, NUMTHREADS)
%
%   This function processes a chunk of raw data (DATA) and writes it into
%   a set of decimated binary files (Level Files) suitable for efficient
%   multi-scale visualization.
%
%   Inputs:
%       DATA       - Numeric matrix of size (Samples x Channels).
%                    Supported types: int8, uint8, int16, uint16, int32, uint32,
%                    int64, uint64, single, double.
%                    Data is assumed to be interleaved by sample if provided
%                    as Samples x Channels (standard MATLAB convention).
%
%       PREFIX     - String or character vector specifying the base path and
%                    name for the output files. The function will generate
%                    files named:
%                        <PREFIX>_L1.bin
%                        <PREFIX>_L2.bin
%                        ...
%                        <PREFIX>_LN.bin
%
%       STEPS      - Vector of integers specifying the decimation factor for
%                    each level relative to the previous level.
%                    Example: [100, 10, 10] means:
%                        Level 1: Decimated by 100 relative to Raw.
%                        Level 2: Decimated by 10 relative to Level 1 (1000 total).
%                        Level 3: Decimated by 10 relative to Level 2 (10000 total).
%
%       NATIVERATE - Scalar double. The sampling rate of the original raw data
%                    in Hz. This is stored in the file header.
%
%       STARTTIME  - Scalar double. The start time of the recording in seconds.
%                    This is stored in the file header.
%
%       APPEND     - (Optional) Logical/Scalar. Default is false (0).
%                    If true (1), the function appends the processed data to
%                    existing level files.
%                    If false (0), existing files are overwritten.
%
%       NUMTHREADS - (Optional) Scalar integer. Default is 0 (Auto).
%                    Specifies the number of worker threads to use for parallel
%                    processing. If 0, the function automatically detects the
%                    number of available hardware concurrency.
%
%   Outputs:
%       STATUS     - Scalar double.
%                    0 on success.
%                    Negative values indicate errors (e.g., I/O error, type mismatch).
%                    If the function fails, it may also throw a MATLAB error.
%
%   File Format:
%       The generated files are binary files with a 1024-byte header followed
%       by the data. The data is stored in a planar layout (all samples for
%       Channel 1, then Channel 2, etc.). Each "sample" in the level file
%       consists of a Minimum and Maximum value pair to preserve signal
%       envelope information during decimation.
%
%   Example:
%       % Process 10 seconds of 1kHz data into 3 levels
%       fs = 1000;
%       data = randn(10000, 2); % 10s, 2 channels
%       steps = [10, 10];       % L1=10x, L2=100x
%
%       % Generates 'mydata_L1.bin' and 'mydata_L2.bin'
%       status = pyraview.pyraview(data, 'mydata', steps, fs, 0);
%
%   See also PYRAVIEW.READFILE, PYRAVIEW.DATASET
