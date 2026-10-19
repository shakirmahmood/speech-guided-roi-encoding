"""The answer format: read output_format.yaml, build the answer checks from it (pydantic
models, also sent to Ollama as the JSON schema the answer must follow), and describe its
fields as text for the instructions."""

import os
import textwrap
from typing import Literal

import yaml
from pydantic import create_model

FORMAT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config", "output_format.yaml"
)
NEW_KEY = "new"  # the key for a thing that is not in the things list


def load_format(path=FORMAT_FILE):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _field_type(name, spec, ids=()):
    values = spec.get("values")
    if values == "text":
        return str
    if values == "list of text":
        return list[str]
    if values == "id":  # one of this video's thing ids, or new
        return Literal[tuple(ids) + (NEW_KEY,)]
    if isinstance(values, list) and values:
        return Literal[tuple(str(v) for v in values)]
    raise ValueError(
        f"{FORMAT_FILE}: field '{name}' needs values: text, list of text, id, or a list"
    )


def section_model(fmt, section, name, ids=()):
    fields = fmt[section]["fields"]
    return create_model(
        name, **{k: (_field_type(k, v, ids), ...) for k, v in fields.items()}
    )


def things_answer(fmt):
    """Step 1's answer: {"things": [...]}."""
    return create_model(
        "ThingsResult", things=(list[section_model(fmt, "things", "Thing")], ...)
    )


def sentence_answer(fmt, ids):
    """Step 2's answer: {"look_at": [...], "left_out": [...]}; each key must be one of ids, or new."""
    target = section_model(fmt, "look_at", "Target", ids)
    left_out = section_model(fmt, "left_out", "LeftOut")
    return create_model(
        "GoalResult", look_at=(list[target], ...), left_out=(list[left_out], ...)
    )


def attention_order(fmt):
    """The attention values, strongest first."""
    return list(fmt["look_at"]["fields"]["attention"]["values"])


def describe_fields(fields, line_width=92):
    """The field definitions from output_format.yaml, as text for the instructions."""
    width = max(len(name) for name in fields) + 2
    lines = []
    for name, spec in fields.items():
        text = str(spec.get("definition") or "").strip()
        if isinstance(spec["values"], list):
            allowed = "One of: " + ", ".join(str(v) for v in spec["values"]) + "."
            text = (
                allowed
                if not text
                else text + ("\n" if "\n" in text else " ") + allowed
            )
        wrapped = [
            w
            for line in (text or str(spec["values"]) + ".").splitlines()
            for w in textwrap.wrap(line, line_width - width - 3) or [""]
        ]
        lines.append(f"  {name + ':':{width}} {wrapped[0]}")
        lines += [f"  {'':{width}} {w}" for w in wrapped[1:]]
    return "\n".join(lines)


def describe_section(fmt, section, title):
    about = str(fmt[section].get("about") or "").strip()
    return (
        (f"{title} - {about}" if about else f"{title}:")
        + "\n"
        + describe_fields(fmt[section]["fields"])
    )
