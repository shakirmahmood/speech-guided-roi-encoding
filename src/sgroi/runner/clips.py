"""Preparing input clips: trim, scale and convert to 8-bit 4:2:0 Y4M.

Prepared clips are cached under <cache_root>/clips/, keyed by the source
file's checksum and the preparation settings, so repeated runs reuse them.

Clip spec (in configs/clips/*.yaml or experiment config):
  id:        short name used in run folders
  source:    path (absolute, or relative to data_root), or "lavfi:<filtergraph>"
             for an ffmpeg-generated test clip
  start:     seconds to skip (default 0)
  duration:  seconds to use (default: all)
  size:      "WxH" to scale to (default: native size, rounded down to even)
  annotations: object annotation file (see sgroi/io/annotations.py), relative to
             data_root (or the repository's data/ folder), optional
"""

import hashlib
import json
import os

from ..importance import ClipInfo
from ..io.annotations import load_annotations
from ..io.y4m import Y4M
from ..utils import proc
from ..utils.repo import repo_root


def resolve_annotations(path, data_root):
    """Annotation file path: absolute, or relative to data_root, or to the repository's
    own data/ folder (where annotations are kept in git, so they are found even when
    data_root is on another drive), or to the repository root."""
    if os.path.isabs(path):
        candidates = [path]
    else:
        candidates = [os.path.join(data_root, path)]
        root = repo_root()
        if root:
            candidates += [os.path.join(root, "data", path), os.path.join(root, path)]
    candidates = list(dict.fromkeys(os.path.normpath(c) for c in candidates))
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    raise FileNotFoundError(f"annotation file not found: {path} (looked in {', '.join(candidates)})")

PREP_VERSION = 1      # bump when preparation changes, to invalidate the cache


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def prepare_clip(spec, data_root, cache_root, log=print):
    """Returns (ClipInfo, inputs-record dict)."""
    if "id" not in spec or "source" not in spec:
        raise ValueError(f"clip spec needs id and source: {spec}")
    source = str(spec["source"])
    start = float(spec.get("start", 0) or 0)
    duration = spec.get("duration")
    size = spec.get("size")

    if source.startswith("lavfi:"):
        src_in = ["-f", "lavfi", "-i", source[len("lavfi:"):]]
        src_path, checksum = None, None
        if start:
            src_in = src_in[:-2] + ["-ss", str(start)] + src_in[-2:]
    else:
        src_path = source if os.path.isabs(source) else os.path.join(data_root, source)
        if not os.path.isfile(src_path):
            raise FileNotFoundError(f"clip '{spec['id']}': source not found: {src_path}")
        checksum = sha256_file(src_path)
        src_in = (["-ss", str(start)] if start else []) + ["-i", src_path]

    key_data = {"v": PREP_VERSION, "source": source if checksum is None else checksum,
                "start": start, "duration": duration, "size": size}
    key = hashlib.sha1(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:12]
    out_dir = os.path.join(cache_root, "clips")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{spec['id']}_{key}.y4m")

    if os.path.isfile(out):
        log(f"clip {spec['id']}: using cached {os.path.relpath(out, cache_root)}")
    else:
        if size:
            w, h = str(size).lower().split("x")
            vf = f"scale={int(w)}:{int(h)}"
        else:
            vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        cmd = ["ffmpeg", "-v", "error", "-y", *src_in]
        if duration:
            cmd += ["-t", str(duration)]
        tmp = out + ".part"
        cmd += ["-an", "-vf", vf, "-pix_fmt", "yuv420p", "-f", "yuv4mpegpipe", tmp]
        log(f"clip {spec['id']}: preparing")
        proc.run(cmd)
        os.replace(tmp, out)

    annotations, ann_sha = None, None
    if spec.get("annotations"):
        annotations = resolve_annotations(str(spec["annotations"]), data_root)
        ann = load_annotations(annotations)               # validate early, before any encoding
        ann_sha = ann.file_sha256
        if ann.source_sha256 and checksum and ann.source_sha256 != checksum:
            log(f"clip {spec['id']}: WARNING: {os.path.basename(annotations)} was made for a different "
                f"video (source_sha256 {ann.source_sha256[:12]}… vs {checksum[:12]}…)")

    y = Y4M(out)
    info = ClipInfo(id=spec["id"], path=out, width=y.width, height=y.height, frames=y.frames,
                    fps=y.fps, source=dict(spec), annotations=annotations, source_sha256=checksum)
    record = {"id": spec["id"], "source": source, "source_path": src_path, "source_sha256": checksum,
              "start": start, "duration": duration, "size": size, "prepared": out,
              "width": y.width, "height": y.height, "frames": y.frames, "fps": [y.fps_num, y.fps_den],
              "annotations": annotations, "annotations_sha256": ann_sha}
    return info, record
