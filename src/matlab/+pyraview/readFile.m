function d = readFile(filename, s0, s1)
%READFILE Reads a specific range of samples from a Pyraview level file.
%
%   D = pyraview.readFile(FILENAME, S0, S1) reads data from the file specified
%   by FILENAME, starting at sample index S0 and ending at sample index S1
%   (inclusive, 0-based indexing).
%
%   Inputs:
%       FILENAME - String or character vector specifying the path to the Pyraview level file.
%       S0       - Scalar numeric. The starting sample index (0-based).
%                  Can be -Inf to indicate the beginning of the file.
%       S1       - Scalar numeric. The ending sample index (0-based).
%                  Can be Inf to indicate the end of the file.
%
%   Outputs:
%       D        - A 3-D matrix of size (Samples x Channels x 2).
%                  The data type matches the file's internal data type.
%                  D(:, :, 1) contains the minimum values for each sample.
%                  D(:, :, 2) contains the maximum values for each sample.
%
%   Example:
%       % Read samples 100 to 200 from 'data_L1.bin'
%       d = pyraview.readFile('data_L1.bin', 100, 200);
%
%       % Read from the beginning to sample 500
%       d = pyraview.readFile('data_L1.bin', -Inf, 500);
%
%       % Read from sample 1000 to the end
%       d = pyraview.readFile('data_L1.bin', 1000, Inf);
%
%   Notes:
%       - Indices are clamped to the file's valid sample range.
%       - Returns an empty array if the requested range is invalid or empty.
%       - Pyraview files use a planar layout where channels are stored contiguously.
%       - Each "sample" in a level file consists of a Min/Max pair.

    if ~isfile(filename)
        error('Pyraview:FileNotFound', 'File not found: %s', filename);
    end

    % Read header
    try
        h = pyraview.get_header(filename);
    catch e
        error('Pyraview:HeaderError', 'Failed to read header: %s', e.message);
    end

    % Determine data type and item size
    switch h.dataType
        case 0, precision = 'int8'; itemSize = 1;
        case 1, precision = 'uint8'; itemSize = 1;
        case 2, precision = 'int16'; itemSize = 2;
        case 3, precision = 'uint16'; itemSize = 2;
        case 4, precision = 'int32'; itemSize = 4;
        case 5, precision = 'uint32'; itemSize = 4;
        case 6, precision = 'int64'; itemSize = 8;
        case 7, precision = 'uint64'; itemSize = 8;
        case 8, precision = 'single'; itemSize = 4;
        case 9, precision = 'double'; itemSize = 8;
        otherwise
            error('Pyraview:UnknownType', 'Unknown data type code: %d', h.dataType);
    end

    % Determine total samples
    dDir = dir(filename);
    fileSize = dDir.bytes;
    headerSize = 1024;
    dataArea = fileSize - headerSize;

    numChannels = double(h.channelCount);
    frameSize = numChannels * 2 * itemSize;
    totalSamples = floor(dataArea / frameSize);

    % Handle s0 and s1
    if isinf(s0) && s0 < 0
        startSample = 0;
    else
        startSample = s0;
    end

    if isinf(s1) && s1 > 0
        endSample = totalSamples - 1;
    else
        endSample = s1;
    end

    % Validate indices
    if startSample < 0
        startSample = 0;
    end

    if endSample >= totalSamples
        endSample = totalSamples - 1;
    end

    if startSample > endSample
        d = zeros(0, numChannels, 2, precision);
        return;
    end

    numSamplesToRead = endSample - startSample + 1;

    % Allocate output
    d = zeros(numSamplesToRead, numChannels, 2, precision);

    % Open file
    f = fopen(filename, 'rb');
    if f == -1
        error('Pyraview:FileOpenError', 'Could not open file: %s', filename);
    end

    cleanupObj = onCleanup(@() fclose(f));

    for ch = 1:numChannels
        % Calculate offset
        % Planar layout: [Header] [Ch1 Data] [Ch2 Data] ...
        % Ch Data size = totalSamples * 2 * itemSize

        chStartOffset = headerSize + (ch-1) * totalSamples * 2 * itemSize;
        readOffset = chStartOffset + startSample * 2 * itemSize;

        fseek(f, readOffset, 'bof');

        % Read min/max pairs
        % precision needs to be char for fread
        raw = fread(f, numSamplesToRead * 2, ['*' char(precision)]);

        if length(raw) < numSamplesToRead * 2
            warning('Pyraview:ShortRead', 'Short read on channel %d. Expected %d, got %d.', ch, numSamplesToRead*2, length(raw));
            % Fill what we got
            nRead = floor(length(raw)/2);
            d(1:nRead, ch, 1) = raw(1:2:2*nRead);
            d(1:nRead, ch, 2) = raw(2:2:2*nRead);
        else
            d(:, ch, 1) = raw(1:2:end);
            d(:, ch, 2) = raw(2:2:end);
        end
    end
end
