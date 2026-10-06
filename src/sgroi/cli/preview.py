"""sgroi-preview-regions: check a clip's annotated objects (and a condition's
timing) on the video before running an experiment. Nothing is encoded.

  sgroi-preview-regions experiments/e002_multi_region                     # all objects
  sgroi-preview-regions experiments/e002_multi_region --condition timed   # + active/off, boosted area
  sgroi-preview-regions experiments/e002_multi_region --condition timed --set qpmap.k=10

Writes <cache>/previews/<experiment>/<clip>_<condition>.mp4 (or -o), and under
WSL also copies it to the Windows Videos folder (sgroi/previews/<experiment>/),
following the experiment's viewing.export setting.
"""

import argparse
import os
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sgroi-preview-regions", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("experiment", help="experiment folder, e.g. experiments/e002_multi_region")
    ap.add_argument("--condition", help="a condition of the experiment: show its timing, weights and boosted area")
    ap.add_argument("--clip", help="use this video instead of the configured clips (needs clip_defaults.annotations)")
    ap.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE",
                    help="override a config value, as in sgroi-run; repeatable")
    ap.add_argument("--no-map", action="store_true", help="don't tint the area the QP map boosts")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-export", action="store_true", help="don't copy the preview anywhere")
    ap.add_argument("-o", "--output", help="output file (single clip only)")
    a = ap.parse_args(argv)

    from ..config import resolve_paths
    from ..importance import get_source
    from ..importance.baselines.regions import object_plan
    from ..maps.conversion import blocks_to_qp
    from ..runner.clips import prepare_clip
    from ..runner.experiment import load_experiment
    from .. import viewing
    from ..viewing.export import display_path, export_files, resolve_export_dir
    from ..viewing.preview import make_preview
    from ..viewing.video import AudioSource

    try:
        root, exp_id, cfg, _ = load_experiment(a.experiment, a.overrides, a.clip)
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 1
    paths = resolve_paths(cfg.get("paths"), root)
    cond = None
    if a.condition:
        if a.condition not in cfg["conditions"]:
            print(f"error: no condition '{a.condition}' (have: {', '.join(cfg['conditions'])})", file=sys.stderr)
            return 1
        cond = cfg["conditions"][a.condition]
    if a.output and len(cfg["clips"]) > 1:
        print("error: -o works with a single clip only", file=sys.stderr)
        return 1
    view = viewing.viewing_config(cfg)
    dest_base = None if a.no_export else resolve_export_dir(view["export"], view["export_dir"])

    made = []
    for spec in cfg["clips"]:
        try:
            clip, inp = prepare_clip(spec, paths["data_root"], paths["cache_root"])
        except Exception as e:  # noqa: BLE001
            print(f"error: clip {spec.get('id')}: {e}", file=sys.stderr)
            return 1
        if not clip.annotations:
            print(f"clip {clip.id}: no annotation file, skipped")
            continue
        plan = offsets = None
        if cond:
            imp = dict(cond.get("importance") or {})
            kind = imp.pop("type")
            if kind == "regions":
                _, plan = object_plan(clip, imp.get("objects"), imp.get("annotations"))
            if not a.no_map:
                offsets = blocks_to_qp(get_source(kind)(clip, **imp), **{**cfg["qpmap"], **(cond.get("qpmap") or {})})
        audio = None
        if not a.no_audio and inp.get("source_path") and os.path.isfile(inp["source_path"]):
            audio = AudioSource(inp["source_path"], float(inp.get("start") or 0), inp.get("duration"))
        name = f"{clip.id}_{a.condition or 'objects'}.mp4"
        out = a.output or os.path.join(paths["cache_root"], "previews", exp_id, name)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        n = make_preview(clip, out, plan, offsets, audio, roi_threshold=cfg["metrics"]["roi_threshold"])
        print(f"clip {clip.id}: {n} frames -> {out}")
        made.append((out, name))
    if dest_base and made:
        dest = os.path.join(dest_base, "previews", exp_id)
        export_files(made, dest)
        print(f"copied to {display_path(dest)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
