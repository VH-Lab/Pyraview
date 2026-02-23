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
            testCase.verifyEqual(ds.StartTime, 100.0);
            testCase.verifyEqual(length(ds.Files), 2);
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
