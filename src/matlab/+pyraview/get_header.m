%GET_HEADER Read the Pyraview binary header from a file.
%
%   HEADER = pyraview.get_header(FILENAME) reads the standard 1024-byte header
%   from the specified Pyraview level file.
%
%   Inputs:
%       FILENAME - String or character vector specifying the path to the
%                  Pyraview level file.
%
%   Outputs:
%       HEADER   - Struct containing the following fields:
%                  * magic (char): "PYRA" magic string.
%                  * version (uint32): Format version.
%                  * dataType (uint32): Enum value for data type (0-9).
%                  * channelCount (uint32): Number of channels.
%                  * sampleRate (double): Sample rate of this level.
%                  * nativeRate (double): Original recording rate.
%                  * startTime (double): Start time of the recording.
%                  * decimationFactor (uint32): Cumulative decimation factor.
%
%   Example:
%       h = pyraview.get_header('data_L1.bin');
%       fprintf('Channels: %d, Rate: %.2f Hz\n', h.channelCount, h.sampleRate);
%
%   See also PYRAVIEW.READFILE, PYRAVIEW.DATASET
