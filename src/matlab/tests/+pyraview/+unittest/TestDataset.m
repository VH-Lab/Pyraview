classdef TestDataset < matlab.unittest.TestCase
    properties
        TestDataDir
    end

    methods(TestMethodSetup)
        function createData(testCase)
            testCase.TestDataDir = tempname;
            mkdir(testCase.TestDataDir);

            % Generate dummy data
            Fs = 1000;
            T = 10;
            t = 0:1/Fs:T-1/Fs;
            data = [sin(2*pi*t)' .* 1000, t' .* 100];
            data = int16(data);

            prefix = fullfile(testCase.TestDataDir, 'test_data');
            steps = [10, 10];
            start_time = 100.0;

            % Call MEX
            pyraview.pyraview_mex(data, prefix, steps, Fs, start_time);
        end
    end

    methods(TestMethodTeardown)
        function removeData(testCase)
            rmdir(testCase.TestDataDir, 's');
        end
    end

    methods(Test)
        function testConstructor(testCase)
            ds = pyraview.Dataset(testCase.TestDataDir);
            testCase.verifyEqual(ds.NativeRate, 1000);
            testCase.verifyEqual(ds.NativeStartTime, 100.0);
            testCase.verifyEqual(length(ds.Files), 2);
            testCase.verifyTrue(iscell(ds.Files));
        end

        function testValidation(testCase)
            % Test invalid inputs
            % Negative rate
            testCase.verifyError(@() pyraview.Dataset("NativeRate", -1), ?MException);

            % Invalid data type
            testCase.verifyError(@() pyraview.Dataset("DataType", "invalid"), ?MException);

            % Invalid channels (non-integer)
            testCase.verifyError(@() pyraview.Dataset("Channels", 1.5), ?MException);
        end

        function testLevelForReading(testCase)
            ds = pyraview.Dataset(testCase.TestDataDir);
            % Duration 10s.
            % Levels: Native=1000, L1=100, L2=10.

            % Case 1: High res demand. Rate >= 500.
            % Only Native (1000) qualifies.
            % Since we don't track raw file, but getLevelForReading should return 0.
            pixels = 5000; % 500 Hz
            [~, level] = ds.getLevelForReading(100, 110, pixels);
            testCase.verifyEqual(level, 0);

            % Case 2: Medium res demand. Rate >= 50.
            % Candidates: Native(1000), L1(100).
            % Should pick coarsest valid -> L1(100) -> Level 1.
            pixels = 500; % 50 Hz
            [~, level] = ds.getLevelForReading(100, 110, pixels);
            testCase.verifyEqual(level, 1);

            % Case 3: Low res demand. Rate >= 5.
            % Candidates: Native(1000), L1(100), L2(10).
            % Coarsest valid -> L2(10) -> Level 2.
            pixels = 50; % 5 Hz
            [~, level] = ds.getLevelForReading(100, 110, pixels);
            testCase.verifyEqual(level, 2);

            % Case 4: Manual initialization
            ds2 = pyraview.Dataset('NativeRate', 2000, 'NativeStartTime', 0);
            testCase.verifyEqual(ds2.NativeRate, 2000);
            testCase.verifyEmpty(ds2.Files);
            % getLevelForReading should return 0 for any demand as it's the only level
            [~, level] = ds2.getLevelForReading(0, 10, 100);
            testCase.verifyEqual(level, 0);
        end

        function testGetData(testCase)
            ds = pyraview.Dataset(testCase.TestDataDir);
            t_start = 100.0;
            t_end = 110.0;
            pixels = 50; % low resolution

            [t, d] = ds.getData(t_start, t_end, pixels);

            testCase.verifyNotEmpty(t);
            testCase.verifyEqual(size(d, 2), 4); % 2 ch * 2

            % Check basic values
            % d(:, 2) is Max Ch0. Should include positive sine peaks (approx 1000)
            mx = max(d(:, 2));
            testCase.verifyTrue(mx > 900);
        end
    end
end
