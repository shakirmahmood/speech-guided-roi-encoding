# Data

The data itself is **not** in git (too large, often licensed). Only this README, `manifests/` and
`annotations/` (small hand-made text files) are.
Git-ignored does not mean untracked: every clip used in an experiment is listed in a manifest with its
checksum, and the data is backed up.

## Layout

```
data/
├── manifests/    in git: one line per clip (source, licence, checksum)
├── annotations/  in git: where the objects are in a clip, <clip>.yaml (see below)
├── raw/          your original clips, never modified
├── external/     third-party datasets (eye-tracking: DIEM, AVAD, Coutrot, ...)
├── interim/      intermediate data you create by hand (e.g. annotations in progress)
└── processed/    final prepared datasets
```

Prepared encoder inputs (trimmed, scaled Y4M) are generated automatically into `cache/clips/` by the
experiment runner; you don't create them yourself.

## Adding a clip

1. Put the file in `data/raw/` (or point `paths.data_root` elsewhere, e.g. an external drive).
2. Add a line to `manifests/clips.csv`: id, path relative to `data/`, where it came from, licence,
   sha256 (`sha256sum data/raw/my_clip.mp4`), and notes.
3. Use it in an experiment via a clip list in `configs/clips/` or `--clip data/raw/my_clip.mp4`.

Each run also records the checksum of every clip it used in its `inputs.json`.

## Object annotations

For experiments with several objects (`regions` conditions), a clip's objects are described in
`annotations/<clip>.yaml`: an id and a box per object, with keyframes for moving objects. Only the geometry
goes there; when an object matters and how much is set by each experiment's conditions. Times are seconds of
the original video, so the same file works however the clip is trimmed. The format is described in
`src/sgroi/io/annotations.py`; `annotations/car_cup_keys.yaml` is an example.

1. Write the file (boxes as fractions of the frame, or pixels with `frame_size: [W, H]`) and set
   `source_sha256` to the video's checksum; runs warn when the annotations were made for a different file.
2. Add `annotations: annotations/<clip>.yaml` to the clip's entry in `configs/clips/`. The path is looked up
   in `data_root` first, then in the repository's `data/` folder, so it is found even when `data_root`
   points to another drive.
3. Check it on the video: `sgroi-preview-regions experiments/<experiment>`.

The runs record each annotation file's path and checksum in `inputs.json`.

## Backup

Back up `data/raw/`, `data/external/` and `runs/` (an external drive or cloud storage). Losing `runs/` means
losing the evidence behind results; `cache/` can always be regenerated.
