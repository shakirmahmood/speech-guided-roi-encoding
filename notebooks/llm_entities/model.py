"""Talk to the model through Ollama: sampling settings, retries for unusable answers, and a
warning when the prompt nearly fills the context."""

import sys
from dataclasses import dataclass

from ollama import chat
from pydantic import ValidationError

TRIES = 3


@dataclass
class Reply:
    answer: object  # the checked answer, or None if no try gave a usable one
    thinking: str  # the model's reasoning ("" with thinking off)
    prompt_tokens: int


def sampling(think, ctx, retry=0):
    """Ollama options. Thinking uses Qwen's recommended sampling for thinking mode. Without
    thinking, decoding is greedy; a retry (greedy decoding looped) uses Qwen's recommended
    sampling for non-thinking mode."""
    seed = 1 + 100 * retry
    if think:
        return {
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "seed": seed,
            "num_ctx": ctx,
        }
    if retry:
        return {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "presence_penalty": 1.5,
            "seed": seed,
            "num_ctx": ctx,
            "num_predict": 4096,
        }
    return {"temperature": 0.0, "seed": seed, "num_ctx": ctx, "num_predict": 4096}


def call_model(messages, answer, model, ctx, think, what="answer"):
    """Send the messages; the reply must match the pydantic model `answer`. Up to TRIES tries."""
    used = 0
    for retry in range(TRIES):
        r = chat(
            model=model,
            messages=messages,
            format=answer.model_json_schema(),
            think=think,
            options=sampling(think, ctx, retry),
        )
        used = getattr(r, "prompt_eval_count", None) or 0
        if (
            used and used >= ctx - 64
        ):  # Ollama silently drops the start of an over-long prompt
            print(
                f"  WARNING: prompt used {used} of {ctx} context tokens; raise --ctx",
                file=sys.stderr,
            )
        thinking = getattr(r.message, "thinking", None) or ""
        try:
            return Reply(answer.model_validate_json(r.message.content), thinking, used)
        except ValidationError as e:  # usually a repetition loop cut off mid-JSON
            print(
                f"  WARNING: {what}: unusable answer ({len(r.message.content)} chars; "
                f"{str(e).splitlines()[0]}); retrying",
                file=sys.stderr,
            )
    print(f"  WARNING: {what}: no usable answer after {TRIES} tries", file=sys.stderr)
    return Reply(None, "", used)
