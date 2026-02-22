% test_pyraview.m
% Simple test script

% Cleanup
if exist('test_matlab_L1.bin', 'file')
    delete('test_matlab_L1.bin');
end

% 1. Create data (1000 samples, 2 channels, single precision)
data = rand(1000, 2, 'single');
steps = [10];
prefix = 'test_matlab';
nativeRate = 1000.0;

% 2. Run MEX
try
    status = pyraview_mex(data, prefix, steps, nativeRate);
catch e
    error('MEX failed: %s. Did you run build_pyraview?', e.message);
end

% 3. Check status
if status ~= 0
    error('Return code was not 0');
end

% 4. Check file existence
if ~exist([prefix '_L1.bin'], 'file')
    error('Output file not created');
end

% 5. Check file size
d = dir([prefix '_L1.bin']);
expectedSize = 1024 + 100 * 2 * 2 * 4; % Header + 100samples * 2channels * 2(min/max) * 4bytes
if d.bytes ~= expectedSize
    error('Output file size incorrect: %d vs %d', d.bytes, expectedSize);
end

disp('Matlab test passed!');
