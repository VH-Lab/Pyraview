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
%   Notes:
%       - The file format is Interleaved (Sample-Major):
%         [Sample0_Ch0, Sample0_Ch1...][Sample1_Ch0, Sample1_Ch1...]
%       - Each "sample point" consists of a Min/Max pair.

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
    % Frame: Min/Max pair for ALL channels
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
    c = onCleanup(@() fclose(f));

    % Interleaved Format:
    % [Header]
    % [Sample 0 (Ch0..ChN)]
    % [Sample 1 (Ch0..ChN)]

    % Seek to Start Sample
    seekOffset = headerSize + startSample * frameSize;
    fseek(f, seekOffset, 'bof');

    % Read block
    % We read numSamplesToRead * frameSize bytes
    % Raw read into vector
    numElements = numSamplesToRead * numChannels * 2;
    raw = fread(f, numElements, ['*' char(precision)]);

    if length(raw) < numElements
        warning('Pyraview:ShortRead', 'Short read. Expected %d elements, got %d.', numElements, length(raw));
        % Truncate
        numSamplesToRead = floor(length(raw) / (numChannels * 2));
        raw = raw(1 : numSamplesToRead * numChannels * 2);
        d = d(1:numSamplesToRead, :, :, :);
    end

    % Reshape
    % Raw is [S0C0m S0C0M S0C1m S0C1M ... S1C0m ...]
    % Shape into (2, Channels, Samples) first?
    % MATLAB is Column Major.
    % Reshape to (2*Channels, Samples) -> Columns are Samples.
    % Data in file (Interleaved) is Sample 0 (all values), Sample 1 (all values).
    % So file is stored Row-Major if mapped to (Samples x [2*Ch]).
    % fread reads linearly.
    % raw = [S0_Vals, S1_Vals ...]
    % If we reshape to [2*Channels, NumSamples], MATLAB fills column 1 with raw(1..2*Ch).
    % raw(1..2*Ch) IS S0_Vals.
    % So reshape(raw, 2*numChannels, numSamplesToRead) puts Sample 0 in Column 1.
    % Transpose to (NumSamples, 2*numChannels).

    reshaped = reshape(raw, 2*numChannels, numSamplesToRead)';

    % Now reshaped is (Samples x [2*Ch]).
    % Columns: C0m C0M C1m C1M ...
    % We want d(Sample, Ch, 1) = C_Ch_m
    % We want d(Sample, Ch, 2) = C_Ch_M

    for ch = 1:numChannels
        d(:, ch, 1) = reshaped(:, 2*ch - 1);
        d(:, ch, 2) = reshaped(:, 2*ch);
    end
end
