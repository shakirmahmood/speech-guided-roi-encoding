"""Pictures for a sentence: a few frames taken while it is spoken, saved as JPEG files."""

import os
import shutil
import subprocess
import sys


def check_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found: sudo apt install ffmpeg")


def video_duration(video):
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            video,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return float(out)


def frame_times(start, end, n, duration):
    """n times spread evenly over [start, end] (the middle of n equal parts), inside the video."""
    end = max(end, start)
    last = max(0.0, duration - 0.05)
    return [
        round(min(last, max(0.0, start + (i + 0.5) * (end - start) / n)), 3)
        for i in range(n)
    ]


def grab_frame(video, t, path, width):
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            f"{t:.3f}",
            "-i",
            video,
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:-2",
            "-q:v",
            "3",
            path,
        ],
        check=True,
    )
    return path


def sentence_frames(video, n, sentence, count, width, duration, folder):
    """The times and image files of `count` frames for sentence number n (none if count is 0)."""
    times = (
        frame_times(sentence["start"], sentence["end"], count, duration)
        if count > 0
        else []
    )
    images = [
        grab_frame(video, t, os.path.join(folder, f"s{n:03d}_{t:07.3f}s.jpg"), width)
        for t in times
    ]
    return times, images
