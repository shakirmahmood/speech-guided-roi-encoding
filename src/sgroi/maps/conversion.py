"""Importance maps -> per-block QP offsets (design doc §5.6).

Per frame:
  1. block-average importance onto the 16x16 grid
  2. spatial softening: dilate by N blocks, then Gaussian blur
  3. temporal smoothing: centred moving average over R frames, so quality
     ramps in slightly before an important region appears and fades after
  4. dQP = -k * (S_b - mean_frame(S_b)), clamped to [qp_min, qp_max]
Steps 2-3 run before the zero-mean step, so every frame stays budget-neutral
and a frame with no importance gets all zeros.
"""

import numpy as np
from scipy import ndimage

from ..io.qpm import BLOCK, grid_shape

DEFAULTS = dict(k=6.0, qp_min=-8.0, qp_max=6.0, dilate_blocks=1, blur_sigma_blocks=0.75, ramp_frames=8)


def block_average_frame(frame, block=BLOCK):
    """[H, W] importance in 0-1 -> [rows, cols] block means (edge blocks padded)."""
    frame = np.clip(np.asarray(frame, dtype=np.float32), 0.0, 1.0)
    h, w = frame.shape
    rows, cols = grid_shape(w, h, block)
    padded = np.pad(frame, ((0, rows * block - h), (0, cols * block - w)), mode="edge")
    return padded.reshape(rows, block, cols, block).mean(axis=(1, 3))


def block_average(frames, block=BLOCK):
    """Iterable of [H, W] importance frames -> [T, rows, cols], one frame at a time."""
    return np.stack([block_average_frame(f, block) for f in frames])


def blocks_to_qp(b, k=6.0, qp_min=-8.0, qp_max=6.0,
                 dilate_blocks=1, blur_sigma_blocks=0.75, ramp_frames=8):
    """Block-level importance [T, rows, cols] in 0-1 -> dQP [T, rows, cols] (steps 2-4).
    k: strength; a small region at importance 1 gets roughly -k."""
    b = np.asarray(b, dtype=np.float32)
    if b.ndim != 3:
        raise ValueError("block importance must be [frames, rows, cols]")
    if dilate_blocks > 0:
        size = 2 * int(dilate_blocks) + 1
        b = ndimage.grey_dilation(b, size=(1, size, size))
    if blur_sigma_blocks > 0:
        b = ndimage.gaussian_filter(b, sigma=(0, blur_sigma_blocks, blur_sigma_blocks), mode="nearest")
    if ramp_frames > 1:
        b = ndimage.uniform_filter1d(b, size=int(ramp_frames), axis=0, mode="nearest")
    dqp = -k * (b - b.mean(axis=(1, 2), keepdims=True))
    return (np.clip(dqp, qp_min, qp_max) + 0.0).astype(np.float32)   # + 0.0 turns -0.0 into 0.0


def importance_to_qp(frames, block=BLOCK, **kwargs):
    """Pixel-level importance (iterable of [H, W] frames in 0-1) -> dQP."""
    return blocks_to_qp(block_average(frames, block), **kwargs)
