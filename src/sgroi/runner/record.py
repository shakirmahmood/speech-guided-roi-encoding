"""The run folder: a self-describing, never-overwritten record of one execution.

runs/<experiment>/<UTC time>_<commit>[_dirty]/
  resolved_config.yaml   every setting used
  metadata.json          git state, status, times, machine, tool versions, command line
  source.patch           uncommitted changes, if any
  inputs.json            clips used (with checksums) and prepared files
  commands.txt           every external command run
  logs/run.log           full log
"""

import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

import yaml

from .. import __version__
from ..utils import proc
from ..utils.repo import git_state


def _utc(fmt="%Y-%m-%dT%H:%M:%SZ"):
    return datetime.now(timezone.utc).strftime(fmt)


def _tool_versions():
    v = {"python": sys.version.split()[0], "sgroi": __version__}
    for mod in ("numpy", "scipy", "yaml", "PIL"):
        try:
            v[mod] = __import__(mod).__version__
        except Exception:  # noqa: BLE001
            pass
    try:
        out = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        v["ffmpeg"] = out.stdout.splitlines()[0] if out.stdout else None
    except FileNotFoundError:
        v["ffmpeg"] = None
    return v


class RunRecord:
    def __init__(self, runs_root, experiment_id, cfg, root, argv, config_blocks=()):
        self.git = git_state(root)
        if self.git["available"]:
            suffix = self.git["commit"][:7] + ("_dirty" if self.git["dirty"] else "")
        else:
            suffix = "nogit"
        self.run_id = f"{_utc('%Y-%m-%dT%H%M%SZ')}_{suffix}"
        self.exp_dir = os.path.join(runs_root, experiment_id)
        self.dir = os.path.join(self.exp_dir, self.run_id)
        n = 1
        while os.path.exists(self.dir):                  # never overwrite
            n += 1
            self.dir = os.path.join(self.exp_dir, f"{self.run_id}-{n}")
        os.makedirs(os.path.join(self.dir, "logs"))
        self.start = time.time()
        self.inputs = []
        self.meta = {
            "experiment": experiment_id,
            "run_id": os.path.basename(self.dir),
            "status": "running",
            "started": _utc(),
            "command": argv,
            "config_blocks": list(config_blocks),
            "git": {k: v for k, v in self.git.items() if k != "patch"},
            "host": {"hostname": socket.gethostname(), "platform": platform.platform(),
                     "cpus": os.cpu_count()},
            "tools": _tool_versions(),
        }
        with open(self.path("resolved_config.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        if self.git.get("dirty"):
            with open(self.path("source.patch"), "w", encoding="utf-8") as f:
                f.write(self.git["patch"])
        self._write_meta()
        proc.set_command_log(self.path("commands.txt"))
        self._setup_logging()
        self._link_latest()

    def path(self, *parts):
        return os.path.join(self.dir, *parts)

    def _write_meta(self):
        with open(self.path("metadata.json"), "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2)

    def _setup_logging(self):
        self.log = logging.getLogger("sgroi.run")
        self.log.setLevel(logging.INFO)
        self.log.handlers.clear()
        fh = logging.FileHandler(self.path("logs", "run.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("%(message)s"))
        self.log.addHandler(fh)
        self.log.addHandler(sh)

    def _link_latest(self):
        link = os.path.join(self.exp_dir, "latest")
        try:
            if os.path.islink(link) or os.path.isfile(link):
                os.remove(link)
            os.symlink(os.path.basename(self.dir), link)
        except OSError:                                  # e.g. Windows without symlink rights
            with open(os.path.join(self.exp_dir, "LATEST.txt"), "w", encoding="utf-8") as f:
                f.write(os.path.basename(self.dir) + "\n")

    def add_input(self, entry):
        self.inputs.append(entry)
        with open(self.path("inputs.json"), "w", encoding="utf-8") as f:
            json.dump(self.inputs, f, indent=2)

    def set_tool(self, name, value):
        self.meta["tools"][name] = value
        self._write_meta()

    def finish(self, status, error=None):
        self.meta["status"] = status
        self.meta["finished"] = _utc()
        self.meta["duration_s"] = round(time.time() - self.start, 1)
        if error:
            self.meta["error"] = error
        self._write_meta()
        proc.set_command_log(None)
        for h in list(self.log.handlers):
            h.close()
            self.log.removeHandler(h)
