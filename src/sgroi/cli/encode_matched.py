"""sgroi-encode-matched: encode with a QP map, matching another encode's bitrate.

  sgroi-encode-matched -i clip.y4m -o roi.hevc --qpmap roi.qpm --match-summary base.json
"""

import argparse
import json
import sys

from ..encode import encode_matched


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sgroi-encode-matched", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--qpmap")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--match-kbps", type=float)
    g.add_argument("--match-summary", help="summary JSON of the encode to match")
    ap.add_argument("--summary", required=True, help="write the final summary JSON here")
    ap.add_argument("--tolerance", type=float, default=0.5, help="percent (default 0.5)")
    ap.add_argument("--max-iter", type=int, default=4)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--x265-params", default="log-level=warning")
    a = ap.parse_args(argv)

    match = a.match_kbps
    if a.match_summary:
        with open(a.match_summary, encoding="utf-8") as f:
            match = json.load(f)["kbps"]
    s = encode_matched(a.input, a.output, match, a.summary, qpmap=a.qpmap, tolerance=a.tolerance,
                       max_iter=a.max_iter, preset=a.preset, passes=a.passes, x265_params=a.x265_params)
    print(f"matched: {s['kbps']:.2f} kbps ({s['match_error_percent']:+.2f}%) "
          f"{'OK' if s['match_ok'] else 'outside tolerance'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
