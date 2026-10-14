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

Two prompts (--prompt):
  strict  (default) one entry per noun phrase or pronoun, with language clues (above)
  goal    first, once per video, a text-only call lists the things in the video, each
          with an id; then, per sentence, one entry per thing the viewer looks at because
          of the sentence, keyed by those ids (enforced), with why, how strongly
          (attention) and a search text, plus what was left out and why. Entries with
          the same key are merged. The answer fields and their definitions come from
          output_format.yaml.
The prompt(s) are printed once before the sentences are analysed.

Setup and notes: README.md in this folder.

Run:
    python3 try_qwen_video.py my_clip.mp4                         # transcribes with faster-whisper
    python3 try_qwen_video.py my_clip.mp4 --transcript transcript.json
    python3 try_qwen_video.py my_clip.mp4 --transcript other_results/rankings.json
    python3 try_qwen_video.py my_clip.mp4 --frames 1 --out results/my_clip.json
    python3 try_qwen_video.py my_clip.mp4 --prompt goal

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
import textwrap
import time
from typing import Literal

import yaml
from ollama import chat
from pydantic import BaseModel, create_model

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


# ---- the goal prompt: built from output_format.yaml -------------------------------------
# Two steps. First, once per video, a text-only call lists the things in the video, each
# with an id (the "things" list). Then, per sentence, the answer's key must be one of those
# ids (or "new"): the answer check enforces it, so one object keeps one key.

FORMAT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_format.yaml")
GOAL_PROMPT_VERSION = "goal-v4"
NEW_KEY = "new"

THINGS_INTRO = """You are given the transcript of a video. Make a list of the concrete things the speech
refers to: anything you could point at in a picture, such as an object, a person, an
animal, food or a plant. Later steps will look for these things in the video.

Read the whole transcript first. Then list each thing once, however many times and in
however many ways it is referred to. Pronouns and names are not things themselves: they
belong to the thing they refer to. Leave pointing words ("this", "that") out: later steps
can see what is pointed at.
If a part of something is talked about on its own, list it separately.

List a thing whether or not it is likely to be in the video; later steps decide that.
Do not list things meant in general, places or directions, or figures of speech."""

GOAL_INTRO = """You help a video encoder decide where to spend detail. Viewers look at what the speech
draws their attention to, so the encoder will make those regions sharper.

You get the full transcript of a video, the list of things in it (each with an id), then
one sentence of the transcript that is being spoken now, with a few frames from that moment.

List the things a viewer would look at because of what is said in THIS sentence:
things named, things referred to by a pronoun, a name, a pointing word ("this", "that")
or a gesture, and things only implied ("she's slicing" -> the knife and the food).
Use the whole transcript and the list of things to work out what the words refer to,
and the frames to see what is being pointed at. One entry per thing, even if the
sentence mentions it twice.

Leave out things that are not here now: in the past or future, somewhere else,
hypothetical, about things in general, absent ("there's no lid"), or only a figure of
speech ("raining cats and dogs"). List those under left_out with the reason."""

# Worked examples in the same format as the real calls (no pictures, so on_screen is "unsure").
GOAL_SHOT_SENTENCES = [
    {"start": 0.0, "end": 1.1, "text": "This is Luna."},
    {"start": 1.3, "end": 4.6, "text": "Cats usually hate water, but look at her paws in the bowl, isn't that funny?"},
    {"start": 4.8, "end": 6.0, "text": "My other cat is at the vet today."},
]
GOAL_SHOT_THINGS = {"things": [
    {"id": "luna", "what": "the speaker's cat, Luna", "first_mention": "1: Luna", "also_called": ["her"]},
    {"id": "luna_paws", "what": "Luna's paws", "first_mention": "2: her paws", "also_called": []},
    {"id": "bowl", "what": "the bowl the paws are in", "first_mention": "2: the bowl", "also_called": []},
    {"id": "other_cat", "what": "the speaker's other cat, at the vet", "first_mention": "3: My other cat",
     "also_called": []},
]}
GOAL_SHOT_ANSWER = {
    "look_at": [
        {"reason": "The speaker tells the viewer to look at Luna's paws in the water.",
         "key": "luna_paws", "search_for": "the cat's paws", "on_screen": "unsure",
         "attention": "high", "main_clue": "named"},
        {"reason": "Her paws are in it, so it is part of what is being shown.",
         "key": "bowl", "search_for": "water bowl", "on_screen": "unsure",
         "attention": "medium", "main_clue": "named"},
        {"reason": "'her' is Luna, whose paws are being shown.",
         "key": "luna", "search_for": "cat", "on_screen": "unsure",
         "attention": "medium", "main_clue": "pronoun"},
    ],
    "left_out": [
        {"words": "Cats", "why": "general"},
        {"words": "water", "why": "general"},
    ],
}


