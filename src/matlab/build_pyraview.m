% build_pyraview.m
% Build script for Pyraview MEX

% Paths relative to src/matlab/
src_path = '../../src/c/pyraview.cpp';
include_path = '-I../../include';

% Source files inside +pyraview
mex_src = '+pyraview/pyraview.c';
header_src = '+pyraview/pyraview_get_header_mex.c';

% Output directory: +pyraview/
out_dir = '+pyraview';

fprintf('Building Pyraview MEX...\n');
try
    % Build the main engine MEX
    % Note: mex will compile .cpp file as C++.
    % It will link with .c file (compiled as C).
    % No OpenMP flags needed as we use C++11 std::thread
    fprintf('Building pyraview...\n');
    mex('-v', '-outdir', out_dir, '-output', 'pyraview', include_path, src_path, mex_src);
    fprintf('Build pyraview successful.\n');

    fprintf('Building pyraview_get_header_mex...\n');
    mex('-v', '-outdir', out_dir, '-output', 'pyraview_get_header_mex', include_path, src_path, header_src);
    fprintf('Build pyraview_get_header_mex successful.\n');
catch e
    fprintf('Build failed: %s\n', e.message);
    rethrow(e);
end
