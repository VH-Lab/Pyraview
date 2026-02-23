#include "mex.h"
#include "../../include/pyraview_header.h"
#include <string.h>

/*
 * pyraview_mex.c
 * Gateway for Pyraview C Engine
 *
 * Usage:
 *   status = pyraview_mex(data, prefix, steps, nativeRate, startTime, [append], [numThreads])
 *
 * Inputs:
 *   data: (Samples x Channels) matrix. uint8, int16, single, or double.
 *   prefix: char array (string).
 *   steps: double array of decimation factors (e.g. [100, 10]).
 *   nativeRate: double scalar.
 *   startTime: double scalar.
 *   append: (optional) logical/scalar. Default false.
 *   numThreads: (optional) scalar. Default 0 (auto).
 *
 * Outputs:
 *   status: 0 on success.
 */

void mexFunction(int nlhs, mxArray *plhs[], int nrhs, const mxArray *prhs[]) {
    // Check inputs
    if (nrhs < 5) {
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "Usage: pyraview_mex(data, prefix, steps, nativeRate, startTime, [append], [numThreads])");
    }

    // 1. Data
    const mxArray *mxData = prhs[0];
    void *dataPtr = mxGetData(mxData);
    mwSize numRows = mxGetM(mxData);
    mwSize numCols = mxGetN(mxData);

    // Determine type
    mxClassID classID = mxGetClassID(mxData);
    int dataType = -1;
    switch (classID) {
        case mxINT8_CLASS:   dataType = PV_INT8; break;   // 0
        case mxUINT8_CLASS:  dataType = PV_UINT8; break;  // 1
        case mxINT16_CLASS:  dataType = PV_INT16; break;  // 2
        case mxUINT16_CLASS: dataType = PV_UINT16; break; // 3
        case mxINT32_CLASS:  dataType = PV_INT32; break;  // 4
        case mxUINT32_CLASS: dataType = PV_UINT32; break; // 5
        case mxINT64_CLASS:  dataType = PV_INT64; break;  // 6
        case mxUINT64_CLASS: dataType = PV_UINT64; break; // 7
        case mxSINGLE_CLASS: dataType = PV_FLOAT32; break;// 8
        case mxDOUBLE_CLASS: dataType = PV_FLOAT64; break;// 9
        default:
            mexErrMsgIdAndTxt("Pyraview:InvalidType", "Data type must be int8, uint8, int16, uint16, int32, uint32, int64, uint64, single, or double.");
    }

    // Layout: Matlab is Column-Major. If input is Samples x Channels, then it is CxS.
    // Layout code for CxS is 1.
    int layout = 1;

    // 2. Prefix
    if (!mxIsChar(prhs[1])) {
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "Prefix must be a string.");
    }
    char *prefix = mxArrayToString(prhs[1]);

    // 3. Steps
    if (!mxIsNumeric(prhs[2])) {
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "Steps must be numeric.");
    }
    mwSize numSteps = mxGetNumberOfElements(prhs[2]);
    int *levelSteps = (int*)mxMalloc(numSteps * sizeof(int));

    if (mxGetClassID(prhs[2]) == mxDOUBLE_CLASS) {
         double *dPtr = mxGetPr(prhs[2]);
         for (size_t i = 0; i < numSteps; i++) levelSteps[i] = (int)dPtr[i];
    } else if (mxGetClassID(prhs[2]) == mxINT32_CLASS) {
         int *iPtr = (int*)mxGetData(prhs[2]);
         for (size_t i = 0; i < numSteps; i++) levelSteps[i] = iPtr[i];
    } else {
        mxFree(levelSteps);
        mxFree(prefix);
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "Steps must be double or int32 array.");
    }

    // 4. Native Rate
    if (!mxIsDouble(prhs[3]) || mxGetNumberOfElements(prhs[3]) != 1) {
        mxFree(levelSteps);
        mxFree(prefix);
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "NativeRate must be scalar double.");
    }
    double nativeRate = mxGetScalar(prhs[3]);

    // 5. Start Time
    if (!mxIsDouble(prhs[4]) || mxGetNumberOfElements(prhs[4]) != 1) {
        mxFree(levelSteps);
        mxFree(prefix);
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "StartTime must be scalar double.");
    }
    double startTime = mxGetScalar(prhs[4]);

    // 6. Append (optional)
    int append = 0;
    if (nrhs >= 6) {
        if (mxIsLogical(prhs[5]) || mxIsNumeric(prhs[5])) {
            append = (int)mxGetScalar(prhs[5]);
        }
    }

    // 7. NumThreads (optional)
    int numThreads = 0;
    if (nrhs >= 7) {
        numThreads = (int)mxGetScalar(prhs[6]);
    }

    // Call Engine
    // Note: We need to link against the engine.
    int ret = pyraview_process_chunk(
        dataPtr,
        (int64_t)numRows,
        (int64_t)numCols,
        dataType,
        layout,
        prefix,
        append,
        levelSteps,
        (int)numSteps,
        nativeRate,
        startTime,
        numThreads
    );

    // Cleanup
    mxFree(prefix);
    mxFree(levelSteps);

    // Return status
    if (nlhs > 0) {
        plhs[0] = mxCreateDoubleScalar((double)ret);
    }

    if (ret < 0) {
        // We might want to warn or error?
        // The prompt says "return a specific error code".
        // But throwing an error in MEX stops execution.
        // It's better to return the code if the user wants to handle it,
        // OR throw error.
        // I'll throw error for now as it's safer.
        mexErrMsgIdAndTxt("Pyraview:ExecutionError", "Engine returned error code %d", ret);
    }
}
