"""Object annotations: where the objects in a clip are (geometry only).

When an object matters and how much is not stored here: that is what an
experiment's conditions decide (see importance/baselines/regions.py). This
keeps one annotation file per clip, shared by every experiment.

data/annotations/<clip>.yaml:

    clip: car_cup_keys
    source_sha256: 0d11...          # optional: the video these belong to (checked)
    frame_size: [1920, 1080]        # optional: boxes are pixels of this size;
                                    # without it, boxes are fractions of the frame
    objects:
      mug:                          # static object
        box: [0.250, 0.339, 0.151, 0.331]
      car:                          # moving object: interpolated between keyframes
        label: blue toy car         # optional, for previews and reports
        keyframes:
          - {t: 0.0, box: [0.016, 0.692, 0.181, 0.119]}
          - {t: 6.6, box: [0.431, 0.630, 0.140, 0.107]}
      ball:                         # per-frame track from a tracker
        track: car_cup_keys_ball.csv    # columns t,x,y,w,h; path relative to this file

Boxes are x, y, width, height from the top-left corner. Times are seconds of
the source video (not of a trimmed clip), so one file serves any trimming.
Between keyframes boxes are interpolated linearly; before the first and after
the last keyframe they hold still.
"""

import csv
import hashlib
import os
from dataclasses import dataclass, field

import numpy as np
import yaml


class AnnotationError(ValueError):
    pass


@dataclass
class ObjectTrack:
    """One object's position over time: boxes [K, 4] (x, y, w, h as fractions
    of the frame) at times [K] (seconds of the source video, increasing)."""
    id: str
    times: np.ndarray
    boxes: np.ndarray
    label: str = ""

    def boxes_at(self, t):
        """Boxes at times t (array): [len(t), 4] fractions, interpolated and held."""
        t = np.asarray(t, dtype=np.float64)
        if len(self.times) == 1:
            return np.repeat(self.boxes[:1], len(t), axis=0)
        return np.stack([np.interp(t, self.times, self.boxes[:, j]) for j in range(4)], axis=1)


@dataclass
class Annotations:
    path: str
    clip: str
    objects: dict                       # id -> ObjectTrack, in file order
    source_sha256: str = None
    file_sha256: str = None
    extra: dict = field(default_factory=dict)


def _box(values, where, scale):
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        raise AnnotationError(f"{where}: box must be [x, y, w, h]")
    try:
        x, y, w, h = (float(v) / s for v, s in zip(values, scale))
    except (TypeError, ValueError):
        raise AnnotationError(f"{where}: box values must be numbers") from None
    if w <= 0 or h <= 0:
        raise AnnotationError(f"{where}: box width and height must be positive")
    tol = 1e-6
    if min(x, y) < -tol or x + w > 1 + 1e-3 or y + h > 1 + 1e-3:
        hint = "" if scale != (1, 1, 1, 1) else " (pixel boxes need frame_size: [W, H])"
        raise AnnotationError(f"{where}: box {list(values)} lies outside the frame{hint}")
    return [x, y, w, h]


def _keyframes(items, where, scale):
    if not isinstance(items, list) or not items:
        raise AnnotationError(f"{where}: keyframes must be a non-empty list")
    times, boxes = [], []
    for n, kf in enumerate(items):
        if not isinstance(kf, dict) or "t" not in kf or "box" not in kf:
            raise AnnotationError(f"{where}: keyframe {n} needs t and box")
        times.append(float(kf["t"]))
        boxes.append(_box(kf["box"], f"{where} keyframe t={kf['t']}", scale))
    if any(b <= a for a, b in zip(times, times[1:])):
        raise AnnotationError(f"{where}: keyframe times must be strictly increasing")
    return times, boxes


