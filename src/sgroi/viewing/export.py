"""Copying viewable videos somewhere easy to open: by default the Windows
Videos folder when running under WSL."""

import os
import shutil
import subprocess
import sys

EXPORT_SUBDIR = "sgroi"


def is_wsl():
    """True when running inside WSL (Linux on Windows)."""
    if not sys.platform.startswith("linux"):
        return False
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        with open("/proc/sys/kernel/osrelease", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _run(cmd, timeout=30):
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (res.stdout or "").strip()
    return out if res.returncode == 0 and out else None


def windows_videos_dir():
    """The Windows Videos folder as a WSL path (e.g. /mnt/c/Users/me/Videos), or
    None. Asks Windows for it, so a Videos folder moved to OneDrive is found too."""
    win = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                "[Environment]::GetFolderPath('MyVideos')"])
    if not win:
        profile = _run(["cmd.exe", "/c", "echo %USERPROFILE%"])
        if profile and "%" not in profile:
            win = profile.rstrip("\\") + "\\Videos"
    if not win:
        return None
    path = _run(["wslpath", "-u", win.splitlines()[-1].strip()])
    return path if path and os.path.isdir(path) else None


def resolve_export_dir(setting, export_dir=None):
    """Where to copy viewable videos, or None for no export.

    setting:    "auto" (only under WSL), True or False
    export_dir: explicit base folder; default <Windows Videos>/sgroi under
                WSL, otherwise ~/Videos/sgroi
    """
    if isinstance(setting, str):
        s = setting.strip().lower()
        if s in ("true", "yes", "on"):
            setting = True
        elif s in ("false", "no", "off"):
            setting = False
        elif s != "auto":
            raise ValueError(f"viewing.export must be auto, true or false (got {setting!r})")
    if setting is False or setting is None:
        return None
    wsl = is_wsl()
    if setting == "auto" and not wsl:
        return None
    if export_dir:
        return os.path.abspath(os.path.expanduser(os.path.expandvars(str(export_dir))))
    if wsl:
        videos = windows_videos_dir()
        if videos:
            return os.path.join(videos, EXPORT_SUBDIR)
        if setting == "auto":
            return None
    return os.path.join(os.path.expanduser("~"), "Videos", EXPORT_SUBDIR)


def export_name(clip, kbps_dir, name):
    """Flat file name for an exported video, e.g. my_clip_600k_compare_box.mp4."""
    return f"{clip}_{kbps_dir}_{name}.mp4"


def export_files(files, dest):
    """Copy [(source path, file name)] into dest; returns the copied paths."""
    os.makedirs(dest, exist_ok=True)
    out = []
    for src, name in files:
        target = os.path.join(dest, name)
        shutil.copyfile(src, target)
        out.append(target)
    return out


def display_path(path):
    """A WSL path like /mnt/c/Users/me/Videos/x as C:\\Users\\me\\Videos\\x, for messages."""
    if is_wsl() and path.startswith("/mnt/") and len(path) > 6 and path[6] == "/":
        return path[5].upper() + ":\\" + path[7:].replace("/", "\\")
    return path
