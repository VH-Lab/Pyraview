% test_pyraview.m
% Comprehensive Matlab Test

fprintf('Running Pyraview Matlab Tests...\n');

% Types to test
types = {'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64', 'single', 'double'};
bytes_per_type = [1, 1, 2, 2, 4, 4, 8, 8, 4, 8];

channels_list = [1, 10];
failures = 0;

for t = 1:length(types)
    for c = 1:length(channels_list)
        type_str = types{t};
        n_ch = channels_list(c);
        bpt = bytes_per_type(t);

        fprintf('Testing %s, %d channels...', type_str, n_ch);

        % Generate data: 1000 samples x N channels
        % Matlab uses column-major by default, so Samples x Channels is naturally CxS layout in memory if transposed?
        % No. Matlab is Column-Major.
        % A (Samples x Channels) matrix is stored as: All samples of Ch1, then All samples of Ch2...
        % This is exactly what Pyraview calls "CxS" (Layout=1).

        data = cast(zeros(1000, n_ch), type_str);

        prefix = sprintf('test_matlab_%s_%d', type_str, n_ch);

        % Cleanup
        outfile = [prefix '_L1.bin'];
        if exist(outfile, 'file'), delete(outfile); end

        try
            status = pyraview_mex(data, prefix, [10], 1000.0);
            if status ~= 0
                fprintf('FAILED (status %d)\n', status);
                failures = failures + 1;
                continue;
            end

            if ~exist(outfile, 'file')
                fprintf('FAILED (no file)\n');
                failures = failures + 1;
                continue;
            end

            % Check size
            d = dir(outfile);
            expected_size = 1024 + (1000/10) * 2 * n_ch * bpt;
            if d.bytes ~= expected_size
                fprintf('FAILED (size mismatch: %d vs %d)\n', d.bytes, expected_size);
                failures = failures + 1;
                continue;
            end

            fprintf('OK\n');
            delete(outfile);

        catch e
            fprintf('FAILED (exception: %s)\n', e.message);
            failures = failures + 1;
        end
    end
end

if failures > 0
    error('Total Failures: %d', failures);
else
    fprintf('ALL TESTS PASSED\n');
end
