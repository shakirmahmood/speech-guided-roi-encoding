"""sgroi-metrics: quality inside vs outside an ROI for a set of encodes.

  sgroi-metrics --ref clip.y4m --qpmap roi.qpm baseline=base.hevc roi=roi.hevc [--csv out.csv]

The first encode is the reference for the "change" lines. The ROI is the
blocks the map favours (offset < --roi-threshold), the same for every encode.
"""

import argparse
import csv
import os
import sys

from ..evaluation import evaluate
from ..io.qpm import read_qpm, roi_block_mask
from ..io.y4m import Y4M


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sgroi-metrics", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--qpmap", required=True)
    ap.add_argument("--roi-threshold", type=float, default=-0.5)
    ap.add_argument("--no-ssim", action="store_true")
    ap.add_argument("--csv")
    ap.add_argument("encodes", nargs="+", help="label=path.hevc")
    a = ap.parse_args(argv)

    offsets, _ = read_qpm(a.qpmap)
    mask = roi_block_mask(offsets, a.roi_threshold)
    ref = Y4M(a.ref)
    rows = []
    for item in a.encodes:
        label, _, path = item.partition("=")
        if not path:
            label, path = os.path.splitext(os.path.basename(item))[0], item
        m = evaluate(a.ref, path, {"roi": mask}, ssim=not a.no_ssim)
        kbps = os.path.getsize(path) * 8 / (m["full"]["frames"] / ref.fps) / 1000
        rows.append({"label": label, "kbps": kbps, "full_psnr": m["full"]["psnr"],
                     "full_ssim": m["full"]["ssim"], **m["roi"]})

    print(f"{'encode':<12}{'kbps':>9}{'PSNR roi':>10}{'PSNR bg':>9}{'PSNR all':>10}{'SSIM roi':>10}{'SSIM bg':>9}")
    for r in rows:
        print(f"{r['label']:<12}{r['kbps']:>9.1f}{r['roi_psnr']:>10.2f}{r['bg_psnr']:>9.2f}"
              f"{r['full_psnr']:>10.2f}{r['roi_ssim']:>10.4f}{r['bg_ssim']:>9.4f}")
    b = rows[0]
    for r in rows[1:]:
        print(f"{r['label']} vs {b['label']}: bitrate {100 * (r['kbps'] / b['kbps'] - 1):+.2f}%  "
              f"PSNR roi {r['roi_psnr'] - b['roi_psnr']:+.2f} dB  bg {r['bg_psnr'] - b['bg_psnr']:+.2f} dB  "
              f"all {r['full_psnr'] - b['full_psnr']:+.2f} dB")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
