function varargout = pyraview(varargin)
%PYRAVIEW Process raw data into multi-resolution pyramid files.
%
%   STATUS = pyraview.pyraview(DATA, PREFIX, STEPS, NATIVERATE, STARTTIME)
%   STATUS = pyraview.pyraview(DATA, PREFIX, STEPS, NATIVERATE, STARTTIME, APPEND)
%   STATUS = pyraview.pyraview(DATA, PREFIX, STEPS, NATIVERATE, STARTTIME, APPEND, NUMTHREADS)
%
%   This function processes a chunk of raw data (DATA) and writes it into
%   a set of decimated binary files (Level Files) suitable for efficient
%   multi-scale visualization.
%
%   NOTE ON THIS FILE:
%       The real implementation of PYRAVIEW is a compiled MEX binary
%       (pyraview.mexa64 / pyraview.mexw64 / pyraview.mexmaca64, etc.).
%       When that binary is present next to this file, MATLAB calls it
%       directly and this .m file is never executed. This .m file only
%       runs as a *fallback* when the MEX binary for your platform is
%       missing. In that case it attempts to download the correct binary
%       from the latest GitHub release and then re-runs the call. If the
%       download fails, it raises a clear error explaining what to do.
%
%   Inputs:
%       DATA       - Numeric matrix of size (Samples x Channels).
%                    Supported types: int8, uint8, int16, uint16, int32, uint32,
%                    int64, uint64, single, double.
%                    Data is assumed to be interleaved by sample if provided
%                    as Samples x Channels (standard MATLAB convention).
%
%       PREFIX     - String or character vector specifying the base path and
%                    name for the output files. The function will generate
%                    files named:
%                        <PREFIX>_L1.bin
%                        <PREFIX>_L2.bin
%                        ...
%                        <PREFIX>_LN.bin
%
%       STEPS      - Vector of integers specifying the decimation factor for
%                    each level relative to the previous level.
%                    Example: [100, 10, 10] means:
%                        Level 1: Decimated by 100 relative to Raw.
%                        Level 2: Decimated by 10 relative to Level 1 (1000 total).
%                        Level 3: Decimated by 10 relative to Level 2 (10000 total).
%
%       NATIVERATE - Scalar double. The sampling rate of the original raw data
%                    in Hz. This is stored in the file header.
%
%       STARTTIME  - Scalar double. The start time of the recording in seconds.
%                    This is stored in the file header.
%
%       APPEND     - (Optional) Logical/Scalar. Default is false (0).
%                    If true (1), the function appends the processed data to
%                    existing level files.
%                    If false (0), existing files are overwritten.
%
%       NUMTHREADS - (Optional) Scalar integer. Default is 0 (Auto).
%                    Specifies the number of worker threads to use for parallel
%                    processing. If 0, the function automatically detects the
%                    number of available hardware concurrency.
%
%   Outputs:
%       STATUS     - Scalar double.
%                    0 on success.
%                    Negative values indicate errors (e.g., I/O error, type mismatch).
%                    If the function fails, it may also throw a MATLAB error.
%
%   File Format:
%       The generated files are binary files with a 1024-byte header followed
%       by the data. The data is stored in a planar layout (all samples for
%       Channel 1, then Channel 2, etc.). Each "sample" in the level file
%       consists of a Minimum and Maximum value pair to preserve signal
%       envelope information during decimation.
%
%   Example:
%       % Process 10 seconds of 1kHz data into 3 levels
%       fs = 1000;
%       data = randn(10000, 2); % 10s, 2 channels
%       steps = [10, 10];       % L1=10x, L2=100x
%
%       % Generates 'mydata_L1.bin' and 'mydata_L2.bin'
%       status = pyraview.pyraview(data, 'mydata', steps, fs, 0);
%
%   See also PYRAVIEW.READFILE, PYRAVIEW.DATASET

    % Guard against infinite recursion: if we get here a second time within
    % the same call, MATLAB is still dispatching to this .m file rather than
    % to the (now downloaded) MEX binary.
    persistent inFallback
    if isempty(inFallback)
        inFallback = false;
    end

    thisDir = fileparts(mfilename('fullpath'));   % the +pyraview package folder
    ext     = mexext;                              % e.g. 'mexa64', 'mexw64', 'mexmaca64'
    mexName = ['pyraview.' ext];
    mexFile = fullfile(thisDir, mexName);

    if inFallback
        error('Pyraview:MexDispatchFailed', ...
            ['The Pyraview MEX binary was placed at\n    %s\n' ...
             'but MATLAB is still calling the placeholder .m file instead of the\n' ...
             'compiled binary. This usually clears up after refreshing MATLAB''s\n' ...
             'function cache. Please run:\n\n' ...
             '    clear functions; rehash toolboxcache\n\n' ...
             'or simply restart MATLAB, then try your command again.'], ...
             mexFile);
    end

    % If the binary already exists on disk but we still landed here, it failed
    % to load (e.g. blocked by macOS Gatekeeper, or wrong architecture). Do not
    % re-download; try to unblock and re-dispatch below.
    if ~isfile(mexFile)
        localDownloadMex(mexFile, mexName);
    else
        fprintf('Pyraview: Found %s but it did not load. Attempting to refresh...\n', mexName);
    end

    % Best effort on macOS: remove the quarantine attribute that Gatekeeper
    % adds to freshly-downloaded binaries and that blocks MEX loading.
    if ismac
        try
            system(sprintf('xattr -dr com.apple.quarantine "%s"', mexFile));
        catch
            % Non-fatal; the user can still run pyraview.macOneTime().
        end
    end

    if ~isfile(mexFile)
        error('Pyraview:MexMissing', ...
            ['Expected the Pyraview MEX binary at\n    %s\n' ...
             'but it is not present after the download attempt. Please install the\n' ...
             'Pyraview toolbox from the Releases page, or build from source with\n' ...
             'build_pyraview.'], mexFile);
    end

    % Make MATLAB aware of the new file. rehash refreshes the function/file
    % cache for folders on the path; we issue both the path and toolbox forms
    % so it works whether Pyraview was added from source or installed as a
    % toolbox.
    rehash path;
    try
        rehash toolboxcache;   % harmless if this folder is not a toolbox
    catch
    end

    % Only re-dispatch if the MEX binary is actually the version MATLAB would
    % now resolve. Immediately after writing the file, the dispatcher may still
    % point at this .m for a beat; recursing then would just loop back here. By
    % consulting WHICH first we avoid that and, in the rare case the binary is
    % not yet visible, hand the user a clear "run it again" message instead of a
    % confusing internal error.
    resolved = which('pyraview.pyraview');
    if ~isempty(resolved) && endsWith(lower(resolved), ['.' lower(ext)])
        inFallback = true;
        try
            [varargout{1:nargout}] = pyraview.pyraview(varargin{:});
        catch ME
            inFallback = false;
            rethrow(ME);
        end
        inFallback = false;
    else
        error('Pyraview:MexInstalledRerun', ...
            ['Pyraview successfully installed the MEX binary:\n    %s\n\n' ...
             'MATLAB has not refreshed its function cache to see it yet, so it\n' ...
             'cannot complete this call automatically. Simply run your command\n' ...
             'ONE more time and it will use the binary.\n\n' ...
             'If it still does not pick it up, run:\n' ...
             '    clear functions; rehash toolboxcache\n' ...
             'or restart MATLAB.'], mexFile);
    end