def load_format(path=FORMAT_FILE):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _field_type(name, spec, ids=()):
    values = spec.get("values")
    if values == "text":
        return str
    if values == "list of text":
        return list[str]
    if values == "id":                                   # one of this video's thing ids, or new
        return Literal[tuple(ids) + (NEW_KEY,)]
    if isinstance(values, list) and values:
        return Literal[tuple(str(v) for v in values)]
    raise ValueError(f"{FORMAT_FILE}: field '{name}' needs values: text, list of text, id, or a list")


def section_model(fmt, section, name, ids=()):
    fields = fmt[section]["fields"]
    return create_model(name, **{k: (_field_type(k, v, ids), ...) for k, v in fields.items()})


def describe_fields(fields, line_width=92):
    """The field definitions from output_format.yaml, as text for the instructions."""
    width = max(len(name) for name in fields) + 2
    lines = []
    for name, spec in fields.items():
        text = str(spec.get("definition") or "").strip()
        if isinstance(spec["values"], list):
            allowed = "One of: " + ", ".join(str(v) for v in spec["values"]) + "."
            text = allowed if not text else text + ("\n" if "\n" in text else " ") + allowed
        wrapped = [w for line in (text or str(spec["values"]) + ".").splitlines()
                   for w in textwrap.wrap(line, line_width - width - 3) or [""]]
        lines.append(f"  {name + ':':{width}} {wrapped[0]}")
        lines += [f"  {'':{width}} {w}" for w in wrapped[1:]]
    return "\n".join(lines)


def describe_section(fmt, section, title):
    about = str(fmt[section].get("about") or "").strip()
    return (f"{title} - {about}" if about else f"{title}:") + "\n" + describe_fields(fmt[section]["fields"])


def format_things(things):
    """The things list as text for the per-sentence calls."""
    if not things:
        return "Things in this video: none found (use new as key)."
    width = max(len(t["id"]) for t in things) + 2
    lines = ["Things in this video (use these ids as key):"]
    for t in things:
        also = f"; also: {', '.join(t['also_called'])}" if t["also_called"] else ""
        lines.append(f"  {t['id']:{width}} {t['what']}  (first: {t['first_mention']}{also})")
    return "\n".join(lines)


def things_step(fmt):
    """Step 1 (once per video): instructions, worked example and answer check for the things list."""
    thing = section_model(fmt, "things", "Thing")
    result = create_model("ThingsResult", things=(list[thing], ...))
    system = "\n\n".join([THINGS_INTRO, describe_section(fmt, "things", "For each thing give"),
                          "Answer only with the JSON."])

    def fixed(transcript):
        return [("system: instructions", {"role": "system", "content": system}),
                ("user: example transcript", {"role": "user", "content": format_transcript(GOAL_SHOT_SENTENCES)}),
                ("assistant: example answer", {"role": "assistant",
                                               "content": result(**GOAL_SHOT_THINGS).model_dump_json()}),
                ("user: this video's transcript", {"role": "user", "content": transcript})]
    return {"name": "things", "version": f"{GOAL_PROMPT_VERSION} / {fmt['version']}", "fixed": fixed,
            "result": result}


def clean_things(things):
    """Make the ids usable as keys: lowercase, letters/digits/_ only, unique, not 'new'."""
    seen, out = set(), []
    for t in things:
        base = re.sub(r"[^a-z0-9_]+", "_", t["id"].strip().lower()).strip("_") or "thing"
        if base == NEW_KEY:
            base = "new_thing"
        tid, k = base, 2
        while tid in seen:
            tid, k = f"{base}_{k}", k + 1
        if tid != t["id"]:
            print(f"  (id {t['id']!r} changed to {tid!r})")
        seen.add(tid)
        out.append({**t, "id": tid})
    return out


