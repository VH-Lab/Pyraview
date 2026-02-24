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
    omp_flags = {'COMPFLAGS="$COMPFLAGS /openmp"'};
else
    % GCC/Clang
    % Pass as separate arguments to avoid quoting issues
    omp_flags = {'CFLAGS="$CFLAGS -fopenmp"', 'LDFLAGS="$LDFLAGS -fopenmp"'};
end

% Output directory: +pyraview/
out_dir = '+pyraview';

fprintf('Building Pyraview MEX...\n');
try
    mex('-v', '-outdir', out_dir, '-output', 'pyraview_mex', include_path, src_path, mex_src, omp_flags{:});
    fprintf('Build pyraview_mex successful.\n');

    fprintf('Building pyraview_get_header_mex...\n');
    mex('-v', '-outdir', out_dir, '-output', 'pyraview_get_header_mex', include_path, src_path, header_src);
    fprintf('Build pyraview_get_header_mex successful.\n');
catch e
    fprintf('Build failed: %s\n', e.message);
    rethrow(e);
end
