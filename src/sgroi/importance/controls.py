"""Sanity-check importance sources."""

import numpy as np

from ..io.qpm import grid_shape
from . import register


@register("zeros")
def zeros(clip):
    """No importance anywhere: the QP map is all zeros, so the encode must be
    bit-identical to the baseline. Checks that the map path changes nothing."""
    rows, cols = grid_shape(clip.width, clip.height)
    return np.zeros((clip.frames, rows, cols), np.float32)
