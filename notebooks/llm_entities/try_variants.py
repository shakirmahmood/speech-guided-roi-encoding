"""Run prompt variants for the "what does the speech send the eyes to" step on one clip,
and save each run in one common format that score.py can score against a gold file.

Written for the prompt review in this folder; untested against a real model (the cloud
session that wrote it could not download one). It was run end to end with a stub in place
of ollama.chat, so the plumbing works; the prompts themselves are hypotheses to test.

Put this file next to try_qwen_video.py (notebooks/llm_entities/) and run it there; it
reuses that script's transcript, frame, things-list and goal-v4 code unchanged.

Variants (--variant):
  current   goal-v4 / look_at-4 exactly as try_qwen_video.py --prompt goal sends it (baseline)
  generic   a short goal description, no rule lists, no examples; one analysis line, then
            targets with the words that refer to each
  labels    the model labels each mention with standard linguistic categories (specific vs
            generic reference, realis vs irrealis, time, place, deixis, perception imperative,
            sentence topic, implied participant); this script turns the labels into
            here-now and a strength with a fixed rule (see labels_to_targets)
Options that apply to every variant:
  --think        let the model reason first (Qwen's recommended sampling for thinking is used)
  --frames 0     text only (the LLM step then works from language alone)
  --samples K    K sampled runs per sentence, combined by majority vote (needs --think or
                 sampling; with temperature 0 every sample is the same)

Run:
    python3 try_variants.py clip.mp4 --variant current --out runs/current.json
    python3 try_variants.py clip.mp4 --variant generic --think --out runs/generic_think.json
    python3 try_variants.py clip.mp4 --variant labels --frames 0 --out runs/labels_text.json
    python3 score.py gold_ratatouille.yaml runs/*.json
"""

import argparse
import collections
import json
import os
import re
import shutil
import sys
import tempfile
import time
from typing import Literal

from ollama import chat
from pydantic import ValidationError, create_model

import try_qwen_video as v

STRENGTHS = ["primary", "secondary", "minor"]


# ---- variant: generic ------------------------------------------------------------------

GENERIC_SYSTEM = """You help a video encoder spend its bits where viewers look. People watching a
narrated video look where the speech sends them: within a fraction of a second of hearing an
expression, their eyes go to the thing it refers to, if that thing is in the scene.

You get the transcript of the whole video, the list of things it mentions (each with an id),
then one sentence that is being spoken now, with frames from that moment.

Say which things in the scene the speech of THIS sentence sends the viewer's eyes to, and how
strongly. Work out what each expression really refers to, using the whole transcript and the
frames. A thing that is talked about but is not actually in the scene now cannot be looked at,
so it is not a target.

First write a short analysis (two or three sentences). Then list the targets:
  words:      the words of this sentence that refer to it ("" if it is only implied)
  refers_to:  its id from the list, or new
  search_for: a short visual description to find it in the frames
  strength:   primary - what the sentence mainly sends the eyes to (usually one thing);
              secondary - also referred to;
              minor - only implied, or in the background of what is said
An empty list is right when the sentence sends the eyes nowhere in particular.

Answer only with the JSON."""


def generic_model(ids):
    target = create_model("Target", words=(str, ...), refers_to=(Literal[tuple(ids) + (v.NEW_KEY,)], ...),
                          search_for=(str, ...), strength=(Literal[tuple(STRENGTHS)], ...))
    return create_model("GenericResult", analysis=(str, ...), targets=(list[target], ...))


def generic_to_targets(res):
    return [{"key": t.refers_to, "words": t.words, "search_for": t.search_for, "strength": t.strength}
            for t in res.targets]


# ---- variant: labels -------------------------------------------------------------------

LABELS_SYSTEM = """You annotate the referring expressions in a narrated video, one sentence at a
time. You get the transcript of the whole video, the list of things it mentions (each with an
id), then one sentence that is being spoken now, with frames from that moment.

First write a short analysis (two or three sentences). Then give one entry per referring
expression in THIS sentence that refers, or might refer, to something concrete (an object,
person, animal, food, plant, or a part of one), including pronouns and demonstratives. Also
add one entry, with words "", for each concrete participant the sentence only implies
(slicing implies the blade and the thing being cut).

  words:        the exact words in this sentence ("" for an implied participant)
  refers_to:    the id of its referent from the list, or new (use the whole transcript to
                resolve pronouns, demonstratives and forward references)
  reference:    specific (a particular thing), generic (a kind of thing in general), or
                non_referential (idiom, figure of speech, abstract)
  reality:      actual, or irrealis (hypothetical, conditional, wished, negated or absent)
  time:         now, habitual (true whenever this happens, including now), past, or future
  place:        here (in the scene being filmed), or elsewhere
  deictic:      true if pointed at or presented in the scene ("this", "these", "here's",
                "this is", "as you can see")
  look_cue:     true if the speaker tells the viewer to look at it ("look at", "watch",
                "check out", "see")
  topic:        true if this sentence is mainly about it (its topic, not just its grammatical
                subject; "I"/"we" doing something are rarely the topic)
  implied:      true for an implied participant
  search_for:   a short visual description to find it in the frames

Answer only with the JSON."""


