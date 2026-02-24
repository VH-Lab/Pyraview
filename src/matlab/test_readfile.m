function tests = test_readfile
    tests = functiontests(localfunctions);
end

function setupOnce(testCase)
    % Verify MEX file exists
    [~, mexName] = fileparts('pyraview');
    mexExt = mexext;
    fullMexPath = fullfile(pwd, 'src', 'matlab', ['pyraview.' mexExt]);

    if ~exist(fullMexPath, 'file')
        % Try relative to where this file is?
        currentFileDir = fileparts(mfilename('fullpath'));
        fullMexPath = fullfile(currentFileDir, ['pyraview.' mexExt]);
        if ~exist(fullMexPath, 'file')
             % If MEX is missing, we might be in an environment where we can't run this.
             % But we proceed assuming user has built it.
             warning('MEX file not found at expected location.');
        end
        addpath(currentFileDir);
        addpath(fullfile(currentFileDir, '+pyraview'));
    else
        addpath(fileparts(fullMexPath));
        addpath(fullfile(fileparts(fullMexPath), '+pyraview'));
    end
end

function test_read_basic(testCase)
    % Create a temporary file with known data
    filename = [tempname '.bin'];
    c = onCleanup(@() delete(filename));

    numChannels = 2;
    numSamples = 10;
    dataType = 'int16';
    itemSize = 2;

    % Header (1024 bytes)
    fid = fopen(filename, 'wb');

    % Magic
    fwrite(fid, 'PYRA', 'char');
    % Version
    fwrite(fid, 1, 'uint32');
    % DataType (2 for int16)
    fwrite(fid, 2, 'uint32');
    % Channels
    fwrite(fid, numChannels, 'uint32');
    % SampleRate
    fwrite(fid, 1000.0, 'double');
    % NativeRate
    fwrite(fid, 1000.0, 'double');
    % StartTime
    fwrite(fid, 0.0, 'double');
    % Decimation
    fwrite(fid, 1, 'uint32');
    % Reserved
    fwrite(fid, zeros(980, 1, 'uint8'), 'uint8');

    % Data: Planar layout
    % Ch1: 0,1, 2,3, ...
    % Ch2: 100,101, 102,103, ...

    dataCh1 = zeros(numSamples * 2, 1, dataType);
    for i = 1:numSamples
        dataCh1((i-1)*2 + 1) = (i-1)*2;     % Min
        dataCh1((i-1)*2 + 2) = (i-1)*2 + 1; % Max
    end

    dataCh2 = zeros(numSamples * 2, 1, dataType);
    for i = 1:numSamples
        dataCh2((i-1)*2 + 1) = 100 + (i-1)*2;     % Min
        dataCh2((i-1)*2 + 2) = 100 + (i-1)*2 + 1; % Max
    end

    fwrite(fid, dataCh1, dataType);
    fwrite(fid, dataCh2, dataType);

    fclose(fid);

    % Test read full
    d = pyraview.readFile(filename, 0, numSamples-1);

    testCase.verifyEqual(size(d), [numSamples, numChannels, 2]);
    testCase.verifyEqual(d(:, 1, 1), dataCh1(1:2:end));
    testCase.verifyEqual(d(:, 1, 2), dataCh1(2:2:end));
    testCase.verifyEqual(d(:, 2, 1), dataCh2(1:2:end));
    testCase.verifyEqual(d(:, 2, 2), dataCh2(2:2:end));

    % Test read partial
    s0 = 2; s1 = 4;
    dPart = pyraview.readFile(filename, s0, s1);
    testCase.verifyEqual(size(dPart), [3, numChannels, 2]);
    testCase.verifyEqual(dPart(:, 1, 1), dataCh1(5:2:9)); % Indices 2,3,4 -> 0-based index 4,6,8 in flat array? No.
    % Sample 2 is index 2. Flat index: 2*2 = 4 (Min), 5 (Max).
    % Sample 3 is index 3. Flat index: 6 (Min), 7 (Max).
    % Sample 4 is index 4. Flat index: 8 (Min), 9 (Max).
    % dataCh1(1:2:end) is Mins. Elements at 3, 4, 5 (1-based).

    expectedMinsCh1 = dataCh1(1:2:end);
    expectedMinsCh1 = expectedMinsCh1(s0+1 : s1+1);
    testCase.verifyEqual(dPart(:, 1, 1), expectedMinsCh1);

    % Test Inf
    dInf = pyraview.readFile(filename, -Inf, Inf);
    testCase.verifyEqual(dInf, d);
end
