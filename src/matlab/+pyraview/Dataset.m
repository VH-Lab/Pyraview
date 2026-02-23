classdef Dataset < handle
    properties
        FolderPath
        Files
        NativeRate
        StartTime
        Channels
        DataType
    end

    methods
        function obj = Dataset(folderPath)
            if ~isfolder(folderPath)
                error('Pyraview:InvalidFolder', 'Folder not found: %s', folderPath);
            end
            obj.FolderPath = folderPath;
            obj.Files = struct('decimation', {}, 'rate', {}, 'path', {}, 'start_time', {});

            d = dir(fullfile(folderPath, '*_L*.bin'));
            if isempty(d)
                error('Pyraview:NoFiles', 'No Pyraview files found in folder.');
            end

            % Compile MEX if needed? Ideally user compiles before use.

            for i = 1:length(d)
                fullPath = fullfile(d(i).folder, d(i).name);
                try
                    h = pyraview.pyraview_get_header_mex(fullPath);
                    if isempty(obj.NativeRate)
                        obj.NativeRate = h.nativeRate;
                        obj.StartTime = h.startTime;
                        obj.Channels = h.channelCount;
                        obj.DataType = h.dataType;
                    end

                    idx = length(obj.Files) + 1;
                    obj.Files(idx).decimation = h.decimationFactor;
                    obj.Files(idx).rate = h.sampleRate;
                    obj.Files(idx).path = fullPath;
                    obj.Files(idx).start_time = h.startTime;
                catch e
                    warning('Failed to parse %s: %s', fullPath, e.message);
                end
            end

            if isempty(obj.Files)
                error('Pyraview:NoFiles', 'No valid Pyraview files loaded.');
            end

            % Sort by decimation (ascending -> High Res first)
            [~, I] = sort([obj.Files.decimation]);
            obj.Files = obj.Files(I);
        end

        function [tVec, dataOut] = getData(obj, tStart, tEnd, pixels)
            duration = tEnd - tStart;
            if duration <= 0
                tVec = []; dataOut = []; return;
            end

            targetRate = pixels / duration;

            % Find optimal file
            % Files are sorted by decimation ASC (High Res -> Low Res)
            % Rates are DESC (High Rate -> Low Rate)
            % We want rate >= targetRate, but as low as possible (coarsest sufficient)

            selectedIdx = 1; % Default high res
            candidates = find([obj.Files.rate] >= targetRate);
            if ~isempty(candidates)
                % Pick the one with min rate (which is the last one in candidates if sorted by rate desc?)
                % Files sorted by decimation ASC => Rate DESC.
                % Candidates are indices of files with enough rate.
                % We want the SMALLEST rate among them.
                % Since rates are descending, this is the LAST candidate.
                selectedIdx = candidates(end);
            end

            fileInfo = obj.Files(selectedIdx);

            % Aperture (3x window)
            tCenter = (tStart + tEnd) / 2;
            apStart = tCenter - 1.5 * duration;
            apEnd = tCenter + 1.5 * duration;

            if apStart < obj.StartTime
                apStart = obj.StartTime;
            end

            rate = fileInfo.rate;
            idxStart = floor((apStart - obj.StartTime) * rate);
            idxEnd = ceil((apEnd - obj.StartTime) * rate);

            if idxStart < 0, idxStart = 0; end
            if idxEnd <= idxStart
                tVec = []; dataOut = []; return;
            end

            numSamples = idxEnd - idxStart;

            % Reading logic (Channel-Major Planar based on C implementation)
            % File: Header(1024) + [Ch0 Data] + [Ch1 Data] ...
            % Data size per sample = 2 * ItemSize (Min/Max)

            f = fopen(fileInfo.path, 'rb');
            fseek(f, 0, 'eof');
            fileSize = ftell(f);

            % Determine item size
            switch obj.DataType
                case 0, dt = 'int8'; itemSize = 1;
                case 1, dt = 'uint8'; itemSize = 1;
                case 2, dt = 'int16'; itemSize = 2;
                case 3, dt = 'uint16'; itemSize = 2;
                case 4, dt = 'int32'; itemSize = 4;
                case 5, dt = 'uint32'; itemSize = 4;
                case 6, dt = 'int64'; itemSize = 8;
                case 7, dt = 'uint64'; itemSize = 8;
                case 8, dt = 'single'; itemSize = 4;
                case 9, dt = 'double'; itemSize = 8;
                otherwise, error('Unknown type');
            end

            dataArea = fileSize - 1024;
            frameSize = obj.Channels * 2 * itemSize;
            % Wait, if it's planar, samplesPerChannel = dataArea / (Channels * 2 * ItemSize)
            samplesPerChannel = floor(dataArea / (obj.Channels * 2 * itemSize));

            if idxStart >= samplesPerChannel
                fclose(f);
                tVec = []; dataOut = []; return;
            end

            if idxEnd > samplesPerChannel
                idxEnd = samplesPerChannel;
                numSamples = idxEnd - idxStart;
            end

            % Read
            % Output: [Samples x (Channels*2)]
            dataOut = zeros(numSamples, obj.Channels * 2, dt);

            for ch = 1:obj.Channels
                chOffset = 1024 + ((ch-1) * samplesPerChannel * 2 * itemSize);
                readOffset = chOffset + (idxStart * 2 * itemSize);

                fseek(f, readOffset, 'bof');
                raw = fread(f, numSamples * 2, ['*' dt]);

                % raw is column vector [Min0; Max0; Min1; Max1...]
                % We want to map to dataOut columns (2*ch-1) and (2*ch)
                % MATLAB is 1-based.
                % Col 1: Min, Col 2: Max for Ch1

                % raw(1:2:end) -> Min
                % raw(2:2:end) -> Max
                if ~isempty(raw)
                    dataOut(1:length(raw)/2, (ch-1)*2 + 1) = raw(1:2:end);
                    dataOut(1:length(raw)/2, (ch-1)*2 + 2) = raw(2:2:end);
                end
            end
            fclose(f);

            % Time vector
            % t = start + (idx / rate)
            indices = (idxStart : (idxStart + numSamples - 1))';
            tVec = obj.StartTime + double(indices) / rate;
        end
    end
end