def labels_model(ids):
    mention = create_model(
        "Mention", words=(str, ...), refers_to=(Literal[tuple(ids) + (v.NEW_KEY,)], ...),
        reference=(Literal["specific", "generic", "non_referential"], ...),
        reality=(Literal["actual", "irrealis"], ...),
        time=(Literal["now", "habitual", "past", "future"], ...),
        place=(Literal["here", "elsewhere"], ...),
        deictic=(bool, ...), look_cue=(bool, ...), topic=(bool, ...), implied=(bool, ...),
        search_for=(str, ...))
    return create_model("LabelsResult", analysis=(str, ...), mentions=(list[mention], ...))


def labels_to_targets(res):
    """The fixed rule: a mention can be looked at only if it is a specific, actual thing,
    here, now (or habitually); strength from the salience labels."""
    out = []
    for m in res.mentions:
        here_now = (m.reference == "specific" and m.reality == "actual"
                    and m.time in ("now", "habitual") and m.place == "here")
        if not here_now:
            continue
        strength = ("primary" if (m.look_cue or m.deictic or m.topic) and not m.implied
                    else "minor" if m.implied else "secondary")
        out.append({"key": m.refers_to, "words": m.words, "search_for": m.search_for, "strength": strength})
    return out


# ---- variant: current (goal-v4) --------------------------------------------------------

ATTENTION_TO_STRENGTH = {"high": "primary", "medium": "secondary", "low": "minor"}


def current_to_targets(res):
    return [{"key": t.key, "words": "", "search_for": t.search_for,
             "strength": ATTENTION_TO_STRENGTH[t.attention], "on_screen": t.on_screen}
            for t in res.look_at]


# ---- shared ----------------------------------------------------------------------------

def make_prompt(variant, fmt, things):
    ids = [t["id"] for t in things]
    if variant == "current":
        p = v.goal_prompt(fmt, things)
        return p["fixed"], p["result"], current_to_targets
    system, model, convert = {"generic": (GENERIC_SYSTEM, generic_model(ids), generic_to_targets),
                              "labels": (LABELS_SYSTEM, labels_model(ids), labels_to_targets)}[variant]

    def fixed(transcript):     # same order as try_qwen_video.py, so Ollama can reuse the prefix
        return [("system", {"role": "system", "content": system}),
                ("transcript", {"role": "user", "content": transcript}),
                ("things", {"role": "user", "content": v.format_things(things)})]
    return fixed, model, convert


def options(think, ctx, sample_index, retry=0):
    if think:     # Qwen's recommended sampling for thinking mode
        return {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "seed": 1 + sample_index + 100 * retry,
                "num_ctx": ctx}
    if retry:     # greedy decoding looped; retry with Qwen's recommended non-thinking sampling
        return {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "presence_penalty": 1.5,
                "seed": 1 + sample_index + 100 * retry, "num_ctx": ctx, "num_predict": 4096}
    return {"temperature": 0.0, "seed": 1 + sample_index, "num_ctx": ctx, "num_predict": 4096}


def call(fixed, result_model, transcript, n, sentence, images, times, model, ctx, think, sample_index):
    messages = [m for _, m in fixed(transcript)] + [
        {"role": "user", "content": v.format_sentence(n, sentence, times), "images": images}]
    for retry in range(3):
        r = chat(model=model, messages=messages, format=result_model.model_json_schema(), think=think,
                 options=options(think, ctx, sample_index, retry))
        used = getattr(r, "prompt_eval_count", None) or 0
        if used and used >= ctx - 64:        # Ollama silently drops the start of an over-long prompt
            print(f"  WARNING: prompt used {used} of {ctx} context tokens; raise --ctx", file=sys.stderr)
        thinking = getattr(r.message, "thinking", None) or ""
        try:
            return result_model.model_validate_json(r.message.content), thinking, used
        except ValidationError as e:         # usually a repetition loop cut off mid-JSON
            print(f"  WARNING: sentence {n}: unusable answer ({len(r.message.content)} chars; "
                  f"{str(e).splitlines()[0]}); retrying", file=sys.stderr)
    print(f"  WARNING: sentence {n}: no usable answer after 3 tries; recorded as empty", file=sys.stderr)
    return None, "", used


