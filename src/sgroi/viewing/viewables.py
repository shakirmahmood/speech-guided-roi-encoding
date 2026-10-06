"""Viewable outputs for a run folder: MP4s, comparison videos, export.

For every clip and bitrate in runs/<experiment>/<run>/clips/<clip>/<kbps>k/:
  <condition>/encode.mp4    each encode (baseline too) as a playable MP4
  compare_<condition>.mp4   baseline | condition, both with the condition's ROI drawn
  compare_all.mp4           baseline and every condition in a grid (2+ conditions)
Then the videos are copied to an easy-to-open folder (default: the Windows
Videos folder under WSL), named <clip>_<kbps>k_<name>.mp4, and listed in
<run>/viewing.json.

Everything is read from the run folder (resolved_config.yaml, inputs.json,
metadata.json, summaries and QP maps), so it works for old runs too
(sgroi-view) and doesn't need the prepared clips in cache/.
"""

import json
import os

import yaml

from ..io.qpm import read_qpm
from .export import display_path, export_files, export_name, is_wsl, resolve_export_dir
from .video import AudioSource, Panel, make_compare, to_mp4

VIEWING_DEFAULTS = {
    "enabled": True,
    "mp4": True,             # each encode as encode.mp4 next to encode.hevc
    "compare": True,         # compare_<condition>.mp4: baseline | condition
    "grid": True,            # compare_all.mp4 when 2+ conditions are compared
    "skip_identical": True,  # leave out conditions expected to equal the baseline (e.g. zeros)
    "roi_style": "outline",  # outline | tint | none
    "roi_color": "red",      # red | yellow | green | cyan | magenta | white
    "labels": True,          # condition name and achieved bitrate on each panel
    "audio": True,           # add the source clip's audio, when it has any
    "crf": 10,               # x264 quality of all viewing videos: 10 visually lossless, 0 bit-exact
    "max_width": 2560,       # comparison videos wider than this are scaled down
    "export": "auto",        # copy to export_dir: auto (only under WSL) | true | false
    "export_dir": None,      # default: <Windows Videos>/sgroi under WSL, else ~/Videos/sgroi
}


def viewing_config(cfg):
    return {**VIEWING_DEFAULTS, **((cfg or {}).get("viewing") or {})}


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _kbps_dirs(clip_dir):
    out = []
    for name in os.listdir(clip_dir):
        if name.endswith("k") and name[:-1].isdigit() and os.path.isdir(os.path.join(clip_dir, name)):
            out.append(name)
    return sorted(out, key=lambda n: int(n[:-1]), reverse=True)


def _audio_for(inp, enabled, log):
    if not enabled or not inp or not inp.get("source_path"):
        return None
    path = inp["source_path"]
    if not os.path.isfile(path):
        log(f"  viewing: source {path} not found; videos without audio")
        return None
    return AudioSource(path, float(inp.get("start") or 0), inp.get("duration"))


def _label(name, s, base):
    text = f"{name}  {s['kbps']:.1f} kbps"
    if base is not None and s is not base:
        text += f" ({100 * (s['kbps'] / base['kbps'] - 1):+.2f}%)"
    return text


