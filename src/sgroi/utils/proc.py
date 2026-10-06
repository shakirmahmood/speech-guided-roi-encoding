"""Running external commands, with an optional log of every command run.

The experiment runner points the log at <run>/commands.txt, so each run
records exactly which external commands (ffmpeg, encoder) produced it.
"""

import shlex
import subprocess
from datetime import datetime, timezone

_command_log = None


def set_command_log(path):
    """Append every command run from now on to `path` (None to stop)."""
    global _command_log
    _command_log = path


def _log(cmd):
    if _command_log:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(_command_log, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {shlex.join(str(c) for c in cmd)}\n")


class CommandError(RuntimeError):
    def __init__(self, cmd, returncode, output):
        tail = "\n".join((output or "").strip().splitlines()[-10:])
        super().__init__(f"command failed ({returncode}): {shlex.join(str(c) for c in cmd)}\n{tail}")
        self.cmd, self.returncode, self.output = cmd, returncode, output


def run(cmd, check=True):
    """Run a command, capture stdout+stderr as text, return the output."""
    cmd = [str(c) for c in cmd]
    _log(cmd)
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if check and res.returncode != 0:
        raise CommandError(cmd, res.returncode, res.stdout)
    return res.stdout


def popen(cmd, **kwargs):
    """Start a command (for streaming output, e.g. decoded frames)."""
    cmd = [str(c) for c in cmd]
    _log(cmd)
    return subprocess.Popen(cmd, **kwargs)
