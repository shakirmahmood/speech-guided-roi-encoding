# Data

The data itself is **not** in git (too large, often licensed). Only this README and `manifests/` are.
Git-ignored does not mean untracked: every clip used in an experiment is listed in a manifest with its
checksum, and the data is backed up.

## Layout (on disk, not in git)

```
data/
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

## Backup

Back up `data/raw/`, `data/external/` and `runs/` (an external drive or cloud storage). Losing `runs/` means
losing the evidence behind results; `cache/` can always be regenerated.
