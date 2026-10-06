"""Importance sources: everything that decides which regions matter.

Every source has the same interface, so the rest of the pipeline (QP maps,
encoding, metrics) is shared by all methods:

    blocks = source(clip, **params)

clip:    ClipInfo (prepared Y4M path, width, height, frames, fps, source info)
returns: float array [frames, rows, cols] in 0-1, on the 16x16 block grid
         (rows, cols = sgroi.io.qpm.grid_shape(width, height)).

Sources that work at pixel level can use sgroi.maps.block_average().

baselines/  comparison methods (dummy box, later ViNet/AViNet, simple noun extraction)
ours/       the proposed speech-interpretation pipeline (added when implemented)
controls    sanity-check sources (all-zero importance)

Register a source with @register("name"); experiment configs refer to it as
importance: {type: name, ...params}. A "module.path:function" type string
also works, for trying out a source without registering it.
"""

import importlib
from dataclasses import dataclass, field

_REGISTRY = {}


@dataclass
class ClipInfo:
    id: str
    path: str               # prepared 8-bit 4:2:0 Y4M
    width: int
    height: int
    frames: int
    fps: float
    source: dict = field(default_factory=dict)   # original clip spec (source file, start, ...)


def register(name):
    def deco(fn):
        _REGISTRY[name] = fn
        return fn
    return deco


def get_source(type_name):
    if ":" in type_name:
        module, func = type_name.split(":", 1)
        return getattr(importlib.import_module(module), func)
    _load_builtin()
    if type_name not in _REGISTRY:
        raise KeyError(f"unknown importance source '{type_name}'; known: {', '.join(sorted(_REGISTRY))}")
    return _REGISTRY[type_name]


def available():
    _load_builtin()
    return sorted(_REGISTRY)


def _load_builtin():
    from . import controls  # noqa: F401
    from .baselines import box  # noqa: F401
