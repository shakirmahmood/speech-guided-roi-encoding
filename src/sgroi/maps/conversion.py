"""Importance maps -> per-block QP offsets (design doc §5.6).

Per frame:
  1. block-average importance onto the 16x16 grid
  2. spatial softening: dilate by N blocks, then Gaussian blur
  3. temporal smoothing: centred moving average over R frames, so quality
     ramps in slightly before an important region appears and fades after
  4. importance -> dQP, budget-neutral per frame, clamped to [qp_min, qp_max].
     Two rules (`budget`):
       relative         dQP = -k * (S_b - mean_frame(S_b))
                        Everything is relative to the frame's average importance:
                        in a busy frame, weakly important blocks fall below the
                        average and get a positive offset (fewer bits).
       background_pays  dQP = -k * S_b for every block; blocks with importance
                        below `background_threshold` (the background) also get
                        one uniform positive offset that makes the frame's mean 0.
                        Important blocks never get fewer bits than neutral; only
                        the background pays. A frame with no background left
                        falls back to `relative`.
Steps 2-3 run before step 4, so every frame stays budget-neutral (up to the
clamp) and a frame with no importance gets all zeros, under either rule.
"""

import logging

import numpy as np
from scipy import ndimage

from ..io.qpm import BLOCK, grid_shape

DEFAULTS = dict(k=6.0, qp_min=-8.0, qp_max=6.0, dilate_blocks=1, blur_sigma_blocks=0.75, ramp_frames=8,
                budget="relative", background_threshold=0.05)
BUDGETS = ("relative", "background_pays")

log = logging.getLogger("sgroi.run")


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


def _background_pays(b, k, threshold):
    """dQP for the background_pays rule (see module docstring); b: [T, rows, cols]."""
    dqp = -k * b
    bg = b < threshold
    n_bg = bg.sum(axis=(1, 2))
    total = b.sum(axis=(1, 2), dtype=np.float64)
    pay = np.where(n_bg > 0, k * total / np.maximum(n_bg, 1), 0.0).astype(np.float32)
    dqp = dqp + bg * pay[:, None, None]
    no_bg = (n_bg == 0) & (total > 0)
    if no_bg.any():
        log.warning(f"  qpmap: background_pays: {int(no_bg.sum())} frame(s) have no background "
                    f"(importance < {threshold} everywhere); used the relative rule for them")
        dqp[no_bg] = -k * (b[no_bg] - b[no_bg].mean(axis=(1, 2), keepdims=True))
    return dqp


def blocks_to_qp(b, k=6.0, qp_min=-8.0, qp_max=6.0,
                 dilate_blocks=1, blur_sigma_blocks=0.75, ramp_frames=8,
                 budget="relative", background_threshold=0.05):
    """Block-level importance [T, rows, cols] in 0-1 -> dQP [T, rows, cols] (steps 2-4).
    k: strength; a small region at importance 1 gets roughly -k.
    budget: "relative" or "background_pays" (see module docstring)."""
    if budget not in BUDGETS:
        raise ValueError(f"budget must be one of {', '.join(BUDGETS)} (got {budget!r})")
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
    if budget == "relative":
        dqp = -k * (b - b.mean(axis=(1, 2), keepdims=True))
    else:
        dqp = _background_pays(b, k, background_threshold)
    return (np.clip(dqp, qp_min, qp_max) + 0.0).astype(np.float32)   # + 0.0 turns -0.0 into 0.0


def importance_to_qp(frames, block=BLOCK, **kwargs):
    """Pixel-level importance (iterable of [H, W] frames in 0-1) -> dQP."""
    return blocks_to_qp(block_average(frames, block), **kwargs)
