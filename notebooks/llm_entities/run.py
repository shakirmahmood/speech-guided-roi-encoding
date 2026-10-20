"""Find what the speech of a video sends the viewer's eyes to, sentence by sentence, with
Qwen3.5-9B through Ollama, or a Gemini model (gemini-4-argon) through Google's API.

The model can't hear, so the audio goes in as a transcript (from faster-whisper, or a
transcript file you already have). It can see, so for every sentence a few frames from that
moment go in as images. Two steps (steps.py): first, once per video, a text-only call lists
the things in the video, each with an id; then, per sentence, one entry per thing the
viewer looks at because of the sentence, keyed by those ids, with why, how strongly
(attention) and a search text, plus what was left out and why. Entries with the same key
are merged. The prompts are printed once before the sentences are analysed.

Prompt text: config/prompt_goal.yaml. Answer fields: config/output_format.yaml. Defaults: config/settings.yaml.
Setup and notes: README.md in this folder.

Run:
    python3 run.py my_clip.mp4                                   # transcribes with faster-whisper
    python3 run.py my_clip.mp4 --transcript transcript.json
    python3 run.py my_clip.mp4 --frames 0                        # text only
    python3 run.py my_clip.mp4 --no-think                        # faster, worse on hard cases
    python3 run.py my_clip.mp4 --things runs/earlier.json        # reuse an earlier run's things list
    python3 run.py my_clip.mp4 --model gemini-4-argon            # Gemini (paid; prints the cost)
    python3 score.py answer_keys/gold_ratatouille.yaml runs/*.json
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time

import yaml

from answer_format import attention_order, load_format
from frames import check_ffmpeg, frame_times, sentence_frames, video_duration
from models import gemini, is_gemini
from models.reply import total_usage
from output import print_sentence, print_things, print_usage, save_run, show_prompt
from prompts import (
    format_sentence,
    format_transcript,
    load_prompt,
    sentence_prompt,
    things_prompt,
)
from steps import analyse_sentence, make_things, merge_by_key
from transcript import load_transcript, transcribe

SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config", "settings.yaml"
)


def parse_args(argv=None):
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("video")
    ap.add_argument("--transcript", help="timed transcript JSON (skips transcription)")
    ap.add_argument(
        "--whisper",
        default=d["whisper"],
        help=f"faster-whisper model (default {d['whisper']})",
    )
    ap.add_argument(
        "--frames",
        type=int,
        default=d["frames"],
        help=f"frames per sentence (default {d['frames']}; 0 = text only)",
    )
    ap.add_argument(
        "--width",
        type=int,
        default=d["width"],
        help=f"frame width in pixels (default {d['width']})",
    )
    ap.add_argument(
        "--think",
        action=argparse.BooleanOptionalAction,
        default=d["think"],
        help=f"let the model reason before it answers in step 2 (default {d['think']})",
    )
    ap.add_argument(
        "--things",
        help="reuse the things list saved in an earlier run's JSON (same transcript), "
        "so two runs differ only in step 2",
    )
    ap.add_argument(
        "--model",
        default=d["model"],
        help=f"Ollama model, or a Gemini model such as gemini-4-argon (default {d['model']})",
    )
    ap.add_argument(
        "--ctx",
        type=int,
        default=d["ctx"],
        help=f"context size in tokens (default {d['ctx']})",
    )
    ap.add_argument(
        "--out",
        help="where to save the results (default runs/<video>_<date>_<time>.json)",
    )
    ap.add_argument(
        "--keep-frames",
        help="save the frames in this folder (to look at what the model saw)",
    )
    return ap.parse_args(argv)


def default_out(video):
    name = os.path.splitext(os.path.basename(video))[0]
    return os.path.join("runs", f"{name}_{time.strftime('%Y-%m-%d_%H%M%S')}.json")


def get_things(a, fmt, text, transcript):
    """Step 1, or the things list of an earlier run; and what step 1 used (Gemini only)."""
    if a.things:
        with open(a.things, encoding="utf-8") as f:
            things = json.load(f)["things"]
        print_things(things, 0.0)
        return things, {}
    prompt = things_prompt(fmt, text, transcript)
    show_prompt(prompt)
    t0 = time.time()
    things, usage = make_things(prompt, a.model, a.ctx)
    print_things(things, time.time() - t0)
    return things, usage


def analyse(a, prompt, order, n, sent, duration, frame_dir):
    """Step 2 for one sentence -> its result record."""
    times, images = sentence_frames(
        a.video, n, sent, a.frames, a.width, duration, frame_dir
    )
    t0 = time.time()
    reply = analyse_sentence(prompt, n, sent, times, images, a.model, a.ctx, a.think)
    took = time.time() - t0
    look_at = [t.model_dump() for t in reply.answer.look_at] if reply.answer else []
    left_out = (
        [item.model_dump() for item in reply.answer.left_out] if reply.answer else []
    )
    return {
        "n": n,
        **sent,
        "frame_times": times,
        "seconds": round(took, 2),
        "failed": reply.answer is None,
        "thinking_words": len(reply.thinking.split()),
        "prompt_tokens": reply.prompt_tokens,
        "look_at": look_at,
        "look_at_merged": merge_by_key(look_at, order),
        "left_out": left_out,
        "usage": reply.usage,
    }


def main(argv=None):
    a = parse_args(argv)
    check_ffmpeg()
    duration = video_duration(a.video)
    sentences = (
        load_transcript(a.transcript)
        if a.transcript
        else transcribe(a.video, a.whisper)
    )
    if not sentences:
        sys.exit("no speech found")
    out = a.out or default_out(a.video)

    fmt, text = load_format(), load_prompt()
    transcript = format_transcript(sentences)
    things, things_usage = get_things(a, fmt, text, transcript)
    prompt = sentence_prompt(fmt, text, transcript, things)
    order = attention_order(fmt)

    frame_dir = a.keep_frames or tempfile.mkdtemp(prefix="qwen_frames_")
    os.makedirs(frame_dir, exist_ok=True)
    first = sentences[0]
    first_times = (
        frame_times(first["start"], first["end"], a.frames, duration)
        if a.frames > 0
        else []
    )
    show_prompt(
        prompt,
        format_sentence(1, first, first_times)
        + ("\n[+ the frame images]" if first_times else ""),
    )
    results = []
    try:
        for n, sent in enumerate(sentences, 1):
            results.append(analyse(a, prompt, order, n, sent, duration, frame_dir))
            print_sentence(results[-1])
    finally:
        if not a.keep_frames:
            shutil.rmtree(frame_dir, ignore_errors=True)

    usage = total_usage([things_usage] + [r["usage"] for r in results])
    print_usage(usage)
    save_run(
        out,
        {
            "video": os.path.basename(a.video),
            "model": a.model,
            "prompt": prompt.name,
            "prompt_version": prompt.version,
            "format_version": fmt["version"],
            "think": a.think,
            "thinking_level": (
                gemini.thinking_level(a.think) if is_gemini(a.model) else None
            ),
            "frames_per_sentence": a.frames,
            "frame_width": a.width,
            "ctx": a.ctx,
            "things": things,
            "usage": usage,
            "sentences": results,
        },
    )


if __name__ == "__main__":
    main()
