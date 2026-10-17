"""The two steps of the method.

Step 1, once per video, from the words only: the list of things in the video, each with an id.
Step 2, per sentence, with its frames: the things a viewer looks at because of the sentence,
each keyed by a thing id (the answer check enforces it, so one object keeps one key).
"""

import re
import sys

from answer_format import NEW_KEY
from model import call_model
from prompts import sentence_message


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


def make_things(prompt, model, ctx):
    """Step 1: the things in the video (thinking off: it is a plain listing task)."""
    reply = call_model(prompt.messages, prompt.answer, model, ctx, think=False, what="things list")
    if reply.answer is None:
        sys.exit("step 1 gave no usable things list")
    return clean_things([t.model_dump() for t in reply.answer.things])


def analyse_sentence(prompt, n, sentence, times, images, model, ctx, think):
    """Step 2 for sentence number n: the model's Reply (its answer is None if unusable)."""
    messages = prompt.messages + [sentence_message(n, sentence, times, images)]
    return call_model(messages, prompt.answer, model, ctx, think, what=f"sentence {n}")


def merge_by_key(items, attention_order):
    """Entries with the same key are the same thing: keep one, with the strongest attention
    (and its search text and clue), on screen if any says so, and all the reasons."""
    rank = {v: i for i, v in enumerate(attention_order)}          # first value = strongest
    seen_rank = {"yes": 0, "unsure": 1, "no": 2}
    merged = {}
    for d in items:
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
