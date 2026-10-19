"""What a run prints, and the JSON file it saves."""

import json
import os

from prompts import format_things


def show_prompt(prompt, last_text=None):
    """Print a prompt once, as it is sent (example answers laid out for reading)."""
    print("=" * 78)
    print(
        f"PROMPT ({prompt.name}, {prompt.version})"
        + (
            f" - messages 1-{len(prompt.labelled)} are sent with every sentence"
            if last_text
            else ""
        )
    )
    print("=" * 78)
    for i, (label, msg) in enumerate(prompt.labelled, 1):
        content = msg["content"]
        if msg["role"] == "assistant":
            content = (
                json.dumps(json.loads(content), indent=2)
                + "\n(sent as a single line of JSON)"
            )
        print(f"\n--- {i}. {label} ---\n{content}")
    if last_text:
        print(
            f"\n--- {len(prompt.labelled) + 1}. user: the sentence and its frames (different every time), "
            f"the first one: ---\n{last_text}"
        )
    print("=" * 78)


def print_things(things, seconds):
    print(f"\nTHINGS IN THIS VIDEO   ({seconds:.1f} s)")
    print(format_things(things))


def print_sentence(result):
    """One analysed sentence: its merged entries, then what was left out."""
    print(
        f"\n{result['n']} [{result['start']:.2f}-{result['end']:.2f} s] {result['text']}   "
        f"({result['seconds']:.1f} s)"
    )
    if result["failed"]:
        print("  (no usable answer: recorded as empty)")
    for t in result["look_at_merged"]:
        note = f"   ({t['merged']} entries merged)" if t["merged"] > 1 else ""
        print(
            f"  {t['attention']:6} [{t['key']}] search={t['search_for']!r} on_screen={t['on_screen']} "
            f"({t['main_clue']}){note}"
        )
        print(f"         {t['reason']}")
    for item in result["left_out"]:
        print(f"  left out: {item['words']!r} ({item['why']})")


def save_run(path, run):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2)
    print(f"\nsaved {path}")
