"""Drawing on 8-bit 4:2:0 frames: grid layout, ROI outline or tint, text labels.

Everything works directly on Y/U/V planes, so the decoded encodes are shown
exactly as decoded (no RGB round trip); only the final comparison video is
compressed, at near-lossless quality.
"""

import math

import numpy as np
from scipy import ndimage

BLOCK = 16

# BT.601 limited-range YUV for the outline / tint colour
COLORS_YUV = {
    "red": (81, 90, 240),
    "yellow": (210, 16, 146),
    "green": (145, 54, 34),
    "cyan": (170, 166, 16),
    "magenta": (106, 202, 222),
    "white": (235, 128, 128),
}


def grid_layout(n, width, height, max_width=None):
    """Panels for n videos of width x height: (cols, rows, panel_w, panel_h).
    Up to 3 panels side by side, more in a near-square grid; panels are scaled
    down so the whole grid is at most max_width wide. Panel sizes are even."""
    if n < 1:
        raise ValueError("need at least one panel")
    cols = n if n <= 3 else math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    scale = min(1.0, max_width / (cols * width)) if max_width else 1.0
    pw = max(2, int(width * scale) // 2 * 2)
    ph = max(2, int(height * scale) // 2 * 2)
    return cols, rows, pw, ph


class BlockMapper:
    """Maps block-grid values (one per 16x16 block of the source frame) onto a
    panel of panel_w x panel_h pixels, which may be scaled."""

    def __init__(self, src_w, src_h, panel_w, panel_h, block=BLOCK):
        self.rows_idx = (np.arange(panel_h) * src_h // panel_h) // block
        self.cols_idx = (np.arange(panel_w) * src_w // panel_w) // block

    def __call__(self, blocks):
        return blocks[np.ix_(self.rows_idx, self.cols_idx)]


def outline(mask, thickness=2):
    """The border pixels (inner side) of a boolean mask."""
    if not mask.any():
        return mask
    inner = ndimage.binary_erosion(mask, iterations=thickness, border_value=0)
    return mask & ~inner


def to_chroma(mask):
    """Luma-resolution mask -> 4:2:0 chroma resolution (any of the 2x2 pixels)."""
    h, w = mask.shape
    return mask.reshape(h // 2, 2, w // 2, 2).any(axis=(1, 3))


class RoiPainter:
    """Draws one condition's ROI on a panel, frame by frame.

    offsets:   QP map [frames, rows, cols] (negative = more bits)
    threshold: blocks below it are ROI (same rule as the metrics)
    style:     "outline", "tint" or "none"
    """

    def __init__(self, offsets, src_w, src_h, panel_w, panel_h, threshold=-0.5,
                 style="outline", color="red"):
        if style not in ("outline", "tint", "none"):
            raise ValueError(f"roi_style must be outline, tint or none (got {style!r})")
        if color not in COLORS_YUV:
            raise ValueError(f"roi_color must be one of {', '.join(COLORS_YUV)} (got {color!r})")
        self.offsets = offsets
        self.threshold = threshold
        self.style = style
        self.color = COLORS_YUV[color]
        self.map = BlockMapper(src_w, src_h, panel_w, panel_h)
        self.thickness = max(2, round(panel_h / 360))
        self._cache_key = None
        self._cache = None

    def _frame_masks(self, i):
        blocks = self.offsets[min(i, len(self.offsets) - 1)]
        key = blocks.tobytes()
        if key != self._cache_key:                      # maps are often static: reuse
            if self.style == "outline":
                edge = outline(self.map(blocks < self.threshold), self.thickness)
                self._cache = (edge, to_chroma(edge))
            else:
                px = self.map(blocks)
                alpha = np.clip(-px / 8.0, 0.0, 1.0) * 0.5
                alpha[px >= self.threshold] = 0.0
                self._cache = (alpha, alpha[::2, ::2])
            self._cache_key = key
        return self._cache

    def paint(self, y, u, v, i):
        if self.style == "none":
            return
        cy, cu, cv = self.color
        a, ac = self._frame_masks(i)
        if self.style == "outline":
            y[a], u[ac], v[ac] = cy, cu, cv
        else:
            if not a.any():
                return
            y[:] = (y * (1 - a) + cy * a).round().astype(np.uint8)
            u[:] = (u * (1 - ac) + cu * ac).round().astype(np.uint8)
            v[:] = (v * (1 - ac) + cv * ac).round().astype(np.uint8)


def _font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)        # Pillow >= 10.1: scalable
    except TypeError:
        return ImageFont.load_default()                 # older Pillow: small bitmap font


class Label:
    """White text on a translucent dark box, drawn in the panel's top-left corner."""

    def __init__(self, text, panel_w, panel_h):
        from PIL import Image, ImageDraw
        size = max(12, round(panel_h / 24))
        font = _font(size)
        x0, y0, x1, y1 = font.getbbox(text)
        pad = max(4, size // 3)
        w = min(panel_w, (x1 - x0) + 2 * pad) // 2 * 2
        h = min(panel_h, (y1 - y0) + 2 * pad) // 2 * 2
        img = Image.new("L", (w, h), 0)
        ImageDraw.Draw(img).text((pad - x0, pad - y0), text, fill=255, font=font)
        self.text = np.asarray(img, np.float32) / 255.0
        self.margin = max(2, size // 3) // 2 * 2
        self.h, self.w = h, w

    def paint(self, y, u, v, at=None):
        """Draw at the top-left corner, or with its top-left at `at` = (x, y) pixels."""
        if at is None:
            x0 = y0 = self.margin
        else:
            x0 = max(0, min(int(at[0]), y.shape[1] - 2)) // 2 * 2
            y0 = max(0, min(int(at[1]), y.shape[0] - 2)) // 2 * 2
        h = min(self.h, y.shape[0] - y0) // 2 * 2
        w = min(self.w, y.shape[1] - x0) // 2 * 2
        if h <= 0 or w <= 0:
            return
        t = self.text[:h, :w]
        region = y[y0:y0 + h, x0:x0 + w].astype(np.float32)
        region = region * 0.45 + 16 * 0.55              # darken behind the text
        region = region * (1 - t) + 235 * t
        y[y0:y0 + h, x0:x0 + w] = region.round().astype(np.uint8)
        cx, cy, ch, cw = x0 // 2, y0 // 2, h // 2, w // 2
        for p in (u, v):                                # pull chroma towards grey
            c = p[cy:cy + ch, cx:cx + cw].astype(np.float32)
            p[cy:cy + ch, cx:cx + cw] = (c * 0.45 + 128 * 0.55).round().astype(np.uint8)


def draw_rect(y, u, v, x0, y0, x1, y1, color, thickness=2):
    """Rectangle outline (inner side of the box) in a colour from COLORS_YUV or a (Y, U, V) tuple."""
    cy, cu, cv = COLORS_YUV[color] if isinstance(color, str) else color
    h, w = y.shape
    x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(w, int(x1)), min(h, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    t = max(1, min(int(thickness), (x1 - x0) // 2, (y1 - y0) // 2))
    m = np.zeros((h, w), bool)
    m[y0:y1, x0:x1] = True
    m[y0 + t:y1 - t, x0 + t:x1 - t] = False
    y[m] = cy
    mc = to_chroma(m[:h // 2 * 2, :w // 2 * 2])
    u[:mc.shape[0], :mc.shape[1]][mc] = cu
    v[:mc.shape[0], :mc.shape[1]][mc] = cv
