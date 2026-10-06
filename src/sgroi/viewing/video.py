"""ffmpeg I/O for viewable outputs: MP4s of encodes and comparison videos.

The encoder writes raw HEVC, which has no timestamps; copying it into MP4
without re-encoding loses frames at the end (B-frame reordering) and breaks
audio. So viewable MP4s are decoded and re-encoded with x264: crf 10 is
visually lossless (~54 dB PSNR against the decoded HEVC) and plays in any
player; crf 0 is bit-exact (High 4:4:4 Predictive profile: VLC plays it,
Windows' built-in player may not). Measurements always use the .hevc.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass

import numpy as np

from ..utils import proc
from .draw import Label, RoiPainter, grid_layout


@dataclass
class AudioSource:
    """Audio to add to a viewable video: the original clip's file, trimmed the
    same way the clip was prepared. Files without audio are handled (no audio)."""
    path: str
    start: float = 0.0
    duration: float = None

    def input_args(self):
        args = ["-ss", str(self.start)] if self.start else []
        if self.duration:
            args += ["-t", str(self.duration)]
        return args + ["-i", self.path]


AUDIO_OUT = ["-map", "1:a:0?", "-c:a", "aac", "-b:a", "192k"]


def fps_arg(fps_num, fps_den):
    return f"{int(fps_num)}/{int(fps_den)}"


def _x264(crf, preset="medium"):
    return ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]


def _tail(audio, seconds, out):
    """Audio mapping, length limit and container options for the output.
    The length is the video's, so audio that is longer is cut and audio that
    is shorter just ends early (the video is never shortened)."""
    args = AUDIO_OUT[:] if audio else []
    if seconds:
        args += ["-t", f"{seconds:.6f}"]
    return args + ["-movflags", "+faststart", out]


def to_mp4(hevc, out, fps_num, fps_den, audio=None, crf=10, seconds=None):
    """An encode as a playable MP4 at its exact frame rate, optionally with the
    clip's audio. seconds: video length (frames / fps), to trim the audio."""
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", fps_arg(fps_num, fps_den), "-i", hevc]
    if audio:
        cmd += audio.input_args()
    cmd += ["-map", "0:v:0", *_x264(crf), *_tail(audio, seconds, out)]
    proc.run(cmd)
    return out


@dataclass
class Panel:
    """One video in a comparison: label, bitstream, and optionally the QP map
    whose ROI is drawn on it."""
    label: str
    hevc: str
    offsets: np.ndarray = None


def _decoder(hevc, pw, ph, scale):
    cmd = ["ffmpeg", "-v", "error", "-i", hevc]
    if scale:
        cmd += ["-vf", f"scale={pw}:{ph}:flags=bicubic"]
    cmd += ["-f", "rawvideo", "-pix_fmt", "yuv420p", "-"]
    return proc.popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


class FrameWriter:
    """Encode raw 4:2:0 frames (numpy Y, U, V planes) to an MP4 with x264,
    optionally with the clip's audio. Use as a context manager:

        with FrameWriter(out, w, h, 30, 1, crf=10) as wr:
            wr.write(y, u, v)
    """

    def __init__(self, out, width, height, fps_num, fps_den, audio=None, crf=10, seconds=None,
                 preset="medium"):
        self.out = out
        self.cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                    "-s", f"{width}x{height}", "-framerate", fps_arg(fps_num, fps_den), "-i", "-"]
        if audio:
            self.cmd += audio.input_args()
        self.cmd += ["-map", "0:v:0", *_x264(crf, preset), *_tail(audio, seconds, out)]
        self.frames = 0

    def __enter__(self):
        self._err = tempfile.TemporaryFile()
        self._p = proc.popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._err)
        return self

    def write(self, y, u, v):
        self._p.stdin.write(y.tobytes() + u.tobytes() + v.tobytes())
        self.frames += 1

    def __exit__(self, exc_type, exc, tb):
        try:
            self._p.stdin.close()
        except BrokenPipeError:
            pass
        code = self._p.wait()
        self._err.seek(0)
        msg = self._err.read().decode("utf-8", "replace")
        self._err.close()
        # ffmpeg failed: report its message, also when writing failed because it died
        if code != 0 and (exc_type is None or issubclass(exc_type, BrokenPipeError)):
            raise proc.CommandError(self.cmd, code, msg) from exc
        return False


def make_compare(panels, out, width, height, fps_num, fps_den, audio=None, roi_style="outline",
                 roi_color="red", roi_threshold=-0.5, labels=True, crf=10, max_width=2560, seconds=None):
    """Side-by-side (or grid) comparison video of several encodes of one clip.

    width, height: size of the encodes. Panels are decoded with ffmpeg,
    labelled and given their ROI drawing in YUV, stacked, and encoded with
    x264 (crf). Returns the number of frames written.
    """
    cols, rows, pw, ph = grid_layout(len(panels), width, height, max_width)
    gw, gh = cols * pw, rows * ph
    scale = (pw, ph) != (width, height)
    painters = [RoiPainter(p.offsets, width, height, pw, ph, roi_threshold, roi_style, roi_color)
                if p.offsets is not None and roi_style != "none" else None for p in panels]
    texts = [Label(p.label, pw, ph) if labels else None for p in panels]

    ysize, csize = pw * ph, (pw // 2) * (ph // 2)
    decoders = [_decoder(p.hevc, pw, ph, scale) for p in panels]
    try:
        with FrameWriter(out, gw, gh, fps_num, fps_den, audio, crf, seconds) as wr:
            while True:
                gy = np.full((gh, gw), 16, np.uint8)
                gu = np.full((gh // 2, gw // 2), 128, np.uint8)
                gv = np.full((gh // 2, gw // 2), 128, np.uint8)
                done = False
                for k, d in enumerate(decoders):
                    data = d.stdout.read(ysize + 2 * csize)
                    if len(data) < ysize + 2 * csize:
                        done = True
                        break
                    buf = np.frombuffer(data, np.uint8)
                    y = buf[:ysize].reshape(ph, pw).copy()
                    u = buf[ysize:ysize + csize].reshape(ph // 2, pw // 2).copy()
                    v = buf[ysize + csize:].reshape(ph // 2, pw // 2).copy()
                    if painters[k]:
                        painters[k].paint(y, u, v, wr.frames)
                    if texts[k]:
                        texts[k].paint(y, u, v)
                    r, c = divmod(k, cols)
                    gy[r * ph:(r + 1) * ph, c * pw:(c + 1) * pw] = y
                    gu[r * ph // 2:(r + 1) * ph // 2, c * pw // 2:(c + 1) * pw // 2] = u
                    gv[r * ph // 2:(r + 1) * ph // 2, c * pw // 2:(c + 1) * pw // 2] = v
                if done:
                    break
                wr.write(gy, gu, gv)
            frames = wr.frames
    finally:
        for d in decoders:
            d.stdout.close()
            d.wait()
    if frames == 0:
        raise RuntimeError(f"no frames decoded for {out}")
    return frames


def probe(path):
    """(width, height, frames, duration_s, has_audio) of a video file, via ffprobe."""
    out = proc.run(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
                    "stream=codec_type,width,height,nb_read_packets:format=duration",
                    "-of", "default=noprint_wrappers=1", path])
    vals, streams = {}, []
    for line in out.splitlines():
        k, _, v = line.partition("=")
        if k == "codec_type":
            streams.append(v)
        vals.setdefault(k, v)
    return (int(vals.get("width", 0)), int(vals.get("height", 0)), int(vals.get("nb_read_packets", 0)),
            float(vals.get("duration", 0) or 0), "audio" in streams)


def exists_nonempty(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0
