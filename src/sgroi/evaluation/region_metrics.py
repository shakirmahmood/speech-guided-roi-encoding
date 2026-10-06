"""Region-aware quality metrics: PSNR-Y and SSIM-Y inside an ROI, in the
background, and over the full frame.

An ROI is a block mask [frames, rows, cols] (normally the blocks a QP map
favours). One decode of an encode can be measured against several ROIs at
once, so the baseline is decoded only once however many conditions there are.
"""

import subprocess

import numpy as np
from scipy import ndimage

from ..io.y4m import Y4M
from ..utils import proc


def decoded_luma(path, width, height):
    """Decode a bitstream with ffmpeg, yield luma planes."""
    cw, ch = (width + 1) // 2, (height + 1) // 2
    frame_bytes = width * height + 2 * cw * ch
    p = proc.popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                   stdout=subprocess.PIPE)
    try:
        while True:
            data = p.stdout.read(frame_bytes)
            if len(data) < frame_bytes:
                break
            yield np.frombuffer(data, np.uint8, width * height).reshape(height, width)
    finally:
        p.stdout.close()
        p.wait()


def psnr(mse):
    return float("inf") if mse <= 0 else 10 * np.log10(255.0 ** 2 / mse)


def ssim_map(a, b):
    """Gaussian-window SSIM map on luma (Wang et al. 2004, sigma 1.5)."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2

    def blur(x):
        return ndimage.gaussian_filter(x, 1.5, truncate=3.5)

    mu_a, mu_b = blur(a), blur(b)
    s_aa = blur(a * a) - mu_a ** 2
    s_bb = blur(b * b) - mu_b ** 2
    s_ab = blur(a * b) - mu_a * mu_b
    return ((2 * mu_a * mu_b + c1) * (2 * s_ab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (s_aa + s_bb + c2))


def pixel_mask(block_mask, width, height, block=16):
    return np.kron(block_mask, np.ones((block, block), bool))[:height, :width]


PSNR_CAP = 100.0      # per-frame PSNR of an object box that is pixel-identical


def evaluate(ref_y4m, encoded, rois=None, ssim=True, objects=None):
    """Compare `encoded` with the reference Y4M.

    rois:    {name: block mask [frames, rows, cols]} (may be empty).
    objects: {name: pixel boxes [frames, 4] = (x0, y0, x1, y1)}: annotated
             objects, measured inside their own box in every frame.
    Returns {"full": {...}, "<name>": {...}, ..., "objects": {...}}. Region
    entries hold roi_psnr / bg_psnr / roi_ssim / bg_ssim, averaged over frames
    where that part is non-empty, plus roi_frames and roi_fraction. Object
    entries hold per-frame arrays "psnr" and "ssim" (NaN where the box is
    empty), so callers can average over any set of frames.
    """
    ref = Y4M(ref_y4m)
    rois = rois or {}
    objects = objects or {}
    obj_acc = {name: {"psnr": [], "ssim": []} for name in objects}
    acc = {"full": {"psnr": [], "ssim": []}}
    for name in rois:
        acc[name] = {"roi_psnr": [], "bg_psnr": [], "roi_ssim": [], "bg_ssim": [], "roi_px": 0, "px": 0}
    n = 0
    for i, (r, d) in enumerate(zip(ref.luma_frames(), decoded_luma(encoded, ref.width, ref.height))):
        err = (r.astype(np.float64) - d.astype(np.float64)) ** 2
        smap = ssim_map(r, d) if ssim else None
        acc["full"]["psnr"].append(psnr(err.mean()))
        if ssim:
            acc["full"]["ssim"].append(smap.mean())
        for name, blocks in rois.items():
            m = pixel_mask(blocks[min(i, len(blocks) - 1)], ref.width, ref.height)
            a = acc[name]
            a["roi_px"] += int(m.sum())
            a["px"] += m.size
            if m.any():
                a["roi_psnr"].append(psnr(err[m].mean()))
                if ssim:
                    a["roi_ssim"].append(smap[m].mean())
            if (~m).any():
                a["bg_psnr"].append(psnr(err[~m].mean()))
                if ssim:
                    a["bg_ssim"].append(smap[~m].mean())
        for name, boxes in objects.items():
            x0, y0, x1, y1 = (int(v) for v in boxes[min(i, len(boxes) - 1)])
            o = obj_acc[name]
            if x1 > x0 and y1 > y0:
                o["psnr"].append(min(PSNR_CAP, psnr(err[y0:y1, x0:x1].mean())))
                o["ssim"].append(float(smap[y0:y1, x0:x1].mean()) if ssim else np.nan)
            else:
                o["psnr"].append(np.nan)
                o["ssim"].append(np.nan)
        n += 1
    if n == 0:
        raise RuntimeError(f"no frames decoded from {encoded}")

    def mean(v):
        return float(np.mean(v)) if v else float("nan")

    out = {"full": {"frames": n, "psnr": mean(acc["full"]["psnr"]), "ssim": mean(acc["full"]["ssim"])}}
    for name in rois:
        a = acc[name]
        out[name] = {k: mean(a[k]) for k in ("roi_psnr", "bg_psnr", "roi_ssim", "bg_ssim")}
        out[name]["roi_frames"] = len(a["roi_psnr"])
        out[name]["roi_fraction"] = a["roi_px"] / a["px"] if a["px"] else 0.0
    out["objects"] = {name: {k: np.asarray(v, np.float64) for k, v in o.items()} for name, o in obj_acc.items()}
    return out