def vote(samples):
    """Majority vote over K samples: keep a key if more than half of the samples have it,
    with its most common strength (ties go to the stronger one)."""
    k = len(samples)
    by_key = collections.defaultdict(list)
    for targets in samples:
        for t in {t["key"] if t["key"] != v.NEW_KEY else "new:" + t["search_for"]: t for t in targets}.values():
            by_key[t["key"] if t["key"] != v.NEW_KEY else "new:" + t["search_for"]].append(t)
    out = []
    for key, ts in by_key.items():
        if len(ts) * 2 <= k:
            continue
        counts = collections.Counter(t["strength"] for t in ts)
        best = max(counts.values())
        strength = next(s for s in STRENGTHS if counts[s] == best)
        out.append({**next(t for t in ts if t["strength"] == strength), "votes": f"{len(ts)}/{k}"})
    return out


def merge_same_key(targets):
    """One entry per key, with the strongest strength (new entries stay separate)."""
    merged = {}
    for t in targets:
        k = t["key"] if t["key"] != v.NEW_KEY else f"new#{len(merged)}"
        if k not in merged or STRENGTHS.index(t["strength"]) < STRENGTHS.index(merged[k]["strength"]):
            merged[k] = t
    return list(merged.values())


POINTING_WORDS = {"this", "that", "these", "those", "they", "them", "here", "there"}


def key_slip(target, things):
    """The id of another thing whose name occurs in this entry's words, e.g. words='yellow squash' with
    key 'guard'; None if the words fit the key or name no thing."""
    words = " " + " ".join(re.sub(r"[^\w\s]", " ", target["words"].lower()).split()) + " "
    if words.strip() == "":
        return None
    def names(t):
        return [t["id"].replace("_", " ")] + [p for p in t["id"].split("_") if len(p) > 3] + \
               [a.lower() for a in t["also_called"] if len(a) > 3 and a.lower() not in POINTING_WORDS]
    if any(f" {n} " in words or f" {n}s " in words for t in things if t["id"] == target["key"] for n in names(t)):
        return None
    for t in things:
        if t["id"] != target["key"] and any(f" {n} " in words or f" {n}s " in words for n in names(t)):
            return t["id"]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--variant", choices=["current", "generic", "labels"], required=True)
    ap.add_argument("--transcript", help="timed transcript JSON (skips transcription)")
    ap.add_argument("--whisper", default="small.en")
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--width", type=int, default=768)
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--things", help="reuse a things list saved by an earlier run (same transcript), "
                                     "so variants differ only in step 2")
    ap.add_argument("--model", default=v.MODEL)
    ap.add_argument("--ctx", type=int, default=16384)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    duration = v.video_duration(a.video)
    sentences = v.load_transcript(a.transcript) if a.transcript else v.transcribe(a.video, a.whisper)
    transcript = v.format_transcript(sentences)
    fmt = v.load_format()
    if a.things:
        with open(a.things, encoding="utf-8") as f:
            things = json.load(f)["things"]
    else:
        things = v.make_things(fmt, transcript, a.model, a.ctx)
    fixed, result_model, convert = make_prompt(a.variant, fmt, things)

    frame_dir = tempfile.mkdtemp(prefix="variant_frames_")
    results = []
    try:
        for n, sent in enumerate(sentences, 1):
            times = v.frame_times(sent["start"], sent["end"], a.frames, duration) if a.frames > 0 else []
            images = [v.grab_frame(a.video, t, os.path.join(frame_dir, f"s{n:03d}_{i}.jpg"), a.width)
                      for i, t in enumerate(times)]
            t0 = time.time()
            samples, raw = [], []
            for k in range(a.samples):
                res, thinking, used = call(fixed, result_model, transcript, n, sent, images, times,
                                           a.model, a.ctx, a.think, k)
                samples.append(merge_same_key(convert(res)) if res is not None else [])
                raw.append({"answer": res.model_dump() if res is not None else None, "failed": res is None,
                            "thinking_words": len(thinking.split()), "prompt_tokens": used})
            targets = vote(samples) if a.samples > 1 else samples[0]
            print(f"\n{n} {sent['text']}   ({time.time() - t0:.1f} s)")
            for t in targets:
                slip = key_slip(t, things)
                if slip:
                    t["check"] = f"words name {slip}"
            for t in sorted(targets, key=lambda t: STRENGTHS.index(t["strength"])):
                print(f"  {t['strength']:9} [{t['key']}] words={t['words']!r} search={t['search_for']!r}"
                      + (f" votes={t['votes']}" if "votes" in t else "")
                      + (f"   <- CHECK KEY: {t['check']}" if "check" in t else ""))
            results.append({"n": n, **sent, "targets": targets, "raw": raw})
    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"variant": a.variant, "think": a.think, "samples": a.samples, "frames": a.frames,
                   "model": a.model, "things": things, "sentences": results}, f, indent=2)
    print(f"\nsaved {a.out}")


if __name__ == "__main__":
    main()
