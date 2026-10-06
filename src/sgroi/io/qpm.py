"""The .qpm QP-offset map format shared with the C encoder.

Little-endian: "QPM1", int32 block (16), int32 cols = ceil(W/16),
int32 rows = ceil(H/16), int32 nframes, then float32 offsets
[nframes][rows][cols], row-major. Negative offset = more bits.
"""

import struct

import numpy as np

BLOCK = 16
MAGIC = b"QPM1"


def grid_shape(width, height, block=BLOCK):
    """(rows, cols) of the block grid x265 uses for quantOffsets."""
    return (height + block - 1) // block, (width + block - 1) // block


def write_qpm(path, offsets, block=BLOCK):
    """offsets: float array [frames, rows, cols]."""
    offsets = np.ascontiguousarray(offsets, dtype="<f4")
    if offsets.ndim != 3:
        raise ValueError("offsets must be [frames, rows, cols]")
    if not np.all(np.isfinite(offsets)):
        raise ValueError("offsets contain NaN/inf")
    t, rows, cols = offsets.shape
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<4i", block, cols, rows, t))
        f.write(offsets.tobytes())


def read_qpm(path):
    """Returns (offsets [frames, rows, cols] float32, block)."""
    with open(path, "rb") as f:
        if f.read(4) != MAGIC:
            raise ValueError(f"{path} is not a QPM1 file")
        block, cols, rows, t = struct.unpack("<4i", f.read(16))
        data = np.frombuffer(f.read(), dtype="<f4")
    if data.size != t * rows * cols:
        raise ValueError(f"{path}: expected {t * rows * cols} values, found {data.size}")
    return data.reshape(t, rows, cols).astype(np.float32), block


def roi_block_mask(offsets, threshold=-0.5):
    """Blocks the map favours (offset below threshold): [frames, rows, cols] bool."""
    return offsets < threshold


def describe(offsets):
    """Short text summary of a map."""
    t, rows, cols = offsets.shape
    roi = roi_block_mask(offsets)
    return (f"{t} frames, {cols}x{rows} blocks; offset mean {offsets.mean():+.3f}, "
            f"min {offsets.min():+.2f}, max {offsets.max():+.2f}; "
            f"ROI {100 * roi.mean():.1f}% of blocks, in {int(roi.any(axis=(1, 2)).sum())}/{t} frames")
