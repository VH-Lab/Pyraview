% build_pyraview.m
% Build script for Pyraview MEX

% Paths relative to src/matlab/
src_path = '../../src/c/pyraview.c';
include_path = '-I../../include';

% Source files inside +pyraview
mex_src = '+pyraview/pyraview_mex.c';
header_src = '+pyraview/pyraview_get_header_mex.c';

% OpenMP flags (adjust for OS/Compiler)
if ispc
    % Windows MSVC usually supports /openmp
    omp_flags = 'COMPFLAGS="$COMPFLAGS /openmp"';
else
    % GCC/Clang
    % We need to pass the flags as separate arguments or correctly formatted
    omp_flags = 'CFLAGS="$CFLAGS -fopenmp" LDFLAGS="$LDFLAGS -fopenmp"';
    % The previous attempt caused quoting issues.
    % Trying with simpler quoting for linux runner environment
    omp_flags = 'CFLAGS=''$CFLAGS -fopenmp'' LDFLAGS=''$LDFLAGS -fopenmp''';
end

% Output directory: +pyraview/
out_dir = '+pyraview';

fprintf('Building Pyraview MEX...\n');
try
    mex('-v', '-outdir', out_dir, include_path, src_path, mex_src, omp_flags);
    fprintf('Build pyraview_mex successful.\n');

    fprintf('Building pyraview_get_header_mex...\n');
    mex('-v', '-outdir', out_dir, include_path, src_path, header_src);
    fprintf('Build pyraview_get_header_mex successful.\n');
catch e
    fprintf('Build failed: %s\n', e.message);
    rethrow(e);
end
