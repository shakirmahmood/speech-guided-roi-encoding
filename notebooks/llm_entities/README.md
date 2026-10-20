# LLM entity choice (exploration)

**Branch:** `exp/llm-entities` (exploratory; not merged into `main`).
**Status:** goal-v4 prompt with thinking is the method; tested on one clip (Ratatouille minute).

## Question

Can a small local model (Qwen3.5-9B) read the speech of a video, with a few frames per sentence, and say
which things the viewer looks at because of each sentence, and how strongly? See design §5.2.

## How it works

1. **Speech to sentences** (`transcript.py`): faster-whisper with word times, or a transcript file.
2. **Step 1, once per video** (`steps.make_things`): from the whole transcript, words only, the model lists the
   things in the video, each with an id.
3. **Step 2, per sentence** (`steps.analyse_sentence`): the model gets the transcript, the things list, the
   sentence and 3 frames from while it is spoken (`frames.py`), and lists the things to look at
   (`look_at`) and the mentions left out (`left_out`). Each key must be an id from the things list, or `new`.
   Entries with the same key are merged.

## Files

| File | Its job |
|---|---|
| `run.py` | Command line: reads the options and runs the steps in order |
| `transcript.py` | Speech to timed sentences |
| `frames.py` | Frames for a sentence |
| `prompts.py` | Builds the messages for both steps |
| `answer_format.py` | Reads `output_format.yaml`; builds the answer checks and the field descriptions |
| `models/` | Model calls, picked by the model name (`__init__.py`): `ollama.py` (Qwen through Ollama: sampling settings, retries, context warning), `gemini.py` (Gemini through Google's API: starting interaction, retries, token counts and cost), `reply.py` (what a call returns) |
| `steps.py` | The two steps, and merging entries with the same key |
| `output.py` | What a run prints and the JSON file it saves |
| `score.py` | Compares saved runs with an answer key |
| `config/prompt_goal.yaml` | The prompt text and worked example (goal-v4) |
| `config/output_format.yaml` | The answer fields and their definitions (look_at-4) |
| `config/settings.yaml` | Defaults: model, frames, frame width, context size, thinking; Gemini thinking level and prices |
| `answer_keys/` | Expected answers per clip, for `score.py` (`gold_ratatouille.yaml` is Claude's, not yet checked) |
| `test_llm_entities.py` | Tests of the parts that need no model (run by `make test`) |
| `logs/` | Earlier run logs and hand-marked outputs, and the first Argon tests (`argon_app_ratatouille.md`) |

To change the prompt, edit `config/prompt_goal.yaml` or `config/output_format.yaml` and give it a new version (each file
says how); no code changes. Code from before this layout (`try_qwen.py`, `try_qwen_video.py`,
`try_variants.py`) is in commit `53cdfd9`, the last commit before this layout (`git show 53cdfd9:notebooks/llm_entities/try_variants.py`).

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

## Gemini (gemini-4-argon)

Paid, and the run prints what it cost. Estimate for the Ratatouille minute: roughly $0.30-1.00 with thinking.

1. Turn on billing in [AI Studio](https://aistudio.google.com/billing) (Argon has no free tier) and make a key
   at [API keys](https://aistudio.google.com/api-keys).
2. `export GEMINI_API_KEY="..."` (WSL or Linux; add it to `~/.bashrc` to keep it). In native Windows
   PowerShell: `setx GEMINI_API_KEY "..."`, then open a new terminal; WSL doesn't see keys set this way.
   Never commit the key. The Gemini path needs no GPU, only Python and ffmpeg.
3. `pip install -e ".[gemini]"` from the repository root.
4. `python3 run.py clip.mp4 --transcript transcript.json --model gemini-4-argon`. To check the code first,
   `--model gemini-3.8-flash` works on the free tier, where Google may use the data for training, so use
   only clips you may share.

The prompt, frames and answer checks are the same as for Qwen. The messages every call of a video shares are
sent once, as a starting interaction (the model replies "ready"), and each call continues from it with only
its own message, so Google can cache the shared part. `--think` uses `thinking_level` from `settings.yaml`
(high); `--no-think` uses low, since Gemini can't switch thinking off. The saved run has a `usage` entry per
sentence and in total: interaction ids, token counts and cost. Google stores the interactions for 55 days
(7 can be set in AI Studio); with the ids you can look them up there or delete them.
Not yet run against the real API: the first run is the real test.

## Running

```bash
cd notebooks/llm_entities
python3 run.py clip.mp4                                  # transcribes with faster-whisper
python3 run.py clip.mp4 --transcript transcript.json     # skip transcription
python3 run.py clip.mp4 --out runs/clip_think.json       # default: runs/<video>_<date>_<time>.json
python3 run.py clip.mp4 --no-think                       # much faster, worse on hard cases
python3 run.py clip.mp4 --frames 0                       # text only
python3 run.py clip.mp4 --things runs/earlier.json       # reuse an earlier run's things list
python3 run.py clip.mp4 --keep-frames frames/            # save the frames the model saw
python3 score.py answer_keys/gold_ratatouille.yaml runs/*.json       # add -v for per-sentence detail
```

A transcript file is a list of `{"start", "end", "text"}` segments (seconds), optionally with
`"words": [{"start", "end", "word"}]`, or a JSON object with such a list under `"transcript"`.
On the HPC, `run.sbatch` should call `python3 run.py ...` (there is no text-only script any more).

Ollama takes images, not video files; passing a whole video so the model samples it itself needs vLLM
(Qwen3.5 accepts video there), which is worth setting up only if frames per sentence aren't enough.

## If it is slow

- `ollama ps` while it runs: `PROCESSOR` should say `100% GPU`. `100% CPU` means the GPU isn't used
  (check `nvidia-smi` in WSL; update the NVIDIA driver on Windows, then `wsl --shutdown`). A CPU/GPU split
  means the model doesn't fit: lower `--ctx` or use `--model qwen3.5:4b`.
- Thinking is most of the time (about 85 s per sentence on the Ratatouille minute). `--no-think` for quick checks.
- The first call loads the model (10-30 s); later calls are quick while Ollama keeps it loaded.

## What we've learnt so far

| Date | Model | Prompt | Finding |
|---|---|---|---|
| 2026-10-07 | qwen3.5:9b (Ollama) | v1: field meanings only in the schema | Visibility mostly right (elsewhere, idiom, hypothetical, negated, presentative). "The dog catching a squirrel" wrongly called *generic*. `search_for`, `evaluated`, `attention_cue` nonsense: the model doesn't see field descriptions inside the schema. Phrases lost "the", "no". |
| 2026-10-07 | qwen3.5:9b, `--think` | v1 | 900-3,300 words of reasoning per sentence (very slow) and the same mistakes. Thinking off from then on (turned back on for goal-v4, see 2026-10-16). |
| 2026-10-07 | qwen3.5:9b | v2: every field explained in the instructions, cue before decision, one worked example | Not run yet. |
| 2026-10-12 | qwen3.5:9b | video-v1: v2 + 3 frames per sentence (768 px), transcript from faster-whisper small.en | `car_cup_keys`: all 7 mentions right from the words and from the pictures, and the two agree everywhere (mug, car, keys yes; "My phone … in the other room" no / elsewhere, and no phone in the frames). "it" resolved to "this little car". The frames improved the search text ("blue toy car" for "this little car"). Listed "those" in "those are my keys" as a separate mention (search "unknown"). ~2.5-3 s per sentence after a 13 s first call (model loading). Sentence starts 0.00 / 2.64 / 4.74 / 6.50 / 8.28 s. Too easy to show what frames add: the narration was written to match the picture. |
| 2026-10-12 | qwen3.5:9b | video-v1, same settings | `doll_school` (two children, one doll, several camera cuts): right: "my new doll", "her", "She" (via Sparkle), "let me see **that**" → doll (pointing word resolved with the frames), "her hair", "comb **it**" → hair; search text improved from the frames ("doll with pink hair and sparkly dress"). Wrong: "Sparkle" (the doll's name) listed as a separate, invisible thing; "Does **she** fly too?" → the star (the doll was mentioned 3 sentences earlier, outside the 2-sentence context); a "she" invented in a sentence without one; `visible_now: no` with `cue: none` twice (breaks the rules); search "hair" for the doll's hair (SAM would also find the children's hair). "me"/"you" (the two speakers) not listed. |
| 2026-10-13/14 | qwen3.5:9b | goal-v1 to goal-v4 (`--prompt goal`): first a things list per video, then per sentence the things to look at | Marked by hand in `logs/outputs_analysis.md`. |
| 2026-10-16/17 | qwen3.5:9b | goal-v4 against two other prompts (`try_variants.py`, now removed), Ratatouille minute, scored with `score.py` | goal-v4 with thinking did best: main object right in 16 of 16 sentences, 1 wrong entry (12 of 16 and 11 wrong without thinking), about 85 s per sentence. Text only (`--frames 0`): 12 of 16, so frames are needed for every sentence. Several samples per sentence with a vote: not worth 2.4 times the run time. Logs in `logs/output_logs_try_variants.md`. |
| 2026-10-20 | Gemini 4 Argon, by hand in the Gemini app | Argon prompt v1: goal-v4 rewritten for the whole video (sent with its sound, no transcript), plus a time, box and outline per object | Main object right in 15 of the 16 sentences scored for Qwen above (16 of 17 with the last one, which faster-whisper joins to the one before); still puts the fingers in "cut my finger". Words and sentence times match faster-whisper. Boxes and outlines: 20 of 48 on the object, 21 rough, 7 in the wrong spot, likely taken from a frame 1-2 s away. A second run at reasoning level medium was no better (13 of 16; 12 of 39 boxes on the object). A third at thinking level high was the best: 15 of 16, any object found 40 of 41 (Qwen 37), 22 of 49 boxes on the object. Log in `logs/argon_app_ratatouille.md`. |

## Habits

- Change one thing at a time and rerun the same sentences.
- Runs aren't exactly repeatable (thinking samples), so a difference of one or two sentences between runs is
  not a real difference.
- Keep worked examples different from test sentences.
- Record the model tag and ID (`ollama list`) with every result; Ollama's download is a compressed
  (quantised) version of the model, fine for development.

## Next

1. Prompt changes still to decide, each as a new prompt version: a field with the exact words of each entry,
   and a rule that imagined or hypothetical mentions ("I'd rather ... than cut my finger") are not things to
   look at.
2. Run on more clips (car_cup_keys, doll_school, one from another kind of video): one clip can't tell
   prompts apart.
3. When it settles and grounding works: the code to `src/sgroi/importance/ours/` on a `feat/` branch.