def make_viewables(run_dir, cfg=None, log=print):
    """Make the viewable videos for a run folder and export them.
    Returns a summary dict (also written to <run>/viewing.json)."""
    run_dir = os.path.realpath(run_dir)
    if cfg is None:
        with open(os.path.join(run_dir, "resolved_config.yaml"), encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    view = viewing_config(cfg)
    if not view["enabled"]:
        return {"status": "disabled"}

    meta = _load_json(os.path.join(run_dir, "metadata.json"), {})
    experiment = meta.get("experiment") or os.path.basename(os.path.dirname(run_dir))
    run_id = meta.get("run_id") or os.path.basename(run_dir)
    inputs = {i["id"]: i for i in _load_json(os.path.join(run_dir, "inputs.json"), [])}
    conditions = cfg.get("conditions") or {}
    threshold = (cfg.get("metrics") or {}).get("roi_threshold", -0.5)
    draw = dict(roi_style=view["roi_style"], roi_color=view["roi_color"], roi_threshold=threshold,
                labels=view["labels"], crf=view["crf"], max_width=view["max_width"])

    clips_root = os.path.join(run_dir, "clips")
    if not os.path.isdir(clips_root):
        raise FileNotFoundError(f"{run_dir} has no clips/ folder (not a run folder?)")
    made = []                                           # (path, export file name)
    for clip in sorted(os.listdir(clips_root)):
        clip_dir = os.path.join(clips_root, clip)
        if not os.path.isdir(clip_dir):
            continue
        audio = _audio_for(inputs.get(clip), view["audio"], log)
        maps = {}
        for name in conditions:
            qpm = os.path.join(clip_dir, "maps", f"{name}.qpm")
            if os.path.isfile(qpm):
                maps[name] = read_qpm(qpm)[0]
        for kdir_name in _kbps_dirs(clip_dir):
            kdir = os.path.join(clip_dir, kdir_name)
            base_dir = os.path.join(kdir, "baseline")
            base = _load_json(os.path.join(base_dir, "summary.json"), None)
            if base is None or not os.path.isfile(os.path.join(base_dir, "encode.hevc")):
                log(f"  viewing: {clip} {kdir_name}: no baseline encode, skipped")
                continue
            w, h, fn, fd = base["width"], base["height"], base["fps_num"], base["fps_den"]
            seconds = base.get("seconds") or base["frames"] * fd / fn
            names = [n for n in conditions
                     if os.path.isfile(os.path.join(kdir, n, "encode.hevc"))
                     and not (view["skip_identical"] and (conditions[n] or {}).get("expect_identical_to_baseline"))]
            summ = {n: _load_json(os.path.join(kdir, n, "summary.json"), {"kbps": float("nan")}) for n in names}
            log(f"  viewing: {clip} @ {kdir_name}")

            if view["mp4"]:
                for n in ["baseline", *names]:
                    out = to_mp4(os.path.join(kdir, n, "encode.hevc"), os.path.join(kdir, n, "encode.mp4"),
                                 fn, fd, audio, view["crf"], seconds)
                    made.append((out, export_name(clip, kdir_name, n)))

            base_panel_label = _label("baseline", base, None)
            if view["compare"]:
                for n in names:
                    out = os.path.join(kdir, f"compare_{n}.mp4")
                    panels = [Panel(base_panel_label, os.path.join(base_dir, "encode.hevc"), maps.get(n)),
                              Panel(_label(n, summ[n], base), os.path.join(kdir, n, "encode.hevc"), maps.get(n))]
                    make_compare(panels, out, w, h, fn, fd, audio, seconds=seconds, **draw)
                    made.append((out, export_name(clip, kdir_name, f"compare_{n}")))
            if view["grid"] and len(names) >= 2:
                out = os.path.join(kdir, "compare_all.mp4")
                panels = [Panel(base_panel_label, os.path.join(base_dir, "encode.hevc"))]
                panels += [Panel(_label(n, summ[n], base), os.path.join(kdir, n, "encode.hevc"), maps.get(n))
                           for n in names]
                make_compare(panels, out, w, h, fn, fd, audio, seconds=seconds, **draw)
                made.append((out, export_name(clip, kdir_name, "compare_all")))

    info = {"status": "ok", "files": [os.path.relpath(p, run_dir) for p, _ in made],
            "export_dir": None, "exported": []}
    dest_base = resolve_export_dir(view["export"], view["export_dir"])
    if dest_base and made:
        dest = os.path.join(dest_base, experiment, run_id)
        info["export_dir"] = dest
        info["exported"] = export_files(made, dest)
        log(f"  viewing: {len(made)} videos copied to {display_path(dest)}")
    elif not dest_base and view["export"] == "auto":
        if is_wsl():
            log("  viewing: Windows Videos folder not found, videos not copied; "
                "set viewing.export_dir (e.g. /mnt/c/Users/<you>/Videos/sgroi)")
        else:
            log("  viewing: videos are in the run folder (export: auto copies them only under WSL)")
    with open(os.path.join(run_dir, "viewing.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    return info
