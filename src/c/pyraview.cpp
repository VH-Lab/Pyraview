#define _FILE_OFFSET_BITS 64
#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include <thread>
#include <vector>
#include <mutex>
#include <condition_variable>
#include <atomic>

#ifdef _WIN32
  #include <windows.h>
  #define pv_fseek _fseeki64
  #define pv_ftell _ftelli64
#else
  #include <unistd.h>
  #define pv_fseek fseeko
  #define pv_ftell ftello
#endif

#include <pyraview_header.h>

// Utility: Write header
static void pv_write_header(FILE* f, int channels, int type, double sampleRate, double nativeRate, double startTime, int decimation) {
    PyraviewHeader h;
    memset(&h, 0, sizeof(h));
    memcpy(h.magic, "PYRA", 4);
    h.version = 1;
    h.dataType = type;
    h.channelCount = channels;
    h.sampleRate = sampleRate;
    h.nativeRate = nativeRate;
    h.startTime = startTime;
    h.decimationFactor = decimation;
    fwrite(&h, sizeof(h), 1, f);
}

// Utility: Validate header
// Returns 1 if valid (or created), 0 if mismatch, -1 if error
static int pv_validate_or_create(FILE** f_out, const char* filename, int channels, int type, double sampleRate, double nativeRate, double startTime, int decimation, int append) {
    FILE* f = NULL;
    if (append) {
        f = fopen(filename, "r+b"); // Try open existing for read/write
        if (f) {
            PyraviewHeader h;
            if (fread(&h, sizeof(h), 1, f) != 1) {
                fclose(f);
                return -1; // File too short
            }
            if (memcmp(h.magic, "PYRA", 4) != 0) {
                fclose(f);
                return -1; // Not a PYRA file
            }
            // Strict match check
            if (h.channelCount != (uint32_t)channels ||
                h.dataType != (uint32_t)type ||
                h.decimationFactor != (uint32_t)decimation ||
                fabs(h.sampleRate - sampleRate) > 1e-5) {
                fclose(f);
                return 0; // Mismatch
            }
            // Verify startTime is valid (not necessarily matching, just valid double)
            if (isnan(h.startTime) || isinf(h.startTime)) {
                fclose(f);
                return -1; // Invalid start time in existing file
            }

            // Seek to end
            pv_fseek(f, 0, SEEK_END);
            *f_out = f;
            return 1;
        }
        // If append is requested but file doesn't exist, create it (fall through)
    }

    f = fopen(filename, "wb"); // Write new
    if (!f) return -1;
    pv_write_header(f, channels, type, sampleRate, nativeRate, startTime, decimation);
    *f_out = f;
    return 1;
}

