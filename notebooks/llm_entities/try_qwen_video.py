"""Give a video to Qwen3.5-9B: the speech as timed text, plus a few frames
taken while each sentence is spoken.

The model can't hear, so the audio goes in as a transcript (from faster-whisper,
or a transcript file you already have). It can see, so for every sentence a few
frames from that moment go in as images. Each call gets the whole numbered
transcript for context and analyses one sentence of it. For each mention it
gives the first mention of the same thing (e.g. "1: the old truck"), so all mentions
of one object share one key across calls, and it answers twice:
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
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Literal

from ollama import chat
from pydantic import BaseModel

from try_qwen import MODEL, RULES, Cue

PROMPT_VERSION = "video-v2"


# ---- what we want back ------------------------------------------------------------

class VideoMention(BaseModel):
    # The model fills these in this order, so the evidence (cue) comes before the decision.
    phrase: str
    first_mention: str          # "N: phrase" of the first mention of the same thing in the transcript
    cue: Cue
    visible_now: Literal["yes", "no", "unsure"]
    role: Literal["subject", "object", "other"]
    attention_cue: bool
    evaluated: bool
    search_for: str
    in_frames: Literal["yes", "no", "unsure"]


class VideoResult(BaseModel):
    mentions: list[VideoMention]


def _replace_once(text, old, new):
    """str.replace that fails loudly if `old` is missing (e.g. RULES was reworded)."""
    if text.count(old) != 1:
        raise RuntimeError(f"VIDEO_RULES: expected to find this once in RULES (try_qwen.py): {old[:60]!r}")
    return text.replace(old, new)


VIDEO_RULES = RULES
for _old, _new in [
    ("You only see the words, never the picture.",
     "You get the full numbered transcript of the video, then one sentence of it to analyse,\n"
     "with a few frames taken from the video while that sentence was spoken."),
    ("List every noun phrase or pronoun",
     "List every noun phrase or pronoun IN THE SENTENCE TO ANALYSE (never from other sentences)"),
    ('refers_back_to: for a pronoun (it, she, he, they, him, them), the earlier phrase it means; otherwise "".',
     'first_mention: the FIRST mention of the same thing anywhere in the transcript, written as\n'
     '  "<sentence number>: <phrase>", e.g. "1: the old truck". Pronouns, names ("we call it Rusty")\n'
     '  and other descriptions of that same thing all get that same first mention. If this is the\n'
     '  first mention, write its own sentence number and phrase.'),
    ("Answer only with the JSON.",
     """visible_now: decide it from the WORDS only, exactly as described above, even if a picture says otherwise.
in_frames: decide it from the PICTURES only: "yes" if you can see the thing in at least one frame,
  "no" if the frames clearly don't show it, "unsure" if you can't tell or no frames were given.
  For "this little guy" or "it", judge what the words most likely point at.

