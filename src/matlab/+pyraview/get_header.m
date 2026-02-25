function header = get_header(filename)
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

    if ~isfile(filename)
        error('Pyraview:FileNotFound', 'File not found: %s', filename);
    end

    % Open file for binary reading, little-endian
    fid = fopen(filename, 'rb', 'ieee-le');
    if fid == -1
        error('Pyraview:FileOpenError', 'Could not open file: %s', filename);
    end

    % Ensure file is closed on exit
    c = onCleanup(@() fclose(fid));

    % Read 1024 byte header block
    % Structure layout (packed/aligned to 64 bytes, but members are standard sizes):
    % char magic[4];              // 0
    % uint32_t version;           // 4
    % uint32_t dataType;          // 8
    % uint32_t channelCount;      // 12
    % double sampleRate;          // 16
    % double nativeRate;          // 24
    % double startTime;           // 32
    % uint32_t decimationFactor;  // 40
    % uint8_t reserved[980];      // 44 .. 1023

    % Read Magic
    magicBytes = fread(fid, 4, '*char')';
    if ~strcmp(magicBytes, 'PYRA')
        error('Pyraview:InvalidHeader', 'Invalid magic string. Expected "PYRA", got "%s"', magicBytes);
    end
    header.magic = magicBytes;

    header.version = fread(fid, 1, 'uint32');
    header.dataType = fread(fid, 1, 'uint32');
    header.channelCount = fread(fid, 1, 'uint32');
    header.sampleRate = fread(fid, 1, 'double');
    header.nativeRate = fread(fid, 1, 'double');
    header.startTime = fread(fid, 1, 'double');
    header.decimationFactor = fread(fid, 1, 'uint32');

    % Verify size? Optional but good for sanity.
    % We read 4 + 4 + 4 + 4 + 8 + 8 + 8 + 4 = 44 bytes.
    % Remaining 980 bytes are reserved.

    % No need to read reserved unless we want to validate file size.
end
