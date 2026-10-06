"""Experiment configuration: plain YAML, composed from reusable blocks.

experiments/<id>/config.yaml names the blocks it uses under `defaults`:

    defaults:
      paths: default        -> configs/paths/default.yaml   -> cfg["paths"]
      encoder: medium_2pass -> configs/encoder/medium_2pass.yaml -> cfg["encoder"]
      ...

Its own keys are then merged on top (nested dicts merge key by key; any other
value replaces), and finally command-line overrides ("encoder.preset=slow")
are applied. The fully resolved result is what a run records.
"""

import copy
import os

import yaml


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {} if data is None else data


def deep_merge(base, over):
    """Merge `over` into a copy of `base`: dicts recursively, everything else replaced."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def set_dotted(cfg, dotted, value):
    """cfg["a"]["b"]["c"] = value for dotted = "a.b.c" (creating dicts as needed)."""
    keys = dotted.split(".")
    d = cfg
    for k in keys[:-1]:
        if not isinstance(d.get(k), dict):
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value


def parse_override(text):
    """'a.b=value' -> ('a.b', parsed value); the value is read as YAML, so
    numbers, lists ([300, 600]) and booleans work."""
    if "=" not in text:
        raise ValueError(f"override must look like key.path=value, got '{text}'")
    key, raw = text.split("=", 1)
    return key.strip(), yaml.safe_load(raw)


def compose(experiment_config_path, configs_dir, overrides=()):
    """Returns (resolved config dict, list of block files used)."""
    exp = load_yaml(experiment_config_path)
    defaults = exp.pop("defaults", {}) or {}
    if isinstance(defaults, list):                 # also accept [{group: name}, ...]
        merged = {}
        for item in defaults:
            merged.update(item)
        defaults = merged
    cfg, used = {}, []
    for group, name in defaults.items():
        path = os.path.join(configs_dir, group, f"{name}.yaml")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"config block not found: {path}")
        cfg[group] = load_yaml(path)
        used.append(os.path.relpath(path, os.path.dirname(configs_dir)))
    cfg = deep_merge(cfg, exp)
    for ov in overrides:
        key, value = parse_override(ov)
        set_dotted(cfg, key, value)
    return cfg, used


def resolve_paths(paths_cfg, root):
    """Make every entry of the paths block absolute (relative entries are
    relative to the repository root)."""
    out = {}
    for k, v in (paths_cfg or {}).items():
        v = os.path.expanduser(os.path.expandvars(str(v)))
        out[k] = v if os.path.isabs(v) else os.path.normpath(os.path.join(root, v))
    for k, default in (("data_root", "data"), ("cache_root", "cache"), ("runs_root", "runs"),
                       ("models_root", "models")):
        out.setdefault(k, os.path.join(root, default))
    return out
