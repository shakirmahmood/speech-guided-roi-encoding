"""Give a video to Qwen3.5-9B: the speech as timed text, plus a few frames
taken while each sentence is spoken.

The model can't hear, so the audio goes in as a transcript (from faster-whisper,
or a transcript file you already have). It can see, so for every sentence a few
frames from that moment go in as images. For each mention it answers twice:
  visible_now  from the words only (as in try_qwen.py)
  in_frames    from the pictures: can it actually see the thing?
which is the text-only vs text+frames comparison, one run at a time.

Setup and notes: README.md in this folder.

Run:
    python3 try_qwen_video.py my_clip.mp4                         # transcribes with faster-whisper
    python3 try_qwen_video.py my_clip.mp4 --transcript transcript.json
    python3 try_qwen_video.py my_clip.mp4 --transcript other_results/rankings.json
    python3 try_qwen_video.py my_clip.mp4 --frames 1 --out results/my_clip.json

A transcript file is a list of {"start": s, "end": s, "text": "..."} (seconds from
the start of the video), optionally with "words": [{"start", "end", "word"}], or a
JSON object with such a list under "transcript".
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Literal

from ollama import chat
from pydantic import BaseModel

from try_qwen import MODEL, RULES, SHOT_IN, SHOT_OUT, Mention

PROMPT_VERSION = "video-v1"


# ---- what we want back ------------------------------------------------------------

class VideoMention(Mention):
    in_frames: Literal["yes", "no", "unsure"]


class VideoResult(BaseModel):
    mentions: list[VideoMention]


VIDEO_RULES = RULES.replace(
    "You only see the words, never the picture.",
    "You get one sentence of the narration, the sentences before it for context, and a few frames\n"
    "taken from the video while that sentence was spoken.",
).replace(
    "List every noun phrase or pronoun",
    "List every noun phrase or pronoun IN THE SENTENCE (not in the earlier context)",
).replace(
    "Answer only with the JSON.",
    """visible_now: decide it from the WORDS only, exactly as described above, even if a picture says otherwise.
in_frames: decide it from the PICTURES only: "yes" if you can see the thing in at least one frame,
  "no" if the frames clearly don't show it, "unsure" if you can't tell or no frames were given.
  For "this little guy" or "it", judge what the words most likely point at.

Answer only with the JSON.""",
)

# The worked example from try_qwen.py, without pictures (so in_frames is "unsure").
SHOT_VIDEO_IN = f"Sentence: {SHOT_IN}\n(No frames for this example.)"
SHOT_VIDEO_OUT = VideoResult(mentions=[
    VideoMention(**m, in_frames="unsure") for m in json.loads(SHOT_OUT)["mentions"]
]).model_dump_json()


# ---- transcript --------------------------------------------------------------------

def sentences_from_words(words):
    """Split timed words into sentences at . ! ? -> [{start, end, text}]."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w["word"].strip().endswith((".", "!", "?")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"start": float(s[0]["start"]), "end": float(s[-1]["end"]),
             "text": "".join(w["word"] for w in s).strip()} for s in out]


def load_transcript(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("transcript")
    if not isinstance(data, list):
        sys.exit(f"{path}: expected a list of segments, or an object with a 'transcript' list")
    out = []
    for seg in data:
        if seg.get("words"):
            out += sentences_from_words(seg["words"])
        else:
            out.append({"start": float(seg["start"]), "end": float(seg["end"]), "text": str(seg["text"]).strip()})
    return [s for s in out if s["text"]]


def load_audio(video, rate=16000):
    """The video's audio as mono float32 samples at `rate` Hz, decoded with ffmpeg.
    (faster-whisper can open files itself through PyAV, but that fails on some setups;
    ffmpeg is needed for the frames anyway.)"""
    import numpy as np
    streams = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                              "stream=index", "-of", "csv=p=0", video],
                             capture_output=True, text=True, check=True).stdout.strip()
    if not streams:
        return np.zeros(0, np.float32)                  # no audio track
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
                        "-f", "f32le", "-"], capture_output=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg could not decode the audio of {video}:\n{p.stderr.decode(errors='replace')}")
    return np.frombuffer(p.stdout, np.float32).copy()


def transcribe(video, model_name):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed: pip install faster-whisper, or give --transcript FILE")
    audio = load_audio(video)
    if audio.size == 0:
        sys.exit(f"{video} has no audio track")
    print(f"transcribing {audio.size / 16000:.1f} s of audio with faster-whisper {model_name} ...", flush=True)
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, vad_filter=True, word_timestamps=True,
                                   condition_on_previous_text=False)
    words = [{"start": w.start, "end": w.end, "word": w.word} for seg in segments for w in (seg.words or [])]
    return sentences_from_words(words)


