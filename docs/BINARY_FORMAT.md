# Pyraview Binary Format

Pyraview uses a simple, efficient binary format for storing multi-resolution time-series data. Each level of the pyramid is stored in a separate file (e.g., `data_L1.bin`, `data_L2.bin`).

## File Structure

| Section | Size | Description |
|---|---|---|
| Header | 1024 bytes | Metadata about the file. |
| Data | Variable | Interleaved Min/Max pairs for all channels. |

## Header (1024 bytes)

The header is fixed-size and little-endian.

| Field | Type | Size | Description |
|---|---|---|---|
| `magic` | char[4] | 4 | "PYRA" magic string. |
| `version` | uint32 | 4 | Format version (currently 1). |
| `dataType` | uint32 | 4 | 0=uint8, 1=int16, 2=float32, 3=float64. |
| `channelCount` | uint32 | 4 | Number of channels. |
| `sampleRate` | double | 8 | Sample rate of *this level*. |
| `nativeRate` | double | 8 | Original recording rate. |
| `decimationFactor` | uint32 | 4 | Cumulative decimation factor from raw. |
| `reserved` | uint8 | 988 | Padding (zeros). |

## Data Layout

The data section follows the header immediately (byte 1024).

The layout consists of **Time Chunks**. Each time chunk contains the Min/Max values for all channels for a specific time interval.

Within a chunk, data is organized as:

`[Ch0_MinMax][Ch1_MinMax]...[ChN_MinMax]`

Where `ChX_MinMax` is a sequence of `(Min, Max)` pairs for that channel in that time chunk.

Note: Since files are often appended to, the file consists of a sequence of these chunks. The chunk size depends on the processing block size used during generation.

### Values

Each logical sample in the decimated file consists of TWO values: `Min` and `Max`. They are stored interleaved: `Min, Max, Min, Max...`.

If the file contains `N` logical samples for `C` channels, the total number of values is `N * C * 2`.
