classdef Dataset < handle
    properties
        NativeRate (1,1) double {mustBePositive} = 1
        NativeStartTime (1,1) double = 0
        Channels (1,1) double {mustBeInteger, mustBePositive} = 1
        DataType (1,1) string {mustBeMember(DataType, {'int8','uint8','int16','uint16','int32','uint32','int64','uint64','single','double'})} = "int16"
        decimationLevels (1,:) double {mustBeInteger, mustBeNonnegative} = []
        decimationSamplingRates (1,:) double {mustBePositive} = []
        decimationStartTime (1,:) double = []
        Files cell = {}
        FolderPath (1,1) string = ""
    end

    methods
        function obj = Dataset(folderPath, options)
            arguments
                folderPath (1,1) string = ""
                options.NativeRate (1,1) double = -1
                options.NativeStartTime (1,1) double = -9999999 % Sentinel
                options.Channels (1,1) double = -1
                options.DataType (1,1) string = ""
                options.decimationLevels (1,:) double = -1 % Sentinel for vector
                options.decimationSamplingRates (1,:) double = -1
                options.decimationStartTime (1,:) double = -9999999
                options.Files cell = {"<MISSING>"} % Sentinel
                options.FolderPath (1,1) string = ""
            end

            % Check if folderPath is a valid folder and not empty
            if folderPath ~= ""
                 if ~isfolder(folderPath)
                     error('Pyraview:InvalidFolder', 'Folder not found: %s', folderPath);
                 end
                 obj.FolderPath = folderPath;
                 obj.scanFolder();
            end

            % Override/Set properties if provided in options
            % Only override if the option is NOT the sentinel value

            if options.NativeRate ~= -1
                obj.NativeRate = options.NativeRate;
            end

            if options.NativeStartTime ~= -9999999
                obj.NativeStartTime = options.NativeStartTime;
            end

            if options.Channels ~= -1
                obj.Channels = options.Channels;
            end

            if options.DataType ~= ""
                obj.DataType = options.DataType;
            end

            if ~isequal(options.decimationLevels, -1)
                obj.decimationLevels = options.decimationLevels;
            end

            if ~isequal(options.decimationSamplingRates, -1)
                obj.decimationSamplingRates = options.decimationSamplingRates;
            end

            if ~isequal(options.decimationStartTime, -9999999)
                obj.decimationStartTime = options.decimationStartTime;
            end

            if ~isequal(options.Files, {"<MISSING>"})
                obj.Files = options.Files;
            end

            if options.FolderPath ~= ""
                 if ~isfolder(options.FolderPath)
                     error('Pyraview:InvalidFolder', 'Folder not found: %s', options.FolderPath);
                 end
                 obj.FolderPath = options.FolderPath;
                 obj.scanFolder();
            end
        end

        function scanFolder(obj)
             d = dir(fullfile(obj.FolderPath, '*_L*.bin'));
             if isempty(d)
                 return;
             end

             tempFiles = [];
             firstHeader = true;

             for i = 1:length(d)
                 fullPath = fullfile(d(i).folder, d(i).name);
                 try
                     h = pyraview.pyraview_get_header_mex(fullPath);

                     if firstHeader
                         obj.NativeRate = h.nativeRate;
                         obj.NativeStartTime = h.startTime;
                         obj.Channels = h.channelCount;
                         obj.DataType = obj.mapTypeToString(h.dataType);
                         firstHeader = false;
                     end

                     entry.decimation = double(h.decimationFactor);
                     entry.rate = h.sampleRate;
                     entry.start_time = h.startTime;
                     entry.name = d(i).name;

                     if isempty(tempFiles)
                         tempFiles = entry;
                     else
                         tempFiles(end+1) = entry;
                     end
                 catch e
                     warning('Failed to parse %s: %s', fullPath, e.message);
                 end
             end

             if ~isempty(tempFiles)
                 [~, I] = sort([tempFiles.decimation]);
                 tempFiles = tempFiles(I);

                 obj.decimationLevels = [tempFiles.decimation];
                 obj.decimationSamplingRates = [tempFiles.rate];
                 obj.decimationStartTime = [tempFiles.start_time];
                 obj.Files = {tempFiles.name};
             end
        end

        function str = mapTypeToString(obj, typeInt)
             switch typeInt
                case 0, str = 'int8';
                case 1, str = 'uint8';
                case 2, str = 'int16';
                case 3, str = 'uint16';
                case 4, str = 'int32';
                case 5, str = 'uint32';
                case 6, str = 'int64';
                case 7, str = 'uint64';
                case 8, str = 'single';
                case 9, str = 'double';
                otherwise, str = 'unknown';
            end
        end

        function [tVec, decimationLevel, sampleStart, sampleEnd] = getLevelForReading(obj, tStart, tEnd, pixels)
            duration = tEnd - tStart;
            if duration <= 0
                tVec = []; decimationLevel = []; sampleStart = []; sampleEnd = []; return;
            end

            targetRate = pixels / duration;

            % Gather candidates: [level_index, rate, start_time]
            candidates = [];

            % Level 0 (Raw Data)
            if ~isempty(obj.NativeRate)
                candidates = [candidates; 0, obj.NativeRate, obj.NativeStartTime];
            end

            % Decimated Levels (1..N)
            for i = 1:length(obj.decimationSamplingRates)
                if i <= length(obj.decimationStartTime)
                    sTime = obj.decimationStartTime(i);
                else
                    sTime = obj.NativeStartTime; % Fallback if not specified
                end
                candidates = [candidates; i, obj.decimationSamplingRates(i), sTime];
            end

            if isempty(candidates)
                tVec = []; decimationLevel = []; sampleStart = []; sampleEnd = []; return;
            end

            % Filter for sufficient rate
            validMask = candidates(:, 2) >= targetRate;
            validCandidates = candidates(validMask, :);

            if isempty(validCandidates)
                % All are too coarse (slow). Pick the finest available (highest rate).
                [~, maxIdx] = max(candidates(:, 2));
                chosen = candidates(maxIdx, :);
            else
                % Pick the coarsest sufficient (lowest rate among valid).
                [~, minIdx] = min(validCandidates(:, 2));
                chosen = validCandidates(minIdx, :);
            end

            decimationLevel = chosen(1);
            rate = chosen(2);
            sTime = chosen(3);

            % Calculate sample indices
            % samples are 0-based index from start of file/stream
            % t = sTime + idx/rate => idx = (t - sTime) * rate

            idxStart = floor((tStart - sTime) * rate);
            idxEnd = ceil((tEnd - sTime) * rate);

            if idxStart < 0, idxStart = 0; end
            if idxEnd < idxStart, idxEnd = idxStart; end

            sampleStart = idxStart;
            sampleEnd = idxEnd;

            % Calculate time vector
            numSamples = sampleEnd - sampleStart;
            if numSamples > 0
                indices = (0 : numSamples - 1)';
                tVec = sTime + (double(sampleStart) + double(indices)) / rate;
            else
                tVec = [];
            end
        end

        function [tVec, dataOut] = getData(obj, tStart, tEnd, pixels)
             [tVec, level, sStart, sEnd] = obj.getLevelForReading(tStart, tEnd, pixels);

             if isempty(level)
                 dataOut = []; return;
             end

             % Handle Level 0 fallback (Raw Data not currently supported via Files)
             if level == 0
                 if ~isempty(obj.Files)
                     % Fallback to Level 1
                     level = 1;
                     rate = obj.decimationSamplingRates(level);
                     if level <= length(obj.decimationStartTime)
                        sTime = obj.decimationStartTime(level);
                     else
                        sTime = obj.NativeStartTime;
                     end

                     sStart = floor((tStart - sTime) * rate);
                     sEnd = ceil((tEnd - sTime) * rate);
                     if sStart < 0, sStart = 0; end
                     if sEnd < sStart, sEnd = sStart; end

                     numSamples = sEnd - sStart;
                     if numSamples > 0
                         indices = (0 : numSamples - 1)';
                         tVec = sTime + (double(sStart) + double(indices)) / rate;
                     else
                         tVec = []; dataOut = []; return;
                     end
                 else
                     % No files at all
                     tVec = []; dataOut = []; return;
                 end
             end

             % Now reading from level > 0
             if level > length(obj.Files)
                 warning('Level %d requested but only %d files available.', level, length(obj.Files));
                 tVec = []; dataOut = []; return;
             end

             filename = obj.Files{level};
             if ~isempty(obj.FolderPath)
                 fullPath = fullfile(obj.FolderPath, filename);
             else
                 fullPath = filename;
             end

             if ~isfile(fullPath)
                 warning('File not found: %s', fullPath);
                 tVec = []; dataOut = []; return;
             end

             f = fopen(fullPath, 'rb');
             if f == -1
                 warning('Could not open file: %s', fullPath);
                 tVec = []; dataOut = []; return;
             end

             % Determine item size
             precision = obj.DataType;
             switch precision
                 case {'int8', 'uint8'}, itemSize = 1;
                 case {'int16', 'uint16'}, itemSize = 2;
                 case {'int32', 'uint32', 'single'}, itemSize = 4;
                 case {'int64', 'uint64', 'double'}, itemSize = 8;
                 otherwise
                     fclose(f);
                     error('Unknown data type: %s', precision);
             end

             % Calculate offsets
             % Header is 1024 bytes.
             fseek(f, 0, 'eof');
             fileSize = ftell(f);
             dataArea = fileSize - 1024;

             % Planar layout: [Ch1...][Ch2...]
             % Each channel has N samples. Each sample is Min/Max (2 values).
             % Total samples = dataArea / (Channels * 2 * itemSize)

             samplesPerChannel = floor(dataArea / (obj.Channels * 2 * itemSize));

             if sStart >= samplesPerChannel
                 fclose(f);
                 tVec = []; dataOut = []; return;
             end

             readEnd = sEnd;
             if readEnd > samplesPerChannel
                 readEnd = samplesPerChannel;
             end

             numSamples = readEnd - sStart;
             if numSamples <= 0
                 fclose(f);
                 tVec = []; dataOut = []; return;
             end

             % Adjust tVec if we truncated readEnd
             if readEnd < sEnd
                 indices = (0 : numSamples - 1)';
                 % Recalculate tVec based on actual read samples
                 % Need rate and sTime
                 rate = obj.decimationSamplingRates(level);
                  if level <= length(obj.decimationStartTime)
                        sTime = obj.decimationStartTime(level);
                     else
                        sTime = obj.NativeStartTime;
                     end
                 tVec = sTime + (double(sStart) + double(indices)) / rate;
             end

             % Read
             dataOut = zeros(numSamples, obj.Channels * 2, precision);

             for ch = 1:obj.Channels
                 % Offset for channel start
                 chOffset = 1024 + ((ch-1) * samplesPerChannel * 2 * itemSize);
                 % Offset for sample start (each sample is 2 values)
                 readOffset = chOffset + (sStart * 2 * itemSize);

                 fseek(f, readOffset, 'bof');
                 raw = fread(f, numSamples * 2, ['*' char(precision)]);

                 % raw is [Min0; Max0; Min1; Max1...]
                 if ~isempty(raw)
                     dataOut(1:length(raw)/2, (ch-1)*2 + 1) = raw(1:2:end);
                     dataOut(1:length(raw)/2, (ch-1)*2 + 2) = raw(2:2:end);
                 end
             end
             fclose(f);
        end
    end
end
