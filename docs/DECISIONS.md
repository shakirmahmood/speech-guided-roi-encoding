# Decisions

Engineering and process decisions, newest last. Research-design decisions (D1–D5: what importance means,
fixed budget, etc.) are in [design.md](design.md) §3.

Format: what was decided, why, and what was rejected.

---

### 001 — Codec: HEVC with x265 (2026-10-05)
**Decision:** encode with x265. **Why:** HEVC is a credible minimum for video-coding venues; x265 accepts
per-block float QP offsets per frame (`quantOffsets`) and supports 2-pass. **Rejected:** x264 (older codec;
kept as a possible generality check); Kvazaar (1-pass rate control only); SVT-AV1 ROI maps (64x64 blocks only).

### 002 — Rate control: 2-pass ABR, conditions matched to the baseline's achieved bitrate (2026-10-05)
**Why:** CRF/CQP have no bitrate target, so offsets would add bits instead of redistributing them. x265
lands a few percent off target and ROI maps shift it, so each condition is re-encoded until within 0.5% of
the baseline's *achieved* bitrate. x265 takes whole kbps, so low bitrates can't always be matched that
closely; report the achieved bitrates and the direction of any miss.

### 003 — x265 settings required for QP maps (2026-10-05)
AQ on (`aq-mode` ≥ 1), `hevc-aq` off, `qg-size 16`; identical maps in both passes; a map for every frame of
an ROI encode. **Why:** from x265's source: with AQ off or hevc-aq the offsets are ignored; pass 2 reuses
pass-1 data for referenced frames; frame buffers are recycled and only get offset storage if the first
frames had a map. The encoder enforces the first three.

### 004 — Importance → QP conversion order (2026-10-05)
Block average → dilate/blur → temporal ramp → zero-mean and clamp. **Why:** smoothing before the zero-mean
step keeps every frame budget-neutral (design §5.6 listed zero-mean earlier).

### 005 — Repository structure (2026-10-06)
Cookiecutter Data Science-style layout with the src layout for code, one folder per experiment
(`README.md` + `config.yaml`), reusable config blocks in `configs/`, self-describing run folders in
`runs/`, data outside git with manifests. Folders are created when first needed. **Why:** recognisable
standard; every result traceable to code, config and inputs; the src layout avoids importing the
working-tree copy by accident. **Rejected:** flat package at the root; one `run.py` per experiment
(near-duplicate code) in favour of one generic runner.

### 006 — Package name `sgroi`; plain YAML configs (2026-10-06)
**Why:** short import name. Plain YAML with a small composition loader is easy to debug; Hydra can be
adopted later if sweeps get complex.

### 007 — Tests use `unittest` (2026-10-06)
**Why:** runs with no extra dependency; pytest runs the same tests if installed. Integration tests skip
automatically when the encoder isn't built.

### 008 — Development environment: WSL2 on Windows (2026-10-05)
**Why:** everything works as on Linux, and the later GPU stages (WhisperX, SAM 3, AViNet) are Linux-first
and can use an NVIDIA GPU from WSL2. Native Windows via MSYS2 is supported for the encoder but untested.

### 009 — Viewable outputs: re-encoded MP4s, ROI drawn from the QP map, export under WSL (2026-10-06)
**Decision:** every run makes `encode.mp4` per encode, `compare_<condition>.mp4` and (2+ conditions)
`compare_all.mp4`, and copies them to the Windows Videos folder when running under WSL (`export: auto`);
`sgroi-view` remakes them for any run. Settings in `configs/viewing/`. Making them never fails a run.
**Why:**
- *Re-encoded, not stream-copied:* the encoder writes raw HEVC without timestamps. Copying it into MP4 lost
  the last 3 of 150 frames (B-frame reordering), and the clip's audio was dropped. Decoding and re-encoding with
  x264 gives exact frame counts and timing. crf 10 is ~54 dB PSNR against the decoded HEVC (visually
  lossless) and plays in any player; crf 0 is bit-exact (tested) but needs a profile Windows' built-in player
  may not support. Measurements always use the `.hevc`.
- *ROI from the QP map* (blocks below `metrics.roi_threshold`, as in the metrics), not from box
  coordinates: works unchanged for irregular, moving regions from saliency and speech sources.
- *Composited in YUV* with numpy (labels via Pillow's built-in font), not ffmpeg `drawtext`/`xstack`:
  no font or filter dependencies, pixels shown exactly as decoded.
- Owner's open questions resolved with defaults: export automatic under WSL (`export: true/false` to change),
  outline (tint available), audio included (needed later for the speech experiments).
**Rejected:** ffmpeg filter graphs with `drawtext` (font availability varies, especially on WSL/MSYS2);
copying HEVC into MP4 (above).
