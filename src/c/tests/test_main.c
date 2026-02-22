#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <pyraview_header.h>

int main() {
    printf("Running Pyraview C Tests...\n");

    // Test 1: Generate L1 for u8
    int rows = 100;
    int cols = 1;
    unsigned char* data = (unsigned char*)malloc(rows * cols);
    for(int i=0; i<rows; i++) data[i] = (unsigned char)i;

    int steps[] = {10};
    int ret = pyraview_process_chunk(
        data, rows, cols, PV_UINT8, 0,
        "test_c", 0, steps, 1, 100.0, 0
    );

    if (ret != 0) {
        printf("FAILED: pyraview_process_chunk returned %d\n", ret);
        return 1;
    }

    // Verify file exists
    FILE* f = fopen("test_c_L1.bin", "rb");
    if (!f) {
        printf("FAILED: Output file not created\n");
        return 1;
    }

    // Verify header
    PyraviewHeader h;
    fread(&h, sizeof(h), 1, f);
    if (h.version != 1 || h.dataType != PV_UINT8) {
        printf("FAILED: Header invalid\n");
        return 1;
    }

    fclose(f);
    free(data);

    printf("SUCCESS\n");
    return 0;
}