// Template macro for typed worker
#define DEFINE_WORKER(T, SUFFIX) \
static int pv_internal_execute_##SUFFIX( \
    const T* data, \
    int64_t R, \
    int64_t C, \
    int layout, \
    const char* prefix, \
    int append, \
    const int* steps, \
    int nLevels, \
    double nativeRate, \
    double startTime, \
    int dataType, \
    int nThreads \
) { \
    /* Open files */ \
    FILE* files[16]; \
    double currentRate = nativeRate; \
    int currentDecimation = 1; \
    int ret = 0; \
    \
    /* Pre-calculate rates and decimations */ \
    double rates[16]; \
    int decimations[16]; \
    T* global_buffers[16]; /* Interleaved buffers */ \
    int64_t global_sizes[16]; \
    \
    /* Allocation Logic (Main Thread) */ \
    int64_t prev_len = R; \
    for (int i = 0; i < nLevels; i++) { \
        currentDecimation *= steps[i]; \
        currentRate /= steps[i]; \
        rates[i] = currentRate; \
        decimations[i] = currentDecimation; \
        \
        char filename[512]; \
        snprintf(filename, sizeof(filename), "%s_L%d.bin", prefix, i+1); \
        int status = pv_validate_or_create(&files[i], filename, (int)C, dataType, rates[i], nativeRate, startTime, decimations[i], append); \
        if (status <= 0) { \
            /* Cleanup */ \
            for (int j = 0; j < i; j++) fclose(files[j]); \
            for (int j = 0; j < i; j++) if(global_buffers[j]) free(global_buffers[j]); \
            return (status == 0) ? -2 : -1; \
        } \
        \
        int64_t out_len = prev_len / steps[i]; \
        global_sizes[i] = out_len; \
        global_buffers[i] = NULL; \
        if (out_len > 0) { \
            global_buffers[i] = (T*)malloc(out_len * C * 2 * sizeof(T)); \
            if (!global_buffers[i]) { \
                /* Cleanup */ \
                for (int j = 0; j <= i; j++) fclose(files[j]); \
                for (int j = 0; j < i; j++) if(global_buffers[j]) free(global_buffers[j]); \
                return -1; \
            } \
        } \
        prev_len = out_len; \
    } \
    \
    /* Stride logic */ \
    int64_t stride_ch = (layout == 1) ? R : 1; \
    /* int64_t stride_sample = (layout == 1) ? 1 : C; Unused */ \
    int64_t input_stride = (layout == 0) ? C : 1; \
    int64_t channel_step = (layout == 0) ? 1 : R; \
    \
    /* Determine effective threads */ \
    int effective_threads = (nThreads > 0) ? nThreads : std::thread::hardware_concurrency(); \
    if (effective_threads < 1) effective_threads = 1; \
    \
    std::atomic<int64_t> next_channel(0); \
    std::atomic<int> error_occurred(0); \
    \
    auto worker = [&]() { \
        while (true) { \
            int64_t ch = next_channel.fetch_add(1); \
            if (ch >= C) break; \
            \
            const T* ch_data = data + (ch * channel_step); \
            T* buffers[16]; \
            /* Each thread computes partial reduction for its channel */ \
            /* And writes directly to the interleaved global buffer */ \
            \
            /* We simulate the buffer pointers to point to local data? No, we write to global */ \
            /* But we need temporary buffers? No. */ \
            \
            /* We compute L1 for Channel ch */ \
            if (global_sizes[0] > 0) { \
                int step = steps[0]; \
                T* out_base = global_buffers[0]; \
                int64_t count = global_sizes[0]; \
                for (int64_t i = 0; i < count; i++) { \
                    T min_val = ch_data[i * step * input_stride]; \
                    T max_val = min_val; \
                    for (int j = 1; j < step; j++) { \
                        T val = ch_data[(i * step + j) * input_stride]; \
                        if (val < min_val) min_val = val; \
                        if (val > max_val) max_val = val; \
                    } \
                    /* Interleaved Output Index: Sample i, Channel ch */ \
                    /* Index = i * C + ch */ \
                    /* Pairs = 2 * Index */ \
                    out_base[2 * (i * C + ch)] = min_val; \
                    out_base[2 * (i * C + ch) + 1] = max_val; \
                } \
            } \
            /* Compute L2..Ln */ \
            for (int lvl = 1; lvl < nLevels; lvl++) { \
                if (global_sizes[lvl] > 0) { \
                    int step = steps[lvl]; \
                    T* prev_buf = global_buffers[lvl-1]; \
                    T* out_base = global_buffers[lvl]; \
                    int64_t count = global_sizes[lvl]; \
                    for (int64_t i = 0; i < count; i++) { \
                        /* Input is Interleaved from Previous Level */ \
                        /* Sample i at Prev Level corresponds to step*i .. step*i + step - 1 */ \
                        /* We need to read Channel ch for those samples */ \
                        \
                        /* First sample index in prev level: i * step */ \
                        /* Interleaved index: (i * step) * C + ch */ \
                        \
                        int64_t start_idx = (i * step) * C + ch; \
                        T min_val = prev_buf[2 * start_idx]; \
                        T max_val = prev_buf[2 * start_idx + 1]; \
                        \
                        for (int j = 1; j < step; j++) { \
                            int64_t idx = ((i * step) + j) * C + ch; \
                            T p_min = prev_buf[2 * idx]; \
                            T p_max = prev_buf[2 * idx + 1]; \
                            if (p_min < min_val) min_val = p_min; \
                            if (p_max > max_val) max_val = p_max; \
                        } \
                        out_base[2 * (i * C + ch)] = min_val; \
                        out_base[2 * (i * C + ch) + 1] = max_val; \
                    } \
                } \
            } \
        } \
    }; \
    \
    std::vector<std::thread> threads; \
    for (int i = 0; i < effective_threads; ++i) { \
        threads.emplace_back(worker); \
    } \
    for (auto& t : threads) { t.join(); } \
    \
    /* Write to files sequentially */ \
    for (int i = 0; i < nLevels; i++) { \
        if (global_sizes[i] > 0 && global_buffers[i]) { \
            if (fwrite(global_buffers[i], sizeof(T), global_sizes[i] * C * 2, files[i]) != (size_t)(global_sizes[i] * C * 2)) { \
                ret = -1; \
            } \
        } \
        if (global_buffers[i]) free(global_buffers[i]); \
        fclose(files[i]); \
    } \
    \
    return ret; \
}

// Instantiate workers
DEFINE_WORKER(int8_t, i8)
DEFINE_WORKER(uint8_t, u8)
DEFINE_WORKER(int16_t, i16)
DEFINE_WORKER(uint16_t, u16)
DEFINE_WORKER(int32_t, i32)
DEFINE_WORKER(uint32_t, u32)
DEFINE_WORKER(int64_t, i64)
DEFINE_WORKER(uint64_t, u64)
DEFINE_WORKER(float, f32)
DEFINE_WORKER(double, f64)

extern "C" {
int pyraview_process_chunk(
    const void* dataArray,
    int64_t numRows,
    int64_t numCols,
    int dataType,
    int layout,
    const char* filePrefix,
    int append,
    const int* levelSteps,
    int numLevels,
    double nativeRate,
    double startTime,
    int numThreads
) {
    if (!dataArray || !filePrefix || !levelSteps || numLevels <= 0 || numLevels > 16) return -1;
    for (int i=0; i<numLevels; i++) { if (levelSteps[i] <= 0) return -1; }

    switch (dataType) {
        case PV_INT8: return pv_internal_execute_i8((const int8_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_UINT8: return pv_internal_execute_u8((const uint8_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_INT16: return pv_internal_execute_i16((const int16_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_UINT16: return pv_internal_execute_u16((const uint16_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_INT32: return pv_internal_execute_i32((const int32_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_UINT32: return pv_internal_execute_u32((const uint32_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_INT64: return pv_internal_execute_i64((const int64_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_UINT64: return pv_internal_execute_u64((const uint64_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_FLOAT32: return pv_internal_execute_f32((const float*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        case PV_FLOAT64: return pv_internal_execute_f64((const double*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, startTime, dataType, numThreads);
        default: return -1;
    }
}

int pyraview_get_header(const char* filename, PyraviewHeader* header) {
    if (!filename || !header) return -1;
    FILE* f = fopen(filename, "rb");
    if (!f) return -1;
    if (fread(header, sizeof(PyraviewHeader), 1, f) != 1) {
        fclose(f);
        return -1;
    }
    fclose(f);
    if (memcmp(header->magic, "PYRA", 4) != 0) return -1;
    return 0;
}
}