Answer only with the JSON."""),
]:
    VIDEO_RULES = _replace_once(VIDEO_RULES, _old, _new)


def format_transcript(sentences):
    """Numbered transcript, the same text in every call for one video."""
    return "Full transcript of the video (for context):\n" + "\n".join(
        f"  {n} [{s['start']:.2f}-{s['end']:.2f} s] {s['text']}" for n, s in enumerate(sentences, 1))


def format_sentence(n, sentence, times):
    """The part that changes from call to call: which sentence, and its frames."""
    frames = ("Frames of sentence {}, in order, at: {}".format(n, ", ".join(f"{t:.2f} s" for t in times))
              if times else "(No frames for this sentence.)")
    return (f"Sentence to analyse: {n} [{sentence['start']:.2f}-{sentence['end']:.2f} s] {sentence['text']}\n"
            + frames)


# A worked example in the same format as the real calls (no pictures, so in_frames is "unsure").
# It shows: only the marked sentence is listed (the towel in sentence 3 is not), a generic
# mention, a name ("Luna") and a pronoun sharing one first mention, an opinion, a plain mention.
SHOT_SENTENCES = [
    {"start": 0.0, "end": 1.1, "text": "This is Luna."},
    {"start": 1.3, "end": 4.2, "text": "Cats usually hate water, but look at my cat here, she's so cute on the mat!"},
    {"start": 4.4, "end": 5.8, "text": "The towel on the chair is for later."},
]
SHOT_TRANSCRIPT = format_transcript(SHOT_SENTENCES)
SHOT_IN = format_sentence(2, SHOT_SENTENCES[1], [])
SHOT_OUT = VideoResult(mentions=[
    VideoMention(phrase="Cats", first_mention="2: Cats", cue="generic", visible_now="no", role="subject",
                 attention_cue=False, evaluated=False, search_for="cat", in_frames="unsure"),
    VideoMention(phrase="water", first_mention="2: water", cue="generic", visible_now="no", role="object",
                 attention_cue=False, evaluated=False, search_for="water", in_frames="unsure"),
    VideoMention(phrase="my cat", first_mention="1: Luna", cue="presentative", visible_now="yes", role="object",
                 attention_cue=True, evaluated=False, search_for="cat", in_frames="unsure"),
    VideoMention(phrase="she", first_mention="1: Luna", cue="presentative", visible_now="yes", role="subject",
                 attention_cue=False, evaluated=True, search_for="cat", in_frames="unsure"),
    VideoMention(phrase="the mat", first_mention="2: the mat", cue="none", visible_now="unsure", role="other",
                 attention_cue=False, evaluated=False, search_for="mat", in_frames="unsure"),
]).model_dump_json()


def phrase_in_sentence(phrase, sentence):
    """Does the phrase occur in the sentence (ignoring case and punctuation)?"""
    norm = lambda t: " " + " ".join(re.sub(r"[^\w\s]", " ", t.lower()).split()) + " "   # "she's" -> "she s"
    return norm(phrase) in norm(sentence)


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

def analyse_sentence(transcript, n, sentence, images, times, model, ctx):
    # Order matters for speed: everything up to and including the video's transcript is
    # identical in every call for one video, so Ollama can reuse its work on that part;
    # only the last message (the sentence and its frames) changes.
    response = chat(
        model=model,
        messages=[{"role": "system", "content": VIDEO_RULES},
                  {"role": "user", "content": SHOT_TRANSCRIPT},             # worked example ...
                  {"role": "user", "content": SHOT_IN},
                  {"role": "assistant", "content": SHOT_OUT},               # ... and its answer
                  {"role": "user", "content": transcript},                  # this video, same every call
                  {"role": "user", "content": format_sentence(n, sentence, times), "images": images}],
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

    transcript = format_transcript(sentences)
    frame_dir = a.keep_frames or tempfile.mkdtemp(prefix="qwen_frames_")
    os.makedirs(frame_dir, exist_ok=True)
    results = []
    try:
        for n, sent in enumerate(sentences, 1):
            times = frame_times(sent["start"], sent["end"], a.frames, duration) if a.frames > 0 else []
            images = [grab_frame(a.video, t, os.path.join(frame_dir, f"s{n:03d}_{t:07.3f}s.jpg"), a.width)
                      for t in times]
            t0 = time.time()
            res = analyse_sentence(transcript, n, sent, images, times, a.model, a.ctx)
            took = time.time() - t0
            print(f"\n{n} [{sent['start']:.2f}-{sent['end']:.2f} s] {sent['text']}   ({took:.1f} s)")
            mentions = []
            for m in res.mentions:
                in_sentence = phrase_in_sentence(m.phrase, sent["text"])
                notes = ("   <- words and pictures disagree" if {m.visible_now, m.in_frames} == {"yes", "no"} else "")
                if not in_sentence:
                    notes += "   <- NOT in this sentence"
                print(f"  {m.phrase!r:22} [{m.first_mention}] words={m.visible_now:6} ({m.cue:12}) "
                      f"pictures={m.in_frames:6} search={m.search_for!r}{notes}")
                mentions.append({**m.model_dump(), "phrase_in_sentence": in_sentence})
            results.append({"n": n, **sent, "frame_times": times, "seconds": round(took, 2),
                            "mentions": mentions})
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
