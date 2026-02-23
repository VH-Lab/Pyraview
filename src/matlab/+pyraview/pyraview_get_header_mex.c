#include "mex.h"
#include "../../include/pyraview_header.h"
#include <string.h>

/*
 * pyraview_get_header_mex.c
 * MEX wrapper for pyraview_get_header
 *
 * Usage:
 *   header = pyraview_get_header_mex(filename)
 *
 * Inputs:
 *   filename: char array (string).
 *
 * Outputs:
 *   header: struct with fields:
 *     version, dataType, channelCount, sampleRate, nativeRate, startTime, decimationFactor
 */

void mexFunction(int nlhs, mxArray *plhs[], int nrhs, const mxArray *prhs[]) {
    if (nrhs != 1) {
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "Usage: pyraview_get_header_mex(filename)");
    }

    if (!mxIsChar(prhs[0])) {
        mexErrMsgIdAndTxt("Pyraview:InvalidInput", "Filename must be a string.");
    }
    char *filename = mxArrayToString(prhs[0]);

    PyraviewHeader h;
    if (pyraview_get_header(filename, &h) != 0) {
        mxFree(filename);
        mexErrMsgIdAndTxt("Pyraview:ReadError", "Failed to read Pyraview header from %s", filename);
    }
    mxFree(filename);

    const char *field_names[] = {
        "version",
        "dataType",
        "channelCount",
        "sampleRate",
        "nativeRate",
        "startTime",
        "decimationFactor"
    };
    int n_fields = 7;

    plhs[0] = mxCreateStructMatrix(1, 1, n_fields, field_names);

    mxSetField(plhs[0], 0, "version", mxCreateDoubleScalar((double)h.version));
    mxSetField(plhs[0], 0, "dataType", mxCreateDoubleScalar((double)h.dataType));
    mxSetField(plhs[0], 0, "channelCount", mxCreateDoubleScalar((double)h.channelCount));
    mxSetField(plhs[0], 0, "sampleRate", mxCreateDoubleScalar(h.sampleRate));
    mxSetField(plhs[0], 0, "nativeRate", mxCreateDoubleScalar(h.nativeRate));
    mxSetField(plhs[0], 0, "startTime", mxCreateDoubleScalar(h.startTime));
    mxSetField(plhs[0], 0, "decimationFactor", mxCreateDoubleScalar((double)h.decimationFactor));
}
