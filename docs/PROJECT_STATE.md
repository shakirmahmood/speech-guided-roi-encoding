# Project state

**Last updated:** 2026-10-06

## Done

- **Research design** drafted: [design.md](design.md) v0.3 (speech + non-speech audio in scope; taxonomy
  of linguistic clues in §5.2.1).
- **ROI encoding setup** (step 1 of the plan) built and validated:
  - C encoder on libx265 with per-frame 16x16 QP offsets, 2-pass ABR, matched baseline.
  - Importance → QP map conversion, bitrate matching, region metrics.
  - Validated on a synthetic clip on the owner's machine (WSL2): all-zero map bit-identical to baseline;
    centre box +1.65 dB PSNR at 1000 kbps and +1.18 dB at 250 kbps, at matched bitrate
    (see [experiment e001](../experiments/e001_box_sanity/README.md)).
- **Repository** set up with the agreed structure, a generic experiment runner with full run records,
  and tests.
- **Viewable outputs** after every run (`src/sgroi/viewing/`, `configs/viewing/default.yaml`): each encode
  as `encode.mp4` with the clip's audio, `compare_<condition>.mp4` (baseline | condition, labelled, ROI
  outlined from the QP map), `compare_all.mp4` grid, copied to the Windows Videos folder under WSL;
  `sgroi-view` remakes them for any run. Defaults chosen for the open questions: export automatic under WSL,
  outline (tint available), audio included. See decision 009.
- **Multi-object ROI encoding, phase 1** (branch `feat/multi-region`), decisions 010–012:
  - object annotations per clip (`data/annotations/<clip>.yaml`, in git): static boxes, keyframes for
    moving objects, or track CSVs; times in source-video seconds;
  - `regions` importance source: per condition, which objects, when (`active` intervals) and how much
    (`weight`);
  - QP map budget rules `relative` (default, unchanged) and `background_pays`;
  - per-object PSNR/SSIM inside each annotated box (`metrics_regions.csv`, table in `summary.md`);
  - `sgroi-preview-regions`: boxes, a condition's timing and the boosted area drawn on the clip, with audio;
  - test clip `car_cup_keys` (AI-generated: mug, moving toy car, keys; narrated) annotated, and experiment
    [e002](../experiments/e002_multi_region/README.md) configured; pipeline checked at reduced settings.

## Next

1. **Run e002** on the owner's machine (full resolution, 600 and 300 kbps), watch `compare_all.mp4`, record
   the results in its README.
2. **Multi-object phase 2 — the interface for the colleagues' components:** a `file` importance source that
   reads per-frame importance maps produced upstream (masks, not just boxes), a validator, and a format spec
   (`docs/importance_map_format.md`) to hand to the colleagues.
3. **Multi-object phase 3:** label each object's outline in the comparison videos (now only the QP-map ROI
   is drawn).
4. Run e001 on real clips at several bitrates and watch the comparison videos.
5. **Baseline B2/B1:** AViNet / ViNet saliency maps as importance sources.
6. **Baseline B3:** simple speech pipeline (WhisperX → noun chunks → SAM 3).
7. Then the proposed method: LLM interpretation of linguistic clues (design §5.2.1).

## Open questions / blockers

- GPU availability on the owner's machine (decides how to set up AViNet, WhisperX, SAM 3).
- Test clips: need 5–10 short clips whose speech refers to on-screen objects (one so far: `car_cup_keys`,
  AI-generated, smooth picture; real footage still needed).
- Which budget rule to use by default once e002 has run.
- Where data and runs are backed up.
- Where paper writing lives (this repo vs Overleaf); `references/` and `papers/` not created yet.
- Encoder tested with x265 3.4; Ubuntu 24.04 ships 3.5 (works on the owner's machine); MSYS2 ships 4.3 (untested).
- Windows export tested with a simulated folder only; to confirm on the owner's WSL machine.
