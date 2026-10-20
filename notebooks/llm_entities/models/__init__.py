"""Which model file answers: model names starting with gemini- go to Google's Gemini API
(gemini.py), all others to Ollama (ollama.py). Each file is imported only when it is used, so
only its library needs to be installed."""

GEMINI_PREFIX = "gemini-"


def is_gemini(model):
    return model.startswith(GEMINI_PREFIX)


def call_model(messages, answer, model, ctx, think, what="answer"):
    """Send the messages; the reply must match the pydantic model `answer` (see Reply)."""
    if is_gemini(model):
        from models import gemini as chosen
    else:
        from models import ollama as chosen
    return chosen.call_model(messages, answer, model, ctx, think, what)
