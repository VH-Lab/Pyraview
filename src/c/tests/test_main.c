#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pyraview_header.h>

// Macros for testing
#define ASSERT(cond, msg) if(!(cond)) { printf("FAIL: %s\n", msg); return 1; }

// Test function
int run_test(int type, int layout, int channels, int threads) {
    printf("Testing Type=%d, Layout=%d, Channels=%d, Threads=%d...", type, layout, channels, threads);

    int rows = 1000;
    int cols = channels;
    int data_size = rows * cols * 8; // Max size (double)
    void* data = malloc(data_size);
    memset(data, 0, data_size);

    // Fill with dummy data (linear ramp for verification if needed)
    // For now just check execution success

    char prefix[256];
    sprintf(prefix, "test_c_T%d_L%d_C%d_Th%d", type, layout, channels, threads);

    // Cleanup previous
    char fname[512];
    sprintf(fname, "%s_L1.bin", prefix);
    remove(fname);

    int steps[] = {10};
    int ret = pyraview_process_chunk(
        data, rows, cols, type, layout,
        prefix, 0, steps, 1, 100.0, threads
    );

    free(data);

    if (ret != 0) {
        printf("FAILED (ret=%d)\n", ret);
        return 1;
    }

    FILE* f = fopen(fname, "rb");
    if (!f) {
        printf("FAILED (no file)\n");
        return 1;
    }

    // Check header
    PyraviewHeader h;
    fread(&h, sizeof(h), 1, f);
    fclose(f);

    if (h.dataType != (uint32_t)type) {
        printf("FAILED (type mismatch)\n");
        return 1;
    }
    if (h.channelCount != (uint32_t)channels) {
        printf("FAILED (channel count mismatch)\n");
        return 1;
    }

    printf("OK\n");
    return 0;
}

int main() {
    printf("Running Comprehensive C Tests...\n");

    int failures = 0;

    // Types: 0..9
    for (int t = 0; t <= 9; t++) {
        // Layouts: 0 (SxC), 1 (CxS)
        for (int l = 0; l <= 1; l++) {
            // Channels: 1, 10
            int channels[] = {1, 10};
            for (int c_idx = 0; c_idx < 2; c_idx++) {
                int c = channels[c_idx];
                // Threads: 0 (Auto), 2
                int threads[] = {0, 2};
                for (int th_idx = 0; th_idx < 2; th_idx++) {
                    int th = threads[th_idx];
                    if (run_test(t, l, c, th) != 0) failures++;
                }
            }
        }
    }

    if (failures > 0) {
        printf("\nTOTAL FAILURES: %d\n", failures);
        return 1;
    }

    printf("\nALL TESTS PASSED\n");
    return 0;
}
