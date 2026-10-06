"""Encode so the achieved bitrate matches a reference bitrate (normally the
baseline's achieved bitrate) within a tolerance.

x265's ABR lands within a few percent of the target, and an ROI map shifts
that slightly, which is enough to bias an equal-bitrate comparison. This
re-runs the encode with a corrected target until the result is close enough.
x265 takes whole kbps only, so at low bitrates the reachable values are
coarse; a repeated target means no closer match exists.
"""

import os
import shutil
import tempfile

from .encoder import encode


def encode_matched(input_y4m, output, match_kbps, summary_path, qpmap=None, tolerance=0.5,
                   max_iter=4, log=print, **encode_kwargs):
    """Returns the summary dict of the closest attempt, with extra keys:
    match_kbps, match_error_percent, match_ok, match_attempts."""
    import json

    tmp = tempfile.mkdtemp(prefix="sgroi_match_")
    best, attempts, tried = None, [], set()
    target = match_kbps
    try:
        for it in range(1, max_iter + 1):
            t = int(round(target))
            if t in tried:
                log(f"  target {t} kbps already tried; no closer match reachable")
                break
            tried.add(t)
            out = os.path.join(tmp, f"try{it}.hevc")
            s = encode(input_y4m, out, t, os.path.join(tmp, f"try{it}.json"), qpmap=qpmap, **encode_kwargs)
            err = 100 * (s["kbps"] / match_kbps - 1)
            attempts.append({"target_kbps": t, "kbps": s["kbps"], "error_percent": err})
            log(f"  try {it}: target {t} kbps -> {s['kbps']:.2f} kbps ({err:+.2f}% vs {match_kbps:.2f})")
            if best is None or abs(err) < abs(best[2]):
                best = (out, s, err)
            if abs(err) <= tolerance:
                break
            target *= match_kbps / s["kbps"]
        out, s, err = best
        shutil.move(out, output)
        s.update(output=output, match_kbps=match_kbps, match_error_percent=err,
                 match_ok=abs(err) <= tolerance, match_tolerance=tolerance, match_attempts=attempts)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
        return s
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
