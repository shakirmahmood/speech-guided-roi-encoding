"""Talk to a Gemini model (gemini-4-argon, or gemini-3.8-flash for free tests) through Google's
Interactions API.

The messages built for Ollama are translated: the system message becomes the system
instruction, user messages become user turns (frames go inside the request as JPEG), and the
worked example's answer becomes a model turn. All calls for one video start with the same
messages, so these are sent once, as a starting interaction that ends with the model replying
"ready"; each call then continues from it (previous_interaction_id) and sends only its own last
message. Google caches the shared part, which is billed at the cached-input price. If Gemini
refuses to continue from the same interaction twice, the full messages are sent from then on.

Interactions are stored by Google (55 days on the paid tier, or less if set in AI Studio) and
are not used for training on the paid tier. Their ids are saved with the run, to look them up in
AI Studio, ask follow-up questions, or delete them.

Needs: pip install -e ".[gemini]" (from the repository root) and the API key in GEMINI_API_KEY.
Settings (thinking level, prices): the gemini section of config/settings.yaml.
"""

import base64
import functools
import hashlib
import json
import os
import sys

import yaml
from pydantic import ValidationError

from models.reply import Reply, total_usage

TRIES = 3  # tries when an answer is unusable; every try is billed
READY = "The message to answer comes next. Until then, reply only with: ready"
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "settings.yaml",
)

_starts = (
    {}
)  # shared messages -> id of their starting interaction (None: send them in full)


@functools.cache
def settings():
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)["gemini"]


@functools.cache
def client():
    from google import genai  # imported here, so Ollama runs don't need it

    return genai.Client()  # reads GEMINI_API_KEY


def thinking_level(think):
    """With thinking: the level in settings.yaml. Without: low (Gemini can't switch it off)."""
    return settings()["thinking_level"] if think else "low"


def text_part(text):
    return {"type": "text", "text": text}


def image_part(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return {"type": "image", "data": data, "mime_type": "image/jpeg"}


def to_turns(messages):
    """Ollama-style messages -> (system instruction, turns for the Interactions API)."""
    system, turns = [], []
    for m in messages:
        if m["role"] == "system":
            system.append(m["content"])
            continue
        content = [text_part(m["content"])] + [
            image_part(p) for p in m.get("images", [])
        ]
        kind = "model_output" if m["role"] == "assistant" else "user_input"
        turns.append({"type": kind, "content": content})
    return "\n\n".join(system), turns


def cost(counts, model):
    """US dollars, from the prices in settings.yaml; None if the model has no price there."""
    price = settings()["prices"].get(model)
    if price is None:
        warn_no_price(model)
        return None
    fresh = counts["input_tokens"] - counts["cached_tokens"]
    written = counts["thinking_tokens"] + counts["output_tokens"]
    return (
        fresh * price["input"]
        + counts["cached_tokens"] * price["cached_input"]
        + written * price["output"]
    ) / 1e6


@functools.cache
def warn_no_price(model):
    print(
        f"  WARNING: no price for {model} in settings.yaml; cost not counted",
        file=sys.stderr,
    )


def usage_of(interaction, model):
    """What one interaction used: its id, token counts and cost."""
    u = interaction.usage
    counts = {
        "input_tokens": getattr(u, "total_input_tokens", None) or 0,
        "cached_tokens": getattr(u, "total_cached_tokens", None) or 0,
        "thinking_tokens": getattr(u, "total_thought_tokens", None) or 0,
        "output_tokens": getattr(u, "total_output_tokens", None) or 0,
    }
    return {
        "interaction_ids": [interaction.id],
        **counts,
        "cost_usd": cost(counts, model),
    }


def create(**request):
    """One stored interaction. A wrong key, missing billing or unknown model stops the run with a
    plain message (the library itself retries rate limits and server errors)."""
    from google.genai import errors

    try:
        return client().interactions.create(store=True, **request)
    except errors.APIError as e:
        if e.code in (401, 403):
            sys.exit(f"Gemini refused the key ({e}): check GEMINI_API_KEY and billing")
        if e.code == 404:
            sys.exit(
                f"Gemini model not found ({e}): check the name, and that billing is on "
                "(gemini-4-argon has no free tier)"
            )
        raise


def start(model, system, shared):
    """The key of the shared messages and the usage of making their starting interaction
    ({} if it was made by an earlier call)."""
    key = hashlib.sha256(json.dumps([model, system, shared]).encode()).hexdigest()
    if key in _starts:
        return key, {}
    r = create(
        model=model,
        system_instruction=system,
        input=shared + [{"type": "user_input", "content": [text_part(READY)]}],
        generation_config={"thinking_level": "low"},
    )
    _starts[key] = r.id
    return key, usage_of(r, model)


def send(request, key, shared, last):
    """Continue from the starting interaction; if Gemini refuses, send all the messages."""
    from google.genai import errors

    if _starts.get(key):
        try:
            return create(**request, previous_interaction_id=_starts[key], input=last)
        except errors.APIError as e:
            if e.code != 400:
                raise
            print(
                f"  WARNING: Gemini would not continue from the starting interaction ({e}); "
                "sending the full messages from now on",
                file=sys.stderr,
            )
            _starts[key] = None
    return create(**request, input=shared + last)


def call_model(messages, answer, model, ctx, think, what="answer"):
    """Send the messages; the reply must match the pydantic model `answer`. Up to TRIES tries.
    ctx is not used (Gemini's context is 1M tokens). The usage covers every try, and the
    starting interaction if this call made it."""
    system, turns = to_turns(messages)
    shared, last = turns[:-1], turns[-1:]
    key, usages = None, []
    if shared:
        key, made = start(model, system, shared)
        usages += [made] if made else []
    request = {
        "model": model,
        "system_instruction": system,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": answer.model_json_schema(),
        },
    }
    for retry in range(TRIES):
        request["generation_config"] = {
            "thinking_level": thinking_level(think),
            "seed": 1 + 100 * retry,
        }
        r = send(request, key, shared, last)
        usages.append(usage_of(r, model))
        text = r.output_text or ""
        try:
            return Reply(
                answer.model_validate_json(text),
                "",
                usages[-1]["input_tokens"],
                total_usage(usages),
            )
        except ValidationError as e:
            print(
                f"  WARNING: {what}: unusable answer (status {r.status}, {len(text)} chars; "
                f"{str(e).splitlines()[0]}); retrying",
                file=sys.stderr,
            )
    print(f"  WARNING: {what}: no usable answer after {TRIES} tries", file=sys.stderr)
    return Reply(None, "", 0, total_usage(usages))
