"""Build the messages sent to the model for the two steps, from prompt_goal.yaml (the
instructions and the worked example) and output_format.yaml (the answer fields).

Everything up to and including this video's transcript (step 1) or things list (step 2) is
the same in every call for one video, so Ollama can reuse its work on that part; only the
last message of step 2, the sentence and its frames, changes from call to call.
"""

import os
from dataclasses import dataclass

import yaml

from answer_format import describe_section, sentence_answer, things_answer

PROMPT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config", "prompt_goal.yaml"
)


@dataclass
class Prompt:
    name: str
    version: str
    labelled: list  # (label, message) pairs sent before the sentence, in order
    answer: type  # pydantic model the answer must match

    @property
    def messages(self):
        return [msg for _, msg in self.labelled]


def load_prompt(path=PROMPT_FILE):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_transcript(sentences):
    """Numbered transcript, the same text in every call for one video."""
    return "Full transcript of the video (for context):\n" + "\n".join(
        f"  {n} [{s['start']:.2f}-{s['end']:.2f} s] {s['text']}"
        for n, s in enumerate(sentences, 1)
    )


def format_sentence(n, sentence, times):
    """The part that changes from call to call: which sentence, and its frames."""
    frames = (
        "Frames of sentence {}, in order, at: {}".format(
            n, ", ".join(f"{t:.2f} s" for t in times)
        )
        if times
        else "(No frames for this sentence.)"
    )
    return (
        f"Sentence to analyse: {n} [{sentence['start']:.2f}-{sentence['end']:.2f} s] {sentence['text']}\n"
        + frames
    )


def format_things(things):
    """The things list as text for the per-sentence calls."""
    if not things:
        return "Things in this video: none found (use new as key)."
    width = max(len(t["id"]) for t in things) + 2
    lines = ["Things in this video (use these ids as key):"]
    for t in things:
        also = f"; also: {', '.join(t['also_called'])}" if t["also_called"] else ""
        lines.append(
            f"  {t['id']:{width}} {t['what']}  (first: {t['first_mention']}{also})"
        )
    return "\n".join(lines)


def _version(text, fmt):
    return f"{text['version']} / {fmt['version']}"


def things_prompt(fmt, text, transcript):
    """Step 1 (once per video, words only): the list of things in the video."""
    answer = things_answer(fmt)
    ex = text["example"]
    system = "\n\n".join(
        [
            text["things_intro"],
            describe_section(fmt, "things", "For each thing give"),
            "Answer only with the JSON.",
        ]
    )
    labelled = [
        ("system: instructions", {"role": "system", "content": system}),
        (
            "user: example transcript",
            {"role": "user", "content": format_transcript(ex["sentences"])},
        ),
        (
            "assistant: example answer",
            {
                "role": "assistant",
                "content": answer(things=ex["things"]).model_dump_json(),
            },
        ),
        ("user: this video's transcript", {"role": "user", "content": transcript}),
    ]
    return Prompt("things", _version(text, fmt), labelled, answer)


def sentence_prompt(fmt, text, transcript, things):
    """Step 2 (per sentence): the things the viewer looks at; each key must be a thing id."""
    ex = text["example"]
    n = ex["example_sentence"]
    example_answer = sentence_answer(fmt, [t["id"] for t in ex["things"]])
    example_json = example_answer(
        **ex["answer"]
    ).model_dump_json()  # fails if it breaks the format
    system = "\n\n".join(
        [
            text["sentence_intro"],
            describe_section(fmt, "look_at", "For each thing to look at"),
            describe_section(fmt, "left_out", "For each thing left out"),
            "Answer only with the JSON.",
        ]
    )
    labelled = [
        ("system: instructions", {"role": "system", "content": system}),
        (
            "user: example transcript",
            {"role": "user", "content": format_transcript(ex["sentences"])},
        ),
        (
            "user: example things",
            {"role": "user", "content": format_things(ex["things"])},
        ),
        (
            "user: example sentence",
            {"role": "user", "content": format_sentence(n, ex["sentences"][n - 1], [])},
        ),
        ("assistant: example answer", {"role": "assistant", "content": example_json}),
        ("user: this video's transcript", {"role": "user", "content": transcript}),
        (
            "user: this video's things",
            {"role": "user", "content": format_things(things)},
        ),
    ]
    return Prompt(
        "goal",
        _version(text, fmt),
        labelled,
        sentence_answer(fmt, [t["id"] for t in things]),
    )


def sentence_message(n, sentence, times, images):
    """The last message of a step 2 call: the sentence and its frames."""
    return {
        "role": "user",
        "content": format_sentence(n, sentence, times),
        "images": images,
    }
