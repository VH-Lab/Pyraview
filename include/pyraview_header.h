#ifndef PYRAVIEW_HEADER_H
#define PYRAVIEW_HEADER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Constants
#define PYRA_MAGIC "PYRA"
#define PYRA_HEADER_SIZE 1024

// Enum for Data Types
typedef enum {
    PV_INT8 = 0,
    PV_UINT8 = 1,
    PV_INT16 = 2,
    PV_UINT16 = 3,
    PV_INT32 = 4,
    PV_UINT32 = 5,
    PV_INT64 = 6,
    PV_UINT64 = 7,
    PV_FLOAT32 = 8,
    PV_FLOAT64 = 9
} PvDataType;

// Alignment Macros
#if defined(_MSC_VER)
    #define PV_ALIGN_PREFIX(n) __declspec(align(n))
    #define PV_ALIGN_SUFFIX(n)
#else
    #define PV_ALIGN_PREFIX(n)
    #define PV_ALIGN_SUFFIX(n) __attribute__((aligned(n)))
#endif

// Header Structure (1024-byte fixed, 64-byte aligned)
typedef PV_ALIGN_PREFIX(64) struct {
    char magic[4];              // "PYRA"
    uint32_t version;           // 1
    uint32_t dataType;          // PvDataType
    uint32_t channelCount;      // Number of channels
    double sampleRate;          // Sample rate of this level
    double nativeRate;          // Original recording rate
    uint32_t decimationFactor;  // Cumulative decimation from raw
    uint8_t reserved[988];      // Padding to 1024 bytes
} PV_ALIGN_SUFFIX(64) PyraviewHeader;

// API Function
// Returns 0 on success, negative values for errors
// layout: 0=SxC (Sample-Major), 1=CxS (Channel-Major)
int pyraview_process_chunk(
    const void* dataArray,      // Pointer to raw data
    int64_t numRows,            // Number of samples per channel
    int64_t numCols,            // Number of channels
    int dataType,               // PvDataType
    int layout,                 // 0=SxC, 1=CxS
    const char* filePrefix,     // Base name for output files
    int append,                 // Boolean flag
    const int* levelSteps,      // Array of decimation factors [100, 10, 10]
    int numLevels,              // Size of levelSteps array
    double nativeRate,          // Original recording rate (required for header/validation)
    int numThreads              // 0 for auto
);

#ifdef __cplusplus
}
#endif

#endif // PYRAVIEW_HEADER_H