end

% -------------------------------------------------------------------------
function localDownloadMex(mexFile, mexName)
%LOCALDOWNLOADMEX Download the platform MEX binary from the latest GitHub release.

    repoSlug = 'VH-Lab/Pyraview';
    url = sprintf('https://github.com/%s/releases/latest/download/%s', repoSlug, mexName);

    fprintf(['Pyraview: The MEX binary for your platform (%s) was not found.\n' ...
             'Pyraview: Downloading the latest release from GitHub...\n' ...
             'Pyraview:   %s\n'], mexName, url);

    tmpFile = [mexFile '.download'];
    if isfile(tmpFile)
        delete(tmpFile);
    end

    ok = false;
    reasons = {};

    % Attempt 1: MATLAB's built-in websave (follows redirects, no external deps).
    try
        opts = weboptions('Timeout', 120, 'ContentType', 'binary');
        websave(tmpFile, url, opts);
        ok = isfile(tmpFile) && (dir_bytes(tmpFile) > 0);
        if ~ok
            reasons{end+1} = 'websave produced an empty file';
        end
    catch webErr
        reasons{end+1} = sprintf('websave: %s', webErr.message);
    end

    % Attempt 2: fall back to system curl (present on Windows 10+, macOS, Linux).
    if ~ok
        try
            cmd = sprintf('curl -L -f -s -S -o "%s" "%s"', tmpFile, url);
            [status, out] = system(cmd);
            if status == 0 && isfile(tmpFile) && dir_bytes(tmpFile) > 0
                ok = true;
            else
                reasons{end+1} = sprintf('curl (exit %d): %s', status, strtrim(out));
            end
        catch curlErr
            reasons{end+1} = sprintf('curl: %s', curlErr.message);
        end
    end

    if ~ok
        if isfile(tmpFile)
            delete(tmpFile);
        end
        error('Pyraview:DownloadFailed', ...
            ['Could not download the Pyraview MEX binary for your platform.\n\n' ...
             '    Platform binary : %s\n' ...
             '    Download URL    : %s\n\n' ...
             'Reasons:\n    %s\n\n' ...
             'How to fix this:\n' ...
             '  1. Check your internet connection / proxy and try again.\n' ...
             '  2. Download %s manually from\n' ...
             '         https://github.com/%s/releases/latest\n' ...
             '     and place it in\n         %s\n' ...
             '  3. Or install the Pyraview toolbox (.mltbx) from that Releases page.\n' ...
             '  4. Or build it from source by running build_pyraview.\n' ...
             '\nIf no binary exists for your platform, building from source\n' ...
             '(build_pyraview) is the recommended option.'], ...
             mexName, url, strjoin(reasons, sprintf('\n    ')), ...
             mexName, repoSlug, fileparts(mexFile));
    end

    % Move the completed download into place.
    [mvOk, mvMsg] = movefile(tmpFile, mexFile, 'f');
    if ~mvOk
        if isfile(tmpFile)
            delete(tmpFile);
        end
        error('Pyraview:InstallFailed', ...
            ['Downloaded the Pyraview MEX binary but could not write it to\n' ...
             '    %s\n(%s)\n' ...
             'Please check that you have write permission to that folder, or\n' ...
             'install the toolbox from the Releases page instead.'], mexFile, mvMsg);
    end

    fprintf('Pyraview: Successfully installed %s.\n', mexName);
end

% -------------------------------------------------------------------------
function n = dir_bytes(f)
%DIR_BYTES Return the size of file F in bytes (0 if it does not exist).
    d = dir(f);
    if isempty(d)
        n = 0;
    else
        n = d(1).bytes;
    end
end
