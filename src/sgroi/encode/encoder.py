"""Calling the C encoder (src/encoder/roi_x265_encode.c, built into bin/)."""

import json
import os

from ..utils import proc
from ..utils.repo import repo_root


class EncoderError(RuntimeError):
    pass


def find_encoder(path=None):
    """The encoder binary: explicit path, $SGROI_ENCODER, or <repo>/bin/roi_x265_encode."""
    candidates = [path, os.environ.get("SGROI_ENCODER")]
    root = repo_root()
    if root:
        name = "roi_x265_encode" + (".exe" if os.name == "nt" else "")
        candidates.append(os.path.join(root, "bin", name))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    raise EncoderError("encoder not found; build it with `make` at the repository root "
                       "or set SGROI_ENCODER")


def encode(input_y4m, output, kbps, summary_path, qpmap=None, preset="medium", passes=2,
           x265_params="log-level=warning", stats=None, encoder=None):
    """Run one encode; returns the encoder's summary dict (achieved kbps etc.).
    x265_params: "key=value:key=value" string, applied after the preset."""
    cmd = [find_encoder(encoder), "-i", input_y4m, "-o", output, "--bitrate", str(int(round(kbps))),
           "--passes", str(passes), "--preset", preset, "--summary", summary_path]
    if qpmap:
        cmd += ["--qpmap", qpmap]
    if x265_params:
        cmd += ["--x265-params", x265_params]
    if stats:
        cmd += ["--stats", stats]
    try:
        proc.run(cmd)
    except proc.CommandError as e:
        raise EncoderError(str(e)) from None
    with open(summary_path, encoding="utf-8") as f:
        return json.load(f)
