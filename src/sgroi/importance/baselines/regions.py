"""Annotated regions: several objects, possibly moving, each with its own
active times and weight. Used for hand-annotated ("oracle") conditions and for
testing multi-object ROI encoding.

Where the objects are comes from the clip's annotation file
(sgroi/io/annotations.py). When they matter and how much is decided here, per
condition:

    importance:
      type: regions
      objects:                      # optional; default: every object, always, weight 1
        mug:  {active: [[0.0, 2.48]]}            # seconds of the source video
        car:  {active: [[2.48, 6.51]], weight: 1.0}
        keys: {weight: 0.3}                      # no active: the whole clip
      annotations: path.yaml        # optional; default: the clip's annotation file

Importance of a block = weight x the fraction of the block the object's box
covers; where objects overlap, the highest value wins. Objects not listed get
no importance.
"""

import logging

import numpy as np

from ...io.annotations import (AnnotationError, active_frames, clip_times, load_annotations,
                               parse_active, pixel_boxes)
from ...io.qpm import BLOCK, grid_shape
from .. import register

log = logging.getLogger("sgroi.run")


def box_coverage(x0, y0, x1, y1, width, height, block=BLOCK):
    """Fraction of each block [rows, cols] covered by the pixel box [x0, x1) x [y0, y1).
    Matches block_average_frame, whose edge padding repeats the last row/column:
    a box touching the right or bottom edge also covers the padding."""
    rows, cols = grid_shape(width, height, block)
    if x1 >= width:
        x1 = cols * block
    if y1 >= height:
        y1 = rows * block
    edges_x = np.arange(cols + 1) * block
    edges_y = np.arange(rows + 1) * block
    ox = np.clip(np.minimum(edges_x[1:], x1) - np.maximum(edges_x[:-1], x0), 0, block) / block
    oy = np.clip(np.minimum(edges_y[1:], y1) - np.maximum(edges_y[:-1], y0), 0, block) / block
    return np.outer(oy, ox).astype(np.float32)


def object_plan(clip, objects=None, annotations=None):
    """Resolve a condition's object settings against the annotations.
    Returns (Annotations, {id: {"weight": w, "active": intervals or None}})."""
    path = annotations or clip.annotations
    if not path:
        raise AnnotationError(f"clip '{clip.id}' has no annotation file; add `annotations:` to its clip "
                              f"entry or to the condition")
    ann = load_annotations(path)
    if objects is None:
        objects = {oid: {} for oid in ann.objects}
    elif isinstance(objects, (list, tuple)):
        objects = {str(oid): {} for oid in objects}
    elif not isinstance(objects, dict):
        raise AnnotationError("regions: `objects` must be a mapping (or a list of object ids)")
    plan = {}
    for oid, spec in objects.items():
        oid = str(oid)
        if oid not in ann.objects:
            raise AnnotationError(f"regions: object '{oid}' is not in {path} "
                                  f"(known: {', '.join(ann.objects)})")
        spec = spec or {}
        unknown = set(spec) - {"weight", "active"}
        if unknown:
            raise AnnotationError(f"regions: object '{oid}': unknown setting(s) {sorted(unknown)}")
        w = float(spec.get("weight", 1.0))
        if not 0.0 <= w <= 1.0:
            raise AnnotationError(f"regions: object '{oid}': weight must be between 0 and 1 (got {w})")
        plan[oid] = {"weight": w, "active": parse_active(spec.get("active"), f"regions: object '{oid}' active")}
    return ann, plan


@register("regions")
def regions(clip, objects=None, annotations=None):
    ann, plan = object_plan(clip, objects, annotations)
    rows, cols = grid_shape(clip.width, clip.height)
    out = np.zeros((clip.frames, rows, cols), np.float32)
    t = clip_times(clip)
    for oid, p in plan.items():
        on = active_frames(clip, p["active"])
        if not on.any():
            log.warning(f"  regions: object '{oid}' is never active in this clip "
                        f"({t[0]:.2f}-{t[-1]:.2f} s of the source); check its active times")
            continue
        if p["weight"] == 0:
            continue
        boxes = pixel_boxes(ann.objects[oid], clip)
        for i in np.flatnonzero(on):
            x0, y0, x1, y1 = boxes[i]
            if x1 > x0 and y1 > y0:
                np.maximum(out[i], p["weight"] * box_coverage(x0, y0, x1, y1, clip.width, clip.height),
                           out=out[i])
    return out
