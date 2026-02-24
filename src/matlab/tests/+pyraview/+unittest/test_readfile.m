classdef test_readfile < matlab.unittest.TestCase

    properties
        TempFilename
        CleanupObj
        NumChannels = 2
        NumSamples = 10
        DataType = 'int16'
        ItemSize = 2
        DataCh1
        DataCh2
    end

    methods(TestClassSetup)
        function setupPaths(testCase)
            % Verify MEX file exists
            [~, mexName] = fileparts('pyraview');
            mexExt = mexext;
            fullMexPath = fullfile(pwd, 'src', 'matlab', ['pyraview.' mexExt]);

            if ~exist(fullMexPath, 'file')
                % Try relative to where this file is
                currentFileDir = fileparts(mfilename('fullpath'));
                fullMexPath = fullfile(currentFileDir, ['pyraview.' mexExt]);
                if ~exist(fullMexPath, 'file')
                     warning('MEX file not found at expected location.');
                end
                addpath(currentFileDir);
                addpath(fullfile(currentFileDir, '+pyraview'));
            else
                addpath(fileparts(fullMexPath));
                addpath(fullfile(fileparts(fullMexPath), '+pyraview'));
            end
        end
    end

    methods(TestMethodSetup)
        function createTestFile(testCase)
            testCase.TempFilename = [tempname '.bin'];
            testCase.CleanupObj = onCleanup(@() delete(testCase.TempFilename));

            % Generate data
            testCase.DataCh1 = zeros(testCase.NumSamples * 2, 1, testCase.DataType);
            for i = 1:testCase.NumSamples
                testCase.DataCh1((i-1)*2 + 1) = (i-1)*2;     % Min
                testCase.DataCh1((i-1)*2 + 2) = (i-1)*2 + 1; % Max
            end

            testCase.DataCh2 = zeros(testCase.NumSamples * 2, 1, testCase.DataType);
            for i = 1:testCase.NumSamples
                testCase.DataCh2((i-1)*2 + 1) = 100 + (i-1)*2;     % Min
                testCase.DataCh2((i-1)*2 + 2) = 100 + (i-1)*2 + 1; % Max
            end

            % Write file
            fid = fopen(testCase.TempFilename, 'wb');

            % Header
            fwrite(fid, 'PYRA', 'char');
            fwrite(fid, 1, 'uint32');
            fwrite(fid, 2, 'uint32'); % int16
            fwrite(fid, testCase.NumChannels, 'uint32');
            fwrite(fid, 1000.0, 'double');
            fwrite(fid, 1000.0, 'double');
            fwrite(fid, 0.0, 'double');
            fwrite(fid, 1, 'uint32');
            fwrite(fid, zeros(980, 1, 'uint8'), 'uint8');

            % Data (Planar)
            fwrite(fid, testCase.DataCh1, testCase.DataType);
            fwrite(fid, testCase.DataCh2, testCase.DataType);

            fclose(fid);
        end
    end

    methods(TestMethodTeardown)
        function deleteTestFile(testCase)
            delete(testCase.CleanupObj);
        end
    end

    methods(Test)
        function testReadFull(testCase)
            d = pyraview.readFile(testCase.TempFilename, 0, testCase.NumSamples-1);

            testCase.verifyEqual(size(d), [testCase.NumSamples, testCase.NumChannels, 2]);
            testCase.verifyEqual(d(:, 1, 1), testCase.DataCh1(1:2:end)); % Ch1 Mins
            testCase.verifyEqual(d(:, 1, 2), testCase.DataCh1(2:2:end)); % Ch1 Maxs
            testCase.verifyEqual(d(:, 2, 1), testCase.DataCh2(1:2:end)); % Ch2 Mins
            testCase.verifyEqual(d(:, 2, 2), testCase.DataCh2(2:2:end)); % Ch2 Maxs
        end

        function testReadPartial(testCase)
            s0 = 2; s1 = 4;
            d = pyraview.readFile(testCase.TempFilename, s0, s1);

            numRead = s1 - s0 + 1;
            testCase.verifyEqual(size(d), [numRead, testCase.NumChannels, 2]);

            % Check Ch1 Mins
            expectedMins = testCase.DataCh1(1:2:end);
            expectedMins = expectedMins(s0+1 : s1+1); % Matlab 1-based indexing
            testCase.verifyEqual(d(:, 1, 1), expectedMins);
        end

        function testReadInf(testCase)
            d = pyraview.readFile(testCase.TempFilename, -Inf, Inf);

            testCase.verifyEqual(size(d), [testCase.NumSamples, testCase.NumChannels, 2]);
            testCase.verifyEqual(d(:, 1, 1), testCase.DataCh1(1:2:end));
        end

        function testReadEmpty(testCase)
            d = pyraview.readFile(testCase.TempFilename, 5, 4);
            testCase.verifyEqual(size(d), [0, testCase.NumChannels, 2]);
        end

        function testReadOutOfBounds(testCase)
            % Request beyond end, should be clamped
            d = pyraview.readFile(testCase.TempFilename, testCase.NumSamples-2, testCase.NumSamples+100);

            numRead = 2; % Samples 8 and 9 (0-based)
            testCase.verifyEqual(size(d, 1), numRead);
        end
    end
end
