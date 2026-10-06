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

### 010 — The encoder consumes only importance maps; times in source-video seconds (2026-10-06)
**Decision:** the encoding component knows nothing about objects, words or coreference: it takes an
importance map per frame (block or pixel values in 0–1) and turns it into QP offsets. Object identity,
mentions and their resolution ("the dog" = "it") belong to the upstream components. Any times given to the
encoder side (active intervals, annotation keyframes) are seconds of the **source video**; trimming a clip is
handled on the encoder side, which maps each prepared frame to its source time (`start + i / fps`).
**Why:** the project is split into four components with different owners; a narrow interface (importance per
frame) lets each be developed and tested alone, and lets any importance source (saliency, speech, oracle) be
compared through the same encoder. Source-video time is the one clock every component shares.
**Rejected:** object-level input to the encoder (would tie it to one upstream representation); times relative
to the trimmed clip (every trim would invalidate the upstream output).

### 011 — Two budget rules for the QP map: `relative` (default) and `background_pays` (2026-10-06)
**Decision:** `qpmap.budget` selects how importance becomes offsets. `relative` (unchanged behaviour,
`dQP = −k·(S − mean S)`) stays the default; `background_pays` gives `−k·S` and takes the bits from blocks below
`background_threshold` only, with a uniform payment. Both keep every frame zero-mean.
**Why:** with several objects in a frame, `relative` can give a weakly weighted object a positive offset
(fewer bits than with no map) because it sits below the frame's average importance; `background_pays`
guarantees no important block loses bits. The owner chose to keep both and compare them (e002) rather than
replace the existing rule; keeping `relative` as default keeps earlier results reproducible (bit-identical
maps, checked).
**Rejected:** replacing `relative` outright; a per-object budget (needs object identity in the encoder,
see 010).

### 012 — Object annotations: geometry per clip in git, timing and weights per condition (2026-10-06)
**Decision:** a clip's objects are described once, in `data/annotations/<clip>.yaml` (in git, unlike the
videos): an id and a box per object, static, keyframed (linear interpolation, held outside the keyframes) or a
per-frame track CSV; boxes as fractions of the frame, or pixels with `frame_size`; `source_sha256` ties the
file to its video. When each object matters (`active` intervals) and how much (`weight`) is set per condition
of the `regions` importance source; overlapping objects take the highest value. Per-object metrics are
measured inside the annotated boxes, independently of the QP map, so all conditions (including `box` and
controls) are measured on the same pixels.
**Why:** geometry is a property of the clip and is shared by every experiment; timing and weights are what
experiments vary. Fractions survive scaling the clip. Keyframes are enough for smooth motion and quick to
write by hand; tracks cover trackers' output. A preview command (`sgroi-preview-regions`) shows the boxes and a
condition's timing on the video, with audio, before anything is encoded.
**Rejected:** boxes inside experiment configs (duplicated across experiments); per-frame masks for Phase 1
(not needed for boxes; masks come with the `file` importance source in Phase 2); measuring per-object quality
on the QP map's ROI (differs between conditions).
