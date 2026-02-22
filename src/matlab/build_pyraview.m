% build_pyraview.m
% Build script for Pyraview MEX

src_path = '../../src/c/pyraview.c';
mex_src = 'pyraview_mex.c';
include_path = '-I../../include';

% OpenMP flags (adjust for OS/Compiler)
if ispc
    % Windows MSVC usually supports /openmp
    omp_flags = 'COMPFLAGS="$COMPFLAGS /openmp"';
else
    % GCC/Clang
    omp_flags = 'CFLAGS="$CFLAGS -fopenmp" LDFLAGS="$LDFLAGS -fopenmp"';
end

fprintf('Building Pyraview MEX...\n');
try
    mex('-v', include_path, src_path, mex_src, omp_flags);
    fprintf('Build successful.\n');
catch e
    fprintf('Build failed: %s\n', e.message);
end
