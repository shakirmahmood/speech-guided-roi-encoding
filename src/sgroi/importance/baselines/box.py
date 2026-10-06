"""Dummy rectangular ROI, for testing the encoding setup."""

import numpy as np

from ...maps.conversion import block_average_frame
from .. import register


def parse_box(box, width, height):
    """box: [x, y, w, h] or "x,y,w,h", in pixels, or fractions of the frame if all <= 1."""
    if isinstance(box, str):
        box = [float(v) for v in box.split(",")]
    vals = [float(v) for v in box]
    if len(vals) != 4:
        raise ValueError("box must be x,y,w,h")
    if all(v <= 1.0 for v in vals):
        vals = [vals[0] * width, vals[1] * height, vals[2] * width, vals[3] * height]
    return tuple(int(round(v)) for v in vals)


@register("box")
def box(clip, box=(0.375, 0.375, 0.25, 0.25), start=0, end=None):
    """Importance 1 inside the box for frames [start, end), 0 elsewhere.
    Default: centred, a quarter of the width and height (1/16 of the frame)."""
    x, y, bw, bh = parse_box(box, clip.width, clip.height)
    mask = np.zeros((clip.height, clip.width), np.float32)
    mask[max(y, 0):y + bh, max(x, 0):x + bw] = 1.0
    one = block_average_frame(mask)
    b = np.zeros((clip.frames,) + one.shape, np.float32)
    b[start:clip.frames if end is None else min(end, clip.frames)] = one
    return b
