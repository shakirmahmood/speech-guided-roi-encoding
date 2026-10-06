"""sgroi-view: (re)make the viewable videos of an existing run.

  sgroi-view runs/e001_box_sanity/latest
  sgroi-view runs/e001_box_sanity/latest --style tint --color yellow
  sgroi-view runs/e001_box_sanity/<run id> --no-export
  sgroi-view runs/e001_box_sanity/latest --export-dir ~/Videos/roi

Uses the run's own settings (resolved_config.yaml, `viewing` block, with
defaults for runs made before it existed); options here override them.
Makes each encode's encode.mp4, compare_<condition>.mp4 and compare_all.mp4,
then copies them to the export folder (default: the Windows Videos folder
under WSL). Existing videos are replaced.
"""

import argparse
import os
import sys

import yaml


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sgroi-view", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="run folder, e.g. runs/e001_box_sanity/latest")
    ap.add_argument("--style", choices=["outline", "tint", "none"], help="how the ROI is drawn")
    ap.add_argument("--color", help="ROI colour: red, yellow, green, cyan, magenta, white")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--export", action="store_true", help="copy the videos even outside WSL")
    g.add_argument("--no-export", action="store_true", help="don't copy the videos anywhere")
    ap.add_argument("--export-dir", help="copy the videos under this folder")
    ap.add_argument("--no-audio", action="store_true", help="videos without the clip's audio")
    ap.add_argument("--no-labels", action="store_true", help="no text labels on the panels")
    ap.add_argument("--crf", type=int, help="x264 quality of the videos (default 10; 0 = bit-exact)")
    a = ap.parse_args(argv)

    from ..viewing import make_viewables

    cfg_path = os.path.join(a.run, "resolved_config.yaml")
    if not os.path.isfile(cfg_path):
        print(f"{a.run} is not a run folder (no resolved_config.yaml)", file=sys.stderr)
        return 1
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    view = dict(cfg.get("viewing") or {})
    view["enabled"] = True
    for key, value in (("roi_style", a.style), ("roi_color", a.color), ("export_dir", a.export_dir),
                       ("crf", a.crf)):
        if value is not None:
            view[key] = value
    if a.export or a.export_dir:
        view["export"] = True
    if a.no_export:
        view["export"] = False
    if a.no_audio:
        view["audio"] = False
    if a.no_labels:
        view["labels"] = False
    cfg["viewing"] = view

    try:
        info = make_viewables(a.run, cfg)
    except Exception as e:  # noqa: BLE001
        print(f"failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"{len(info['files'])} videos in {os.path.realpath(a.run)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