# ---- frames ------------------------------------------------------------------------

def video_duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def frame_times(start, end, n, duration):
    """n times spread evenly over [start, end] (the middle of n equal parts), inside the video."""
    end = max(end, start)
    last = max(0.0, duration - 0.05)
    return [round(min(last, max(0.0, start + (i + 0.5) * (end - start) / n)), 3) for i in range(n)]


def grab_frame(video, t, path, width):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                    "-vf", f"scale={width}:-2", "-q:v", "3", path], check=True)
    return path


# ---- the call ------------------------------------------------------------------------

def analyse_sentence(sentence, earlier, images, times, model, ctx):
    lines = []
    if earlier:
        lines.append("Earlier narration (context only):")
        lines += [f"  [{s['start']:.2f}-{s['end']:.2f} s] {s['text']}" for s in earlier]
    lines.append(f"Sentence [{sentence['start']:.2f}-{sentence['end']:.2f} s]: {sentence['text']}")
    lines.append("Frames, in order, at: " + ", ".join(f"{t:.2f} s" for t in times) if images
                 else "(No frames.)")
    response = chat(
        model=model,
        messages=[{"role": "system", "content": VIDEO_RULES},
                  {"role": "user", "content": SHOT_VIDEO_IN},
                  {"role": "assistant", "content": SHOT_VIDEO_OUT},
                  {"role": "user", "content": "\n".join(lines), "images": images}],
        format=VideoResult.model_json_schema(),
        think=False,
        options={"temperature": 0.0, "seed": 1, "num_ctx": ctx},
    )
    return VideoResult.model_validate_json(response.message.content)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--transcript", help="timed transcript JSON (skips transcription)")
    ap.add_argument("--whisper", default="small.en", help="faster-whisper model if transcribing (default small.en)")
    ap.add_argument("--frames", type=int, default=3, help="frames per sentence (default 3; 0 = text only)")
    ap.add_argument("--width", type=int, default=768, help="frame width in pixels (default 768; smaller is faster)")
    ap.add_argument("--context", type=int, default=2, help="earlier sentences given as context (default 2)")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--ctx", type=int, default=8192, help="context size in tokens (images need room; default 8192)")
    ap.add_argument("--out", help="also save the results as JSON here")
    ap.add_argument("--keep-frames", help="save the frames in this folder (to look at what the model saw)")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found: sudo apt install ffmpeg")
    duration = video_duration(a.video)
    sentences = load_transcript(a.transcript) if a.transcript else transcribe(a.video, a.whisper)
    if not sentences:
        sys.exit("no speech found")

    frame_dir = a.keep_frames or tempfile.mkdtemp(prefix="qwen_frames_")
    os.makedirs(frame_dir, exist_ok=True)
    results = []
    try:
        for n, sent in enumerate(sentences):
            times = frame_times(sent["start"], sent["end"], a.frames, duration) if a.frames > 0 else []
            images = [grab_frame(a.video, t, os.path.join(frame_dir, f"s{n:03d}_{t:07.3f}s.jpg"), a.width)
                      for t in times]
            t0 = time.time()
            res = analyse_sentence(sent, sentences[max(0, n - a.context):n], images, times, a.model, a.ctx)
            took = time.time() - t0
            print(f"\n[{sent['start']:.2f}-{sent['end']:.2f} s] {sent['text']}   ({took:.1f} s)")
            for m in res.mentions:
                back = f" -> {m.refers_back_to}" if m.refers_back_to else ""
                agree = ("   <- words and pictures disagree"
                         if {m.visible_now, m.in_frames} == {"yes", "no"} else "")
                print(f"  {m.phrase!r:22} words={m.visible_now:6} ({m.cue:12}) pictures={m.in_frames:6} "
                      f"search={m.search_for!r}{back}{agree}")
            results.append({**sent, "frame_times": times, "seconds": round(took, 2),
                            "mentions": [m.model_dump() for m in res.mentions]})
    finally:
        if not a.keep_frames:
            shutil.rmtree(frame_dir, ignore_errors=True)

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"video": os.path.basename(a.video), "model": a.model, "prompt_version": PROMPT_VERSION,
                       "frames_per_sentence": a.frames, "frame_width": a.width, "sentences": results}, f, indent=2)
        print(f"\nsaved {a.out}")


if __name__ == "__main__":
    main()