def _track_csv(path, where, scale):
    if not os.path.isfile(path):
        raise AnnotationError(f"{where}: track file not found: {path}")
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    missing = {"t", "x", "y", "w", "h"} - set(rows[0] if rows else {})
    if missing:
        raise AnnotationError(f"{where}: track file needs columns t,x,y,w,h (missing {sorted(missing)})")
    return _keyframes([{"t": r["t"], "box": [r["x"], r["y"], r["w"], r["h"]]} for r in rows], where, scale)


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def load_annotations(path):
    """Read and validate an annotation file. Raises AnnotationError with the
    file and object named when something is wrong."""
    if not os.path.isfile(path):
        raise AnnotationError(f"annotation file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    objs = data.get("objects")
    if not isinstance(objs, dict) or not objs:
        raise AnnotationError(f"{path}: needs an 'objects' mapping with at least one object")
    scale = (1, 1, 1, 1)
    if data.get("frame_size") is not None:
        fs = data["frame_size"]
        if not isinstance(fs, (list, tuple)) or len(fs) != 2 or min(float(v) for v in fs) <= 0:
            raise AnnotationError(f"{path}: frame_size must be [width, height]")
        scale = (float(fs[0]), float(fs[1]), float(fs[0]), float(fs[1]))
    objects = {}
    for oid, spec in objs.items():
        where = f"{path}: object '{oid}'"
        spec = spec or {}
        kinds = [k for k in ("box", "keyframes", "track") if k in spec]
        if len(kinds) != 1:
            raise AnnotationError(f"{where}: give exactly one of box, keyframes or track")
        if kinds == ["box"]:
            times, boxes = [0.0], [_box(spec["box"], where, scale)]
        elif kinds == ["keyframes"]:
            times, boxes = _keyframes(spec["keyframes"], where, scale)
        else:
            track = spec["track"]
            track = track if os.path.isabs(track) else os.path.join(os.path.dirname(path), track)
            times, boxes = _track_csv(track, where, scale)
        objects[str(oid)] = ObjectTrack(str(oid), np.array(times, np.float64), np.array(boxes, np.float64),
                                        str(spec.get("label") or oid))
    return Annotations(path=os.path.abspath(path), clip=str(data.get("clip") or ""), objects=objects,
                       source_sha256=data.get("source_sha256"), file_sha256=sha256_file(path),
                       extra={k: v for k, v in data.items() if k not in ("clip", "objects", "source_sha256",
                                                                         "frame_size")})


def clip_times(clip):
    """Source-video time (s) of each frame of a prepared clip."""
    start = float((clip.source or {}).get("start") or 0.0)
    return start + np.arange(clip.frames) / float(clip.fps)


def pixel_boxes(track, clip):
    """An object's box in every frame of the prepared clip, as integer pixel
    bounds [frames, 4] = (x0, y0, x1, y1), clipped to the frame."""
    b = track.boxes_at(clip_times(clip))
    x0 = np.clip(np.round(b[:, 0] * clip.width), 0, clip.width)
    y0 = np.clip(np.round(b[:, 1] * clip.height), 0, clip.height)
    x1 = np.clip(np.round((b[:, 0] + b[:, 2]) * clip.width), 0, clip.width)
    y1 = np.clip(np.round((b[:, 1] + b[:, 3]) * clip.height), 0, clip.height)
    return np.stack([x0, y0, x1, y1], axis=1).astype(np.int64)


def parse_active(active, where="active"):
    """'all' / None -> None (always active); otherwise a list of [start, end)
    intervals in seconds of the source video."""
    if active is None or (isinstance(active, str) and active.strip().lower() == "all"):
        return None
    if not isinstance(active, (list, tuple)) or not active:
        raise AnnotationError(f"{where}: must be 'all' or a list of [start, end] intervals in seconds")
    if len(active) == 2 and all(isinstance(v, (int, float)) for v in active):
        active = [active]                                   # a single [start, end]
    out = []
    for iv in active:
        if not isinstance(iv, (list, tuple)) or len(iv) != 2:
            raise AnnotationError(f"{where}: each interval must be [start, end] (got {iv!r})")
        a, b = float(iv[0]), float(iv[1])
        if b <= a:
            raise AnnotationError(f"{where}: interval [{a}, {b}] ends before it starts")
        out.append((a, b))
    return out


def active_frames(clip, intervals):
    """Boolean [frames]: frame active if its source time falls in [start, end)."""
    t = clip_times(clip)
    if intervals is None:
        return np.ones(len(t), bool)
    m = np.zeros(len(t), bool)
    for a, b in intervals:
        m |= (t >= a) & (t < b)
    return m
