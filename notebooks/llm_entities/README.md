# LLM entity clues (exploration)

**Branch:** `exp/llm-entities` (exploratory; not merged into `main`).
**Status:** first prompt tried on six sentences; no test set yet.

## Question

Can a small local LLM read narration (text only, no frames) and give, for every mentioned thing, the
language clues the importance step needs: is it here now, and why (`cue`); its grammatical role; whether
the speaker points at it or gives an opinion on it; and what to search the frame for? See design
§5.2 and §5.2.1.

The model doesn't output an importance number. It outputs clues as categories, and importance will be
computed from them with a fixed formula. Rule for visibility: the text can rule a mention out
(`visible_now: no`), and SAM decides the rest by finding the object or not (`yes` / `unsure` → search).

## Setup (WSL / Linux)

1. Check the GPU: `nvidia-smi` should list your NVIDIA card. Without it everything runs on the CPU (slow).
2. Install Ollama and download the model (~7 GB):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull qwen3.5:9b
   ollama run qwen3.5:9b        # optional: chat in the terminal, /bye to quit
   ```
   If a command can't connect, start the server in another terminal: `ollama serve`.
3. Python libraries (in the project's virtual environment):
   ```bash
   pip install -e ".[llm]"      # from the repository root; installs ollama and pydantic
   ```

## Running

```bash
cd notebooks/llm_entities
python3 try_qwen.py                                  # six built-in test sentences
python3 try_qwen.py "Look at the dog! My cat back home would never do that."
python3 try_qwen.py --file transcript.txt --ctx 16384    # long text needs a bigger context
python3 try_qwen.py --json                           # also print the raw JSON
python3 try_qwen.py --model qwen3.5:4b               # a smaller, faster model
```

Inside the script: `Mention` / `Result` fix the shape of the answer; `RULES` are the instructions (edit
these to change behaviour); `SHOT_IN` / `SHOT_OUT` is one worked example shown to the model; `analyse()`
makes the call (temperature 0 and a fixed seed, so the same input gives the same output).

## If it is slow

- `ollama ps` while it runs: `PROCESSOR` should say `100% GPU`. `100% CPU` means the GPU isn't used
  (check `nvidia-smi` in WSL; update the NVIDIA driver on Windows, then `wsl --shutdown`). A CPU/GPU split
  means the model doesn't fit: lower `--ctx` or use `--model qwen3.5:4b`.
- Don't use `--think` for this task (see below).
- The first call loads the model (10-30 s); later calls are quick while Ollama keeps it loaded.

## What we've learnt so far

| Date | Model | Prompt | Finding |
|---|---|---|---|
| 2026-10-07 | qwen3.5:9b (Ollama) | v1: field meanings only in the schema | Visibility mostly right (elsewhere, idiom, hypothetical, negated, presentative). "The dog catching a squirrel" wrongly called *generic*. `search_for`, `evaluated`, `attention_cue` nonsense: the model doesn't see field descriptions inside the schema. Phrases lost "the", "no". |
| 2026-10-07 | qwen3.5:9b, `--think` | v1 | 900-3,300 words of reasoning per sentence (very slow) and the same mistakes. Thinking off from now on. |
| 2026-10-07 | qwen3.5:9b | v2: every field explained in the instructions, cue before decision, one worked example | Not run yet. |

## Habits

- Change one thing at a time and rerun the same sentences.
- When it gets a case wrong, add a worked example of that case; keep examples different from test sentences.
- Record the model tag and ID (`ollama list`) with every result; Ollama's download is a compressed
  (quantised) version of the model, fine for development.
- Save runs worth keeping under `results/` as `<date>_<model>_<prompt-version>.txt`.

## Next

1. Run v2 without `--think`.
2. A test set: 50-100 sentences covering the clue types in design §5.2.1, with the expected answers written
   down before running; score every prompt change on it.
3. Compare with a second model family and one large model as a ceiling.
4. When it settles: code to `src/sgroi/importance/ours/`, the prompt to `configs/prompts/`, the test set to
   `data/eval/` (on a `feat/` branch).
