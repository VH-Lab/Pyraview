function tests = test_pyraview
    tests = functiontests(localfunctions);
end

function setupOnce(testCase)
    % Verify MEX file exists in +pyraview
    [~, mexName] = fileparts('pyraview');
    mexExt = mexext;
    % Expected path: src/matlab/+pyraview/pyraview.mex*
    fullMexPath = fullfile(pwd, 'src', 'matlab', '+pyraview', ['pyraview.' mexExt]);

    % If run via run-tests action, current folder might be repo root.
    if ~exist(fullMexPath, 'file')
        % Try relative to where this file is?
        currentFileDir = fileparts(mfilename('fullpath'));
        % Assuming this test is in src/matlab, the mex is in +pyraview/
        fullMexPath = fullfile(currentFileDir, '+pyraview', ['pyraview.' mexExt]);
        if ~exist(fullMexPath, 'file')
            % Fallback for direct path?
            error('MEX file not found: %s', fullMexPath);
        end
        addpath(currentFileDir); % Add src/matlab to path
    else
        addpath(fileparts(fileparts(fullMexPath))); % Add src/matlab to path
    end

    fprintf('Using MEX: %s\n', fullMexPath);
end

function test_comprehensive(testCase)
    types = {'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64', 'single', 'double'};
    bytes_per_type = [1, 1, 2, 2, 4, 4, 8, 8, 4, 8];
    channels_list = [1, 10];

    for t = 1:length(types)
        for c = 1:length(channels_list)
            type_str = types{t};
            n_ch = channels_list(c);
            bpt = bytes_per_type(t);

            fprintf('Testing %s, %d channels...', type_str, n_ch);

            data = cast(zeros(1000, n_ch), type_str);
            prefix = sprintf('test_matlab_%s_%d', type_str, n_ch);
            outfile = [prefix '_L1.bin'];

            % Ensure cleanup happens even on failure
            c = onCleanup(@() cleanupFile(outfile));

            try
                % Call pyraview.pyraview
                status = pyraview.pyraview(data, prefix, [10], 1000.0, 0);
                testCase.verifyEqual(status, 0, 'Status should be 0');

                testCase.verifyTrue(exist(outfile, 'file') == 2, 'Output file should exist');

                d = dir(outfile);
                expected_size = 1024 + (1000/10) * 2 * n_ch * bpt;
                testCase.verifyEqual(d.bytes, expected_size, 'File size mismatch');

                fprintf('OK\n');
            catch e
                fprintf('FAILED: %s\n', e.message);
                rethrow(e);
            end
        end
    end
end

function cleanupFile(filename)
    if exist(filename, 'file')
        delete(filename);
    end
end
