"""Speech to timed sentences: [{"start": s, "end": s, "text": "..."}], seconds from the start.

Either transcribed from the video with faster-whisper, or read from a transcript file: a list
of {"start", "end", "text"} segments, optionally with "words": [{"start", "end", "word"}],
or a JSON object with such a list under "transcript".
"""

import json
import subprocess
import sys


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
    return [
        {
            "start": float(s[0]["start"]),
            "end": float(s[-1]["end"]),
            "text": "".join(w["word"] for w in s).strip(),
        }
        for s in out
    ]


def load_transcript(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("transcript")
    if not isinstance(data, list):
        sys.exit(
            f"{path}: expected a list of segments, or an object with a 'transcript' list"
        )
    out = []
    for seg in data:
        if seg.get("words"):
            out += sentences_from_words(seg["words"])
        else:
            out.append(
                {
                    "start": float(seg["start"]),
                    "end": float(seg["end"]),
                    "text": str(seg["text"]).strip(),
                }
            )
    return [s for s in out if s["text"]]


def load_audio(video, rate=16000):
    """The video's audio as mono float32 samples at `rate` Hz, decoded with ffmpeg.
    (faster-whisper can open files itself through PyAV, but that fails on some setups;
    ffmpeg is needed for the frames anyway.)"""
    import numpy as np

    streams = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            video,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not streams:
        return np.zeros(0, np.float32)  # no audio track
    p = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            video,
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            str(rate),
            "-f",
            "f32le",
            "-",
        ],
        capture_output=True,
    )
    if p.returncode != 0:
        sys.exit(
            f"ffmpeg could not decode the audio of {video}:\n{p.stderr.decode(errors='replace')}"
        )
    return np.frombuffer(p.stdout, np.float32).copy()


def transcribe(video, model_name):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit(
            "faster-whisper is not installed: pip install faster-whisper, or give --transcript FILE"
        )
    audio = load_audio(video)
    if audio.size == 0:
        sys.exit(f"{video} has no audio track")
    print(
        f"transcribing {audio.size / 16000:.1f} s of audio with faster-whisper {model_name} ...",
        flush=True,
    )
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        audio, vad_filter=True, word_timestamps=True, condition_on_previous_text=False
    )
    words = [
        {"start": w.start, "end": w.end, "word": w.word}
        for seg in segments
        for w in (seg.words or [])
    ]
    return sentences_from_words(words)
