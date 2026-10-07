"""First try of Qwen3.5-9B for the entity step: read a piece of narration and
list the mentioned things with text-only clues (visible now?, why, role, ...).

Setup and notes: README.md in this folder.

Run:
    python3 try_qwen.py                          # built-in test sentences
    python3 try_qwen.py "Look at the dog! My cat back home would never do that."
    python3 try_qwen.py --file transcript.txt
    python3 try_qwen.py --think                  # let the model reason first (slower)
"""

import argparse
import json
from typing import Literal

from ollama import chat
from pydantic import BaseModel

MODEL = "qwen3.5:9b"

# ---- what we want back: the model must answer in exactly this shape ----------

Cue = Literal["none", "presentative", "past", "future", "generic", "hypothetical", "negated",
              "elsewhere", "idiom", "reported", "abstract"]


class Mention(BaseModel):
    # The model fills these in this order, so the evidence (cue) comes before the decision.
    phrase: str
    refers_back_to: str
    cue: Cue
    visible_now: Literal["yes", "no", "unsure"]
    role: Literal["subject", "object", "other"]
    attention_cue: bool
    evaluated: bool
    search_for: str


class Result(BaseModel):
    mentions: list[Mention]


# ---- the instructions (the "program") ------------------------------------------
# The schema only fixes the shape of the answer; the model doesn't reliably see what
# each field means, so every field is explained here.

RULES = """You analyse what a narrator says in a video. You only see the words, never the picture.

List every noun phrase or pronoun that could refer to a physical thing, person or animal.
Skip abstract things (ideas, time, money as a concept). For each one, fill these fields:

phrase: the exact words as spoken, keeping words like "the", "my", "this", "no" and adjectives
  ("the black dog", "this little guy", "no lid").
refers_back_to: for a pronoun (it, she, he, they, him, them), the earlier phrase it means; otherwise "".
cue: the language clue about whether the thing is here now:
  past / future: the sentence is about another time ("the dog caught one yesterday")
  generic: about a kind of thing in general, usually a bare plural or "a ... is" ("dogs are loyal",
    "a cat hates water"). A specific "the dog", "my dog" or "this dog" is NOT generic.
  hypothetical: possible, imagined or suggested, not actual ("if you had a dog", "you could use a whisk")
  negated: said to be absent ("there's no lid", "without the lid")
  elsewhere: somewhere else ("back home", "in the other room")
  idiom: not meant literally ("raining cats and dogs")
  reported: inside someone else's reported words
  presentative: shown or pointed at now ("here's", "this is", "look at", "as you can see", "this one")
  none: none of these. Most plain present-tense mentions are none.
  For a pronoun, copy the cue of what it refers back to.
visible_now: "no" for past, future, generic, hypothetical, negated, elsewhere, idiom, reported;
  "yes" for presentative; "unsure" for none.
role: "subject", "object" or "other" in its own sentence.
attention_cue: true only if the speaker tells the viewer to look at or watch this thing
  ("look at the dog", "watch the water", "check this out"); otherwise false.
evaluated: true only if the speaker gives an opinion or feeling about this thing ("fun to watch",
  "beautiful", "gross", "so cute"). Size or colour alone is not an opinion; otherwise false.
search_for: a short visual description to find it in the picture ("black dog", "fork", "pot").
  If the words don't say what kind of thing it is ("this little guy", "that"), write "unknown".

Answer only with the JSON."""

# One worked example, shown to the model as an earlier question and answer.
# Keep it different from the test sentences, or the test says nothing.
SHOT_IN = "Cats usually hate water. But look at my cat here, she's so cute! The towel on the chair is for later."
SHOT_OUT = Result(mentions=[
    Mention(phrase="Cats", refers_back_to="", cue="generic", visible_now="no", role="subject",
            attention_cue=False, evaluated=False, search_for="cat"),
    Mention(phrase="water", refers_back_to="", cue="generic", visible_now="no", role="object",
            attention_cue=False, evaluated=False, search_for="water"),
    Mention(phrase="my cat", refers_back_to="", cue="presentative", visible_now="yes", role="object",
            attention_cue=True, evaluated=False, search_for="cat"),
    Mention(phrase="she", refers_back_to="my cat", cue="presentative", visible_now="yes", role="subject",
            attention_cue=False, evaluated=True, search_for="cat"),
    Mention(phrase="The towel", refers_back_to="", cue="none", visible_now="unsure", role="subject",
            attention_cue=False, evaluated=False, search_for="towel"),
    Mention(phrase="the chair", refers_back_to="", cue="none", visible_now="unsure", role="other",
            attention_cue=False, evaluated=False, search_for="chair"),
]).model_dump_json()

EXAMPLES = [
    "The dog catching a squirrel is fun to watch.",
    "My cat back home would never do that.",
    "Look at this little guy! It keeps running in circles.",
    "It's raining cats and dogs out there.",
    "You could use a whisk, but I'll just use this fork.",
    "There's no lid on the pot, so watch the water.",
]


def analyse(text, think=False, model=MODEL, ctx=4096):
    response = chat(
        model=model,
        messages=[{"role": "system", "content": RULES},
                  {"role": "user", "content": SHOT_IN},          # worked example ...
                  {"role": "assistant", "content": SHOT_OUT},    # ... and its answer
                  {"role": "user", "content": text}],
        format=Result.model_json_schema(),      # forces the reply into the Result shape
        think=think,
        options={"temperature": 0.6 if think else 0.0,   # reasoning mode should not use temperature 0
                 "seed": 1,                              # same input -> same output
                 "num_ctx": ctx},                        # tokens of room; raise for long transcripts
    )
    return Result.model_validate_json(response.message.content), response.message.thinking


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="narration to analyse (default: built-in examples)")
    ap.add_argument("--file", help="read the narration from a text file")
    ap.add_argument("--think", action="store_true", help="let the model reason before answering")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--ctx", type=int, default=4096,
                    help="context size in tokens (default 4096; e.g. 16384 for long transcripts, uses more GPU memory)")
    ap.add_argument("--json", action="store_true", help="print the raw JSON too")
    a = ap.parse_args()

    if a.file:
        with open(a.file, encoding="utf-8") as f:
            texts = [f.read()]
    else:
        texts = [a.text] if a.text else EXAMPLES

    for text in texts:
        result, thinking = analyse(text, a.think, a.model, a.ctx)
        print(f"\n> {text}")
        if a.think and thinking:
            print(f"  (reasoning: {len(thinking.split())} words)")
        for m in result.mentions:
            flags = [f for f, on in (("look-cue", m.attention_cue), ("evaluated", m.evaluated)) if on]
            back = f" -> {m.refers_back_to}" if m.refers_back_to else ""
            print(f"  {m.phrase!r:24} visible={m.visible_now:6} cue={m.cue:12} role={m.role:7} "
                  f"search={m.search_for!r}{back} {' '.join(flags)}")
        if a.json:
            print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
