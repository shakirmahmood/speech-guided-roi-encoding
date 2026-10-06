"""sgroi-qpmap: make or inspect .qpm QP-offset maps outside an experiment.

  sgroi-qpmap box --y4m clip.y4m -o box.qpm [--box x,y,w,h] [--start N --end M]
  sgroi-qpmap zeros --y4m clip.y4m -o zeros.qpm
  sgroi-qpmap from-importance imp.npy --y4m clip.y4m -o roi.qpm   (.npy [T,H,W] or folder of PNGs)
  sgroi-qpmap info roi.qpm
"""

import argparse
import glob
import os
import sys

import numpy as np

from ..importance import ClipInfo, get_source
from ..io.qpm import describe, grid_shape, read_qpm, write_qpm
from ..io.y4m import Y4M
from ..maps.conversion import DEFAULTS, block_average_frame, blocks_to_qp


def iter_importance(path, width, height):
    """[H, W] frames in 0-1 from a .npy [T,H,W] (float 0-1 or uint8, memory-mapped)
    or a folder of greyscale PNGs sorted by name."""
    if os.path.isdir(path):
        from PIL import Image
        files = sorted(glob.glob(os.path.join(path, "*.png")))
        if not files:
            raise ValueError(f"no PNG files in {path}")
        frames = (np.asarray(Image.open(f).convert("L"), dtype=np.float32) / 255.0 for f in files)
    else:
        arr = np.load(path, mmap_mode="r")
        if arr.ndim != 3:
            raise ValueError("importance must be [frames, height, width]")
        scale = 255.0 if arr.dtype == np.uint8 else 1.0
        frames = (np.asarray(f, dtype=np.float32) / scale for f in arr)
    for f in frames:
        if f.shape != (height, width):
            raise ValueError(f"importance frame is {f.shape[1]}x{f.shape[0]}, video is {width}x{height}")
        yield f


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sgroi-qpmap", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--y4m", required=True, help="the clip the map is for")
        p.add_argument("-o", "--output", required=True)

    def conversion(p):
        p.add_argument("--k", type=float, default=DEFAULTS["k"])
        p.add_argument("--qp-min", type=float, default=DEFAULTS["qp_min"])
        p.add_argument("--qp-max", type=float, default=DEFAULTS["qp_max"])
        p.add_argument("--dilate", type=int, default=DEFAULTS["dilate_blocks"])
        p.add_argument("--blur", type=float, default=DEFAULTS["blur_sigma_blocks"])
        p.add_argument("--ramp", type=int, default=DEFAULTS["ramp_frames"])

    p = sub.add_parser("box")
    common(p)
    conversion(p)
    p.add_argument("--box", default="0.375,0.375,0.25,0.25")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int)
    p = sub.add_parser("zeros")
    common(p)
    p = sub.add_parser("from-importance")
    common(p)
    conversion(p)
    p.add_argument("importance")
    p = sub.add_parser("info")
    p.add_argument("qpm")
    a = ap.parse_args(argv)

    if a.cmd == "info":
        offsets, block = read_qpm(a.qpm)
        print(f"block {block}; {describe(offsets)}")
        return 0

    y = Y4M(a.y4m)
    clip = ClipInfo(id="clip", path=a.y4m, width=y.width, height=y.height, frames=y.frames, fps=y.fps)
    kw = {}
    if a.cmd != "zeros":
        kw = dict(k=a.k, qp_min=a.qp_min, qp_max=a.qp_max, dilate_blocks=a.dilate,
                  blur_sigma_blocks=a.blur, ramp_frames=a.ramp)
    if a.cmd == "zeros":
        rows, cols = grid_shape(y.width, y.height)
        offsets = np.zeros((y.frames, rows, cols), np.float32)
    elif a.cmd == "box":
        offsets = blocks_to_qp(get_source("box")(clip, box=a.box, start=a.start, end=a.end), **kw)
    else:
        frames = []
        for f in iter_importance(a.importance, y.width, y.height):
            if len(frames) == y.frames:
                break
            frames.append(block_average_frame(f))
        if len(frames) < y.frames:
            sys.exit(f"importance has {len(frames)} frames, video has {y.frames}")
        offsets = blocks_to_qp(np.stack(frames), **kw)
    write_qpm(a.output, offsets)
    print(f"wrote {a.output}: {describe(offsets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
