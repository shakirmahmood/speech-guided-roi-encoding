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

## Next

1. Run e001 on real clips at several bitrates and look at the side-by-side videos.
2. **Viewable outputs** (planned, not built): MP4 wrapping, side-by-side `compare.mp4` with labels and the
   ROI outlined from the QP map, export to the Windows Videos folder. Open questions:
   automatic export or opt-in flag; outline vs tint; include original audio.
3. **Baseline B2/B1:** AViNet / ViNet saliency maps as importance sources.
4. **Baseline B3:** simple speech pipeline (WhisperX → noun chunks → SAM 3).
5. Then the proposed method: LLM interpretation of linguistic clues (design §5.2.1).

## Open questions / blockers

- GPU availability on the owner's machine (decides how to set up AViNet, WhisperX, SAM 3).
- Test clips: need 5–10 short clips whose speech refers to on-screen objects.
- Where data and runs are backed up.
- Where paper writing lives (this repo vs Overleaf); `references/` and `papers/` not created yet.
- Encoder tested with x265 3.4; Ubuntu 24.04 ships 3.5 (works on the owner's machine); MSYS2 ships 4.3 (untested).