def goal_prompt(fmt, things):
    """Step 2 (per sentence): instructions, worked example and answer check; key must be a thing id."""
    def result_model(ids):
        target = section_model(fmt, "look_at", "Target", ids)
        left_out = section_model(fmt, "left_out", "LeftOut")
        return create_model("GoalResult", look_at=(list[target], ...), left_out=(list[left_out], ...))
    example_ids = [t["id"] for t in GOAL_SHOT_THINGS["things"]]
    example_answer = result_model(example_ids)(**GOAL_SHOT_ANSWER).model_dump_json()   # fails if it breaks the format
    system = "\n\n".join([GOAL_INTRO,
                          describe_section(fmt, "look_at", "For each thing to look at"),
                          describe_section(fmt, "left_out", "For each thing left out"),
                          "Answer only with the JSON."])

    def fixed(transcript):
        return [("system: instructions", {"role": "system", "content": system}),
                ("user: example transcript", {"role": "user", "content": format_transcript(GOAL_SHOT_SENTENCES)}),
                ("user: example things", {"role": "user", "content": format_things(GOAL_SHOT_THINGS["things"])}),
                ("user: example sentence", {"role": "user",
                                            "content": format_sentence(2, GOAL_SHOT_SENTENCES[1], [])}),
                ("assistant: example answer", {"role": "assistant", "content": example_answer}),
                ("user: this video's transcript", {"role": "user", "content": transcript}),
                ("user: this video's things", {"role": "user", "content": format_things(things)})]
    return {"name": "goal", "version": f"{GOAL_PROMPT_VERSION} / {fmt['version']}", "fixed": fixed,
            "result": result_model([t["id"] for t in things]),
            "attention_order": list(fmt["look_at"]["fields"]["attention"]["values"])}


def strict_prompt():
    def fixed(transcript):
        return [("system: instructions", {"role": "system", "content": VIDEO_RULES}),
                ("user: example transcript", {"role": "user", "content": SHOT_TRANSCRIPT}),
                ("user: example sentence", {"role": "user", "content": SHOT_IN}),
                ("assistant: example answer", {"role": "assistant", "content": SHOT_OUT}),
                ("user: this video's transcript", {"role": "user", "content": transcript})]
    return {"name": "strict", "version": PROMPT_VERSION, "fixed": fixed, "result": VideoResult}


def fixed_messages(prompt, transcript):
    """Everything sent before the sentence itself: the same in every call for one video."""
    return [msg for _, msg in prompt["fixed"](transcript)]


def show_prompt(prompt, transcript, last_text=None):
    """Print a prompt once, as it is sent (example answers laid out for reading)."""
    labelled = prompt["fixed"](transcript)
    print("=" * 78)
    print(f"PROMPT ({prompt['name']}, {prompt['version']})"
          + (f" - messages 1-{len(labelled)} are sent with every sentence" if last_text else ""))
    print("=" * 78)
    for i, (label, msg) in enumerate(labelled, 1):
        content = msg["content"]
        if msg["role"] == "assistant":
            content = json.dumps(json.loads(content), indent=2) + "\n(sent as a single line of JSON)"
        print(f"\n--- {i}. {label} ---\n{content}")
    if last_text:
        print(f"\n--- {len(labelled) + 1}. user: the sentence and its frames (different every time), "
              f"the first one: ---\n{last_text}")
    print("=" * 78)


def make_things(fmt, transcript, model, ctx):
    """Step 1: the things in the video, from the whole transcript (no frames)."""
    step = things_step(fmt)
    show_prompt(step, transcript)
    t0 = time.time()
    response = chat(model=model, messages=fixed_messages(step, transcript),
                    format=step["result"].model_json_schema(), think=False,
                    options={"temperature": 0.0, "seed": 1, "num_ctx": ctx})
    things = [t.model_dump() for t in step["result"].model_validate_json(response.message.content).things]
    print(f"\nTHINGS IN THIS VIDEO   ({time.time() - t0:.1f} s)")
    things = clean_things(things)
    print(format_things(things))
    return things


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

def analyse_sentence(prompt, transcript, n, sentence, images, times, model, ctx):
    # Order matters for speed: everything up to and including the video's transcript is
    # identical in every call for one video, so Ollama can reuse its work on that part;
    # only the last message (the sentence and its frames) changes.
    messages = fixed_messages(prompt, transcript) + [
        {"role": "user", "content": format_sentence(n, sentence, times), "images": images}]

    response = chat(
        model=model,
        messages=messages,
        format=prompt["result"].model_json_schema(),
        think=False,
        options={"temperature": 0.0, "seed": 1, "num_ctx": ctx},
    )
    return prompt["result"].model_validate_json(response.message.content)


def report_strict(res, sent):
    mentions = []
    for m in res.mentions:
        in_sentence = phrase_in_sentence(m.phrase, sent["text"])
        notes = ("   <- words and pictures disagree" if {m.visible_now, m.in_frames} == {"yes", "no"} else "")
        if not in_sentence:
            notes += "   <- NOT in this sentence"
        print(f"  {m.phrase!r:22} [{m.first_mention}] words={m.visible_now:6} ({m.cue:12}) "
              f"pictures={m.in_frames:6} search={m.search_for!r}{notes}")
        mentions.append({**m.model_dump(), "phrase_in_sentence": in_sentence})
    return {"mentions": mentions}


