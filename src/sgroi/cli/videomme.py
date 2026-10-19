"""sgroi-videomme: list Video-MME videos and download chosen ones into data/raw/.

  sgroi-videomme --list                                   # all 900 videos
  sgroi-videomme --list --duration short --domain "Life Record"
  sgroi-videomme 001 017 fFjv93ACGo8                      # by number or YouTube ID
  sgroi-videomme --duration short --sub-category Cooking  # every match

Each video goes to data/raw/videomme_<number>/videomme_<number>.mp4; videos
already there are skipped. The first call builds the video list
(cache/videomme/index.json) by reading the dataset's file listing, which takes
a minute. Needs `pip install -e .[videomme]` and internet (on the HPC: the
login node, not a compute node). Video-MME is for academic use only.
"""

import argparse
import os
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sgroi-videomme", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="*", help="video numbers (001) or YouTube IDs")
    ap.add_argument("--list", action="store_true", help="only print the matching videos")
    ap.add_argument("--duration", help="short, medium or long")
    ap.add_argument("--domain", help='e.g. "Knowledge", "Life Record"')
    ap.add_argument("--sub-category", help='e.g. "Cooking"')
    ap.add_argument("--data-root", help="folder holding raw/ (default: paths.data_root)")
    a = ap.parse_args(argv)
    if not (a.list or a.videos or a.duration or a.domain or a.sub_category):
        print("name videos or filters to download (or --list); downloading all 900 is ~100 GB",
              file=sys.stderr)
        return 1

    from ..config import load_yaml, resolve_paths
    from ..datasets import videomme
    from ..utils.repo import repo_root

    root = repo_root() or os.getcwd()
    paths = resolve_paths(load_yaml(os.path.join(root, "configs", "paths", "default.yaml")), root)
    raw_dir = os.path.join(a.data_root or paths["data_root"], "raw")

    try:
        index = videomme.load_index(os.path.join(paths["cache_root"], "videomme"))
        picked = videomme.select(index, a.duration, a.domain, a.sub_category)
        if a.videos:
            chosen = [videomme.find(index, k) for k in a.videos]
            picked = [v for v in chosen if v in picked]
    except ImportError as e:
        print(f"{e}: run `pip install -e .[videomme]`", file=sys.stderr)
        return 1
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 1

    if not picked:
        print("no matching videos", file=sys.stderr)
        return 1
    total = sum(v.get("bytes", 0) for v in picked) / 1e9
    print(f"{len(picked)} video(s), {total:.2f} GB")
    for v in picked:
        line = (f"  {v['number']}  {v['id']:<12} {v['duration']:<6} {v['domain'][:18]:<18} "
                f"{v['sub_category'][:22]:<22} {v.get('bytes', 0) / 1e6:7.1f} MB")
        if a.list:
            print(line)
            continue
        print(line, end="  ", flush=True)
        path, new = videomme.download(v, raw_dir)
        print(("downloaded " if new else "already there ") + os.path.relpath(path, root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
