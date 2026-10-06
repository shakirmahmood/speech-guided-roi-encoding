"""Locating the repository root and its git state."""

import os
import subprocess


def repo_root(start=None):
    """Nearest folder at or above `start` (default: this package, then the
    current directory) that contains both pyproject.toml and configs/."""
    starts = [start] if start else [os.path.dirname(os.path.abspath(__file__)), os.getcwd()]
    if os.environ.get("SGROI_ROOT"):
        starts.insert(0, os.environ["SGROI_ROOT"])
    for s in starts:
        d = os.path.abspath(s)
        while True:
            if os.path.isfile(os.path.join(d, "pyproject.toml")) and os.path.isdir(os.path.join(d, "configs")):
                return d
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


def _git(root, *args):
    try:
        res = subprocess.run(["git", "-C", root, *args], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError:
        return None
    return res.stdout if res.returncode == 0 else None


def git_state(root):
    """Commit, branch, dirty flag and a patch of uncommitted changes (incl. untracked
    text files), so a run made with local edits can still be reproduced."""
    commit = _git(root, "rev-parse", "HEAD")
    if commit is None:
        return {"available": False}
    status = _git(root, "status", "--porcelain") or ""
    patch = _git(root, "diff", "HEAD", "--binary") or ""
    untracked = _git(root, "ls-files", "--others", "--exclude-standard") or ""
    for rel in untracked.splitlines():
        path = os.path.join(root, rel)
        try:
            if os.path.getsize(path) > 1_000_000:
                patch += f"\n# untracked file not included (over 1 MB): {rel}\n"
                continue
        except OSError:
            continue
        res = subprocess.run(["git", "-C", root, "diff", "--no-index", "--binary", "--", os.devnull, rel],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        patch += res.stdout
    return {
        "available": True,
        "commit": commit.strip(),
        "branch": (_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip(),
        "dirty": bool(status.strip()),
        "status": status,
        "patch": patch,
    }
