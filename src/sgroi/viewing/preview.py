"""Region preview: draw a clip's annotated objects on the clip, without
encoding, to check annotations (and a condition's timing) before a run.

Every object's box is drawn with its id. With a condition, active objects are
drawn in colour with their weight and inactive ones thin and grey, and the
area the condition's QP map boosts is lightly tinted, so what you see is what
the encoder will be given. The clip's audio is included, so the timing can be
checked against what is said.
"""

from ..io.annotations import active_frames, clip_times, load_annotations, pixel_boxes
from ..io.y4m import Y4M
from .draw import Label, RoiPainter, draw_rect
from .video import FrameWriter

PALETTE = ["yellow", "cyan", "magenta", "green", "red", "white"]
GREY = (128, 128, 128)


def make_preview(clip, out, plan=None, offsets=None, audio=None, crf=20, roi_threshold=-0.5):
    """clip: ClipInfo with annotations. plan: {object id: {"weight", "active"}} from a
    `regions` condition (None: just show every object). offsets: the condition's QP
    map [frames, rows, cols] to tint (None: no tint). Returns frames written."""
    ann = load_annotations(clip.annotations)
    boxes = {oid: pixel_boxes(tr, clip) for oid, tr in ann.objects.items()}
    colors = {oid: PALETTE[n % len(PALETTE)] for n, oid in enumerate(ann.objects)}
    active = {}
    if plan is not None:
        active = {oid: active_frames(clip, p["active"]) for oid, p in plan.items()}
    times = clip_times(clip)
    thick = max(2, round(clip.height / 270))
    tint = RoiPainter(offsets, clip.width, clip.height, clip.width, clip.height, roi_threshold,
                      "tint", "white") if offsets is not None else None
    labels = {}

    def label(text):
        if text not in labels:
            labels[text] = Label(text, clip.width, clip.height)
        return labels[text]

    y4m = Y4M(clip.path)
    with FrameWriter(out, clip.width, clip.height, y4m.fps_num, y4m.fps_den, audio, crf, y4m.seconds,
                     preset="veryfast") as wr:
        for i, (y, u, v) in enumerate(y4m.yuv_frames()):
            if tint:
                tint.paint(y, u, v, i)
            for oid, b in boxes.items():
                x0, y0, x1, y1 = b[min(i, len(b) - 1)]
                if plan is None:
                    color, t, text = colors[oid], thick, oid
                elif oid in plan and active[oid][i] and plan[oid]["weight"] > 0:
                    color, t, text = colors[oid], thick * 2, f"{oid}  {plan[oid]['weight']:g}"
                else:
                    color, t, text = GREY, max(1, thick // 2), f"{oid} (off)"
                draw_rect(y, u, v, x0, y0, x1, y1, color, t)
                lab = label(text)
                label_y = y0 - lab.h - 2 if y0 - lab.h - 2 >= 0 else y1 + 2
                lab.paint(y, u, v, at=(x0, label_y))
            label(f"t = {times[i]:.2f} s").paint(y, u, v)
            wr.write(y, u, v)
        return wr.frames
