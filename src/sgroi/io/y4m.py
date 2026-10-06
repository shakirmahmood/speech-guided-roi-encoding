"""Reading 8-bit 4:2:0 Y4M files (the encoder's input format)."""

import os

import numpy as np


class Y4M:
    """Header information and frame access for an 8-bit 4:2:0 Y4M file."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            header = f.readline().decode("ascii", "replace")
            self.first_frame = f.tell()
            f.seek(0, os.SEEK_END)
            size = f.tell()
        if not header.startswith("YUV4MPEG2 "):
            raise ValueError(f"{path} is not a Y4M file")
        fields = {t[0]: t[1:] for t in header.split()[1:]}
        self.width, self.height = int(fields["W"]), int(fields["H"])
        num, den = fields.get("F", "30:1").split(":")
        self.fps_num, self.fps_den = int(num), int(den)
        chroma = fields.get("C", "420")
        if chroma not in ("420", "420jpeg", "420mpeg2", "420paldv"):
            raise ValueError(f"{path}: only 8-bit 4:2:0 Y4M is supported (got C{chroma})")
        self.chroma_w, self.chroma_h = (self.width + 1) // 2, (self.height + 1) // 2
        self.frame_bytes = self.width * self.height + 2 * self.chroma_w * self.chroma_h
        # assumes plain "FRAME\n" frame headers, which is what ffmpeg writes
        self.frames = (size - self.first_frame) // (len(b"FRAME\n") + self.frame_bytes)

    @property
    def fps(self):
        return self.fps_num / self.fps_den

    @property
    def seconds(self):
        return self.frames / self.fps

    def luma_frames(self):
        """Yield the luma plane of each frame as a uint8 [H, W] array."""
        with open(self.path, "rb") as f:
            f.seek(self.first_frame)
            while True:
                line = f.readline()
                if not line:
                    return
                data = f.read(self.frame_bytes)
                if len(data) < self.frame_bytes:
                    return
                yield np.frombuffer(data, np.uint8, self.width * self.height).reshape(self.height, self.width)
