"""What a model call returns, the same for every model file, and adding up what calls used."""

from dataclasses import dataclass, field


@dataclass
class Reply:
    answer: object  # the checked answer, or None if no try gave a usable one
    thinking: str  # the model's reasoning ("" with thinking off, or if the model doesn't show it)
    prompt_tokens: int
    # Gemini only: interaction ids, token counts, cost
    usage: dict = field(default_factory=dict)


def total_usage(usages):
    """Add up usage records: token counts and cost are summed (the cost is None if any cost is
    unknown), interaction ids are listed in order."""
    total = {}
    for u in usages:
        for k, v in u.items():
            if k == "interaction_ids":
                total[k] = total.get(k, []) + v
            elif k == "cost_usd":
                known = k not in total or total[k] is not None
                total[k] = total.get(k, 0) + v if v is not None and known else None
            else:
                total[k] = total.get(k, 0) + v
    return total