def merge_by_key(items, attention_order):
    """Entries with the same key are the same thing: keep one, with the strongest attention
    (and its search text and clue), on screen if any says so, and all the reasons."""
    rank = {v: i for i, v in enumerate(attention_order)}          # first value = strongest
    seen_rank = {"yes": 0, "unsure": 1, "no": 2}
    merged = {}
    for d in (t.model_dump() for t in items):
        k = d["key"] if d["key"] != NEW_KEY else f"{NEW_KEY}#{len(merged)}"
        if k not in merged:
            merged[k] = {**d, "merged": 1}
            continue
        m = merged[k]
        m["merged"] += 1
        if rank.get(d["attention"], 99) < rank.get(m["attention"], 99):
            m.update(attention=d["attention"], search_for=d["search_for"], main_clue=d["main_clue"])
        if seen_rank.get(d["on_screen"], 9) < seen_rank.get(m["on_screen"], 9):
            m["on_screen"] = d["on_screen"]
        m["reason"] += " / " + d["reason"]
    return list(merged.values())


def report_goal(res, sent, attention_order):
    merged = merge_by_key(res.look_at, attention_order)
    for t in merged:
        note = f"   ({t['merged']} entries merged)" if t["merged"] > 1 else ""
        print(f"  {t['attention']:6} [{t['key']}] search={t['search_for']!r} on_screen={t['on_screen']} "
              f"({t['main_clue']}){note}")
        print(f"         {t['reason']}")
    for item in res.left_out:
        print(f"  left out: {item.words!r} ({item.why})")
    return {"look_at": [t.model_dump() for t in res.look_at], "look_at_merged": merged,
            "left_out": [item.model_dump() for item in res.left_out]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--transcript", help="timed transcript JSON (skips transcription)")
    ap.add_argument("--whisper", default="small.en", help="faster-whisper model if transcribing (default small.en)")
    ap.add_argument("--frames", type=int, default=3, help="frames per sentence (default 3; 0 = text only)")
    ap.add_argument("--width", type=int, default=768, help="frame width in pixels (default 768; smaller is faster)")
    ap.add_argument("--prompt", choices=["strict", "goal"], default="strict",
                    help="strict (default): per noun phrase, language clues; goal: per thing to look at "
                         "(fields from output_format.yaml)")
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
    things, fmt_version = None, None
    if a.prompt == "goal":
        fmt = load_format()
        fmt_version = fmt["version"]
        things = make_things(fmt, transcript, a.model, a.ctx)              # step 1, once per video
        prompt = goal_prompt(fmt, things)

        def report(res, sent):
            return report_goal(res, sent, prompt["attention_order"])
    else:
        prompt, report = strict_prompt(), report_strict
    first_times = frame_times(sentences[0]["start"], sentences[0]["end"], a.frames, duration) if a.frames > 0 else []
    show_prompt(prompt, transcript, format_sentence(1, sentences[0], first_times)
                + ("\n[+ the frame images]" if first_times else ""))
    frame_dir = a.keep_frames or tempfile.mkdtemp(prefix="qwen_frames_")
    os.makedirs(frame_dir, exist_ok=True)
    results = []
    try:
        for n, sent in enumerate(sentences, 1):
            times = frame_times(sent["start"], sent["end"], a.frames, duration) if a.frames > 0 else []
            images = [grab_frame(a.video, t, os.path.join(frame_dir, f"s{n:03d}_{t:07.3f}s.jpg"), a.width)
                      for t in times]
            t0 = time.time()
            res = analyse_sentence(prompt, transcript, n, sent, images, times, a.model, a.ctx)
            took = time.time() - t0
            print(f"\n{n} [{sent['start']:.2f}-{sent['end']:.2f} s] {sent['text']}   ({took:.1f} s)")
            results.append({"n": n, **sent, "frame_times": times, "seconds": round(took, 2),
                            **report(res, sent)})
    finally:
        if not a.keep_frames:
            shutil.rmtree(frame_dir, ignore_errors=True)

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"video": os.path.basename(a.video), "model": a.model, "prompt": prompt["name"],
                       "prompt_version": prompt["version"], "format_version": fmt_version, "things": things,
                       "frames_per_sentence": a.frames, "frame_width": a.width, "sentences": results}, f, indent=2)
        print(f"\nsaved {a.out}")


if __name__ == "__main__":
    main()
