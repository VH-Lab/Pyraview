#define _FILE_OFFSET_BITS 64
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#ifdef _WIN32
  #include <windows.h>
  #define pv_fseek _fseeki64
  #define pv_ftell _ftelli64
#else
  #include <unistd.h>
  #define pv_fseek fseeko
  #define pv_ftell ftello
#endif

#ifdef _OPENMP
#include <omp.h>
#else
#define omp_get_max_threads() 1
#endif

#include <pyraview_header.h>

// Utility: Write header
static void pv_write_header(FILE* f, int channels, int type, double sampleRate, double nativeRate, int decimation) {
    PyraviewHeader h;
    memset(&h, 0, sizeof(h));
    memcpy(h.magic, "PYRA", 4);
    h.version = 1;
    h.dataType = type;
    h.channelCount = channels;
    h.sampleRate = sampleRate;
    h.nativeRate = nativeRate;
    h.decimationFactor = decimation;
    fwrite(&h, sizeof(h), 1, f);
}

// Utility: Validate header
// Returns 1 if valid (or created), 0 if mismatch, -1 if error
static int pv_validate_or_create(FILE** f_out, const char* filename, int channels, int type, double sampleRate, double nativeRate, int decimation, int append) {
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
            // Seek to end
            pv_fseek(f, 0, SEEK_END);
            *f_out = f;
            return 1;
        }
        // If append is requested but file doesn't exist, create it (fall through)
    }

    f = fopen(filename, "wb"); // Write new
    if (!f) return -1;
    pv_write_header(f, channels, type, sampleRate, nativeRate, decimation);
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
    for (int i = 0; i < nLevels; i++) { \
        currentDecimation *= steps[i]; \
        currentRate /= steps[i]; \
        rates[i] = currentRate; \
        decimations[i] = currentDecimation; \
        \
        char filename[512]; \
        snprintf(filename, sizeof(filename), "%s_L%d.bin", prefix, i+1); \
        int status = pv_validate_or_create(&files[i], filename, (int)C, dataType, rates[i], nativeRate, decimations[i], append); \
        if (status <= 0) { \
            /* Cleanup previous opens */ \
            for (int j = 0; j < i; j++) fclose(files[j]); \
            return (status == 0) ? -2 : -1; \
        } \
    } \
    \
    /* Stride logic */ \
    int64_t stride_ch = (layout == 1) ? R : 1; /* Distance between samples of same channel */ \
    int64_t stride_sample = (layout == 1) ? 1 : C; /* Distance between channels at same sample */ \
    \
    int64_t input_stride = (layout == 0) ? C : 1; \
    int64_t channel_step = (layout == 0) ? 1 : R; \
    \
    /* Determine max threads */ \
    int max_threads = (nThreads > 0) ? nThreads : omp_get_max_threads(); \
    \
    /* Parallel Loop */ \
    _Pragma("omp parallel for ordered num_threads(max_threads)") \
    for (int64_t ch = 0; ch < C; ch++) { \
        const T* ch_data = data + (ch * channel_step); \
        \
        /* Allocate buffers for this channel's output */ \
        /* Using malloc for buffers to avoid stack overflow */ \
        T* buffers[16]; \
        for(int i=0; i<16; i++) buffers[i] = NULL; \
        int64_t sizes[16]; \
        int64_t prev_len = R; \
        int alloc_failed = 0; \
        \
        for (int i = 0; i < nLevels; i++) { \
            int64_t out_len = prev_len / steps[i]; \
            /* We output Min/Max pairs, so 2 * out_len */ \
            sizes[i] = out_len; \
            if (out_len > 0) { \
                buffers[i] = (T*)malloc(out_len * 2 * sizeof(T)); \
                if (!buffers[i]) { alloc_failed = 1; break; } \
            } \
            prev_len = out_len; \
        } \
        \
        if (!alloc_failed) { \
            /* Compute L1 from Raw */ \
            if (sizes[0] > 0) { \
                int step = steps[0]; \
                T* out = buffers[0]; \
                int64_t count = sizes[0]; \
                for (int64_t i = 0; i < count; i++) { \
                    T min_val = ch_data[i * step * input_stride]; \
                    T max_val = min_val; \
                    for (int j = 1; j < step; j++) { \
                        T val = ch_data[(i * step + j) * input_stride]; \
                        if (val < min_val) min_val = val; \
                        if (val > max_val) max_val = val; \
                    } \
                    out[2*i] = min_val; \
                    out[2*i+1] = max_val; \
                } \
            } \
            \
            /* Compute L2..Ln from previous level */ \
            for (int lvl = 1; lvl < nLevels; lvl++) { \
                if (sizes[lvl] > 0) { \
                    int step = steps[lvl]; \
                    T* prev_buf = buffers[lvl-1]; \
                    T* out = buffers[lvl]; \
                    int64_t count = sizes[lvl]; \
                    for (int64_t i = 0; i < count; i++) { \
                        T min_val = prev_buf[i * step * 2]; \
                        T max_val = prev_buf[i * step * 2 + 1]; \
                        for (int j = 1; j < step; j++) { \
                            T p_min = prev_buf[(i * step + j) * 2]; \
                            T p_max = prev_buf[(i * step + j) * 2 + 1]; \
                            if (p_min < min_val) min_val = p_min; \
                            if (p_max > max_val) max_val = p_max; \
                        } \
                        out[2*i] = min_val; \
                        out[2*i+1] = max_val; \
                    } \
                } \
            } \
            \
            /* Write to files sequentially */ \
            _Pragma("omp ordered") \
            { \
                for (int i = 0; i < nLevels; i++) { \
                    if (sizes[i] > 0 && buffers[i]) { \
                        fwrite(buffers[i], sizeof(T), sizes[i] * 2, files[i]); \
                    } \
                } \
            } \
        } \
        \
        /* Cleanup buffers */ \
        for (int i = 0; i < nLevels; i++) { \
            if(buffers[i]) free(buffers[i]); \
        } \
    } \
    \
    /* Close files */ \
    for (int i = 0; i < nLevels; i++) fclose(files[i]); \
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

// Master Dispatcher
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
    int numThreads
) {
    // 1. Validate inputs (basic)
    if (!dataArray || !filePrefix || !levelSteps || numLevels <= 0 || numLevels > 16) return -1;

    // Validate levelSteps
    for (int i=0; i<numLevels; i++) {
        if (levelSteps[i] <= 0) return -1;
    }

    // Dispatch to typed worker
    switch (dataType) {
        case PV_INT8: // 0
            return pv_internal_execute_i8((const int8_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_UINT8: // 1
            return pv_internal_execute_u8((const uint8_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_INT16: // 2
            return pv_internal_execute_i16((const int16_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_UINT16: // 3
            return pv_internal_execute_u16((const uint16_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_INT32: // 4
            return pv_internal_execute_i32((const int32_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_UINT32: // 5
            return pv_internal_execute_u32((const uint32_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_INT64: // 6
            return pv_internal_execute_i64((const int64_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_UINT64: // 7
            return pv_internal_execute_u64((const uint64_t*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_FLOAT32: // 8
            return pv_internal_execute_f32((const float*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        case PV_FLOAT64: // 9
            return pv_internal_execute_f64((const double*)dataArray, numRows, numCols, layout, filePrefix, append, levelSteps, numLevels, nativeRate, dataType, numThreads);
        default:
            return -1; // Unknown data type
    }
}
