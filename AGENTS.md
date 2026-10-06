# Rules for coding assistants

Read these before changing anything. They are short on purpose.

## Before starting

1. Read `docs/PROJECT_STATE.md` (where things stand) and skim `docs/DECISIONS.md`.
2. For research questions, `docs/design.md` is the reference.
3. Discuss and agree on a plan before large changes; the project owner prefers planning first.

## Documents

- **Do not edit `docs/design.md` unless the owner explicitly asks.** Design changes are discussed first.
- Update `docs/PROJECT_STATE.md` when a piece of work finishes or the plan changes (state, not a diary).
- Add an entry to `docs/DECISIONS.md` for any lasting engineering or process decision.
- After running an experiment, record question / result / conclusion in its `README.md` and in
  `experiments/README.md`.

## Code

- Implementation lives in `src/`. Experiments are configuration (`experiments/<id>/config.yaml`), not code
  copies. The package must not import experiment-specific code.
- New methods are importance sources with the interface in `src/sgroi/importance/__init__.py`.
  Comparison methods go in `importance/baselines/`, the proposed method in `importance/ours/`.
- Settings belong in `configs/` or an experiment config, not hard-coded.
- Run `make test` before committing; add tests for new behaviour.
- Never commit data, encodes, model weights, `runs/` or `cache/`.

## Encoder constraints (x265 `quantOffsets`; see docs/encoder.md)

- Adaptive quantization must stay on (presets veryfast or slower; not ultrafast/superfast, not tune grain).
- Both passes of a 2-pass encode must get identical QP maps.
- In an ROI encode every frame gets a map (zeros where nothing matters).
- Compare conditions at matched bitrate (`encode_matched`), and report achieved bitrates.

## Git

- `main` always works. New work on `feat/<name>` branches; exploratory ideas on `exp/<name>` branches.
- Results reported in a paper or thesis come from clean commits, tagged (e.g. `results-<venue>-<n>`).
