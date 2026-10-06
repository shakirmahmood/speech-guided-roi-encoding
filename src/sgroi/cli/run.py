"""sgroi-run: run an experiment and record everything in a new run folder.

  sgroi-run experiments/e001_box_sanity
  sgroi-run experiments/e001_box_sanity --clip data/raw/my_clip.mp4
  sgroi-run experiments/e001_box_sanity --set bitrates_kbps=[300,600] --set encoder.preset=fast
  sgroi-run experiments/e001_box_sanity --show-config      # print the resolved config only
"""

import argparse
import sys

import yaml


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(prog="sgroi-run", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("experiment", help="experiment folder, e.g. experiments/e001_box_sanity")
    ap.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE",
                    help="override a config value (dotted key, YAML value); repeatable")
    ap.add_argument("--clip", help="run on this video file instead of the configured clips "
                                   "(uses the experiment's clip_defaults)")
    ap.add_argument("--runs-root", help="where run folders go (default: paths.runs_root)")
    ap.add_argument("--debug", action="store_true", help="also save QP map overlay images")
    ap.add_argument("--show-config", action="store_true", help="print the resolved config and exit")
    a = ap.parse_args(argv)

    from ..runner.experiment import load_experiment, run_experiment

    if a.show_config:
        _, exp_id, cfg, blocks = load_experiment(a.experiment, a.overrides, a.clip)
        print(f"# experiment: {exp_id}\n# blocks: {', '.join(blocks)}")
        print(yaml.safe_dump(cfg, sort_keys=False))
        return 0
    try:
        run_experiment(a.experiment, a.overrides, a.clip, a.runs_root, a.debug,
                       argv=["sgroi-run", *argv])
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"\nrun failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
