# Speech-guided ROI video encoding

Research code for improving viewers' quality of experience at a **fixed bitrate**: find what is important
in a video from its **audio** (what is said, and salient sounds), locate it in the frames, and give those
regions more bits while the rest of the frame gets fewer.

```
audio ──► importance source ──► importance maps S(x,y,t) ──► QP offset maps ──► x265 ──► encoded video
          (speech pipeline,                                   (16x16 blocks,      (2-pass ABR,
           saliency baselines, ...)                            per frame)          matched bitrate)
                                                                                        │
                                              quality inside vs outside the ROI ◄───────┘
```

The research design is in [docs/design.md](docs/design.md); where the project stands is in
[docs/PROJECT_STATE.md](docs/PROJECT_STATE.md).

## Repository layout

```
src/encoder/            C encoder: x265 with per-frame, per-block QP offset maps
src/sgroi/              Python package
  importance/             sources of importance maps (one interface for all methods)
    baselines/              comparison methods (dummy box; later ViNet, AViNet, noun extraction)
    controls.py             sanity checks (all-zero importance)
  maps/                   importance -> QP offsets
  encode/                 encoder wrapper, bitrate matching
  evaluation/             region metrics (PSNR/SSIM inside/outside the ROI)
  runner/                 experiment runner and run records
  viewing/                viewable videos: MP4s, side-by-side comparisons, export
  io/  cli/  utils/
configs/                reusable config blocks: encoder/, qpmap/, metrics/, viewing/, paths/, clips/
experiments/<id>/       one folder per experiment: README.md (question, conclusion) + config.yaml
tests/                  unit/, integration/, fixtures/
data/                   README + manifests in git; the data itself is not (see data/README.md)
docs/                   design.md, PROJECT_STATE.md, DECISIONS.md, encoder.md
runs/  cache/  models/  generated, not in git
```

Folders such as `analysis/`, `notebooks/`, `references/` and `papers/` are added when first needed.

## Setup

**Ubuntu / Debian (also WSL2 on Windows):**

```bash
sudo apt install build-essential pkg-config libx265-dev ffmpeg python3-venv
git clone https://github.com/shakirmahmood/speech-guided-roi-encoding.git
cd speech-guided-roi-encoding
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make                      # builds bin/roi_x265_encode
make test                 # unit tests + a ~1 min end-to-end smoke test
```

Activate the environment (`source .venv/bin/activate`) in every new terminal.

**macOS:** `brew install x265 ffmpeg pkg-config`, then the same steps from `git clone` on.

**Windows:** use WSL2 (recommended: `wsl --install`, then follow the Ubuntu steps inside your Linux home
folder, not under `/mnt/c`), or natively with MSYS2: see [docs/encoder.md](docs/encoder.md#windows).

## Running experiments

```bash
sgroi-run experiments/e001_box_sanity                                # as configured
sgroi-run experiments/e001_box_sanity --clip data/raw/my_clip.mp4    # on your own video
sgroi-run experiments/e001_box_sanity --set bitrates_kbps=[300,600] --set encoder.preset=slow
sgroi-run experiments/e001_box_sanity --show-config                  # print resolved settings only
sgroi-run experiments/e001_box_sanity --debug                        # also save QP map overlays
sgroi-run experiments/e001_box_sanity --clip data/raw/my_clip.mp4 --set qpmap.k=14 --set qpmap.qp_min=-12 #increase the importance
```

Each run creates a new folder `runs/<experiment>/<UTC time>_<commit>[_dirty]/` (and a `latest` link)
containing the resolved config, git commit and any uncommitted changes, inputs with checksums, every
command run, logs, QP maps, encodes, `metrics.csv` and a readable `summary.md`.

### Watching the results

Every run also makes videos to watch, for each clip and bitrate:

- `encode.mp4` for every encode (baseline and conditions), with the clip's audio;
- `compare_<condition>.mp4`: baseline on the left, the condition on the right, each labelled with its
  achieved bitrate, and the condition's ROI (from its QP map) outlined on both;
- `compare_all.mp4`: baseline and all conditions in one grid, when there are two or more.

Under WSL they are also copied to your Windows **Videos** folder, in `Videos\sgroi\<experiment>\<run>\`, named
`<clip>_<kbps>k_<name>.mp4`. Settings (outline or tint, colour, audio, quality, export on or off) are in
`configs/viewing/default.yaml`. To remake the videos of an existing run, e.g. with a different style:

```bash
sgroi-view runs/e001_box_sanity/latest
sgroi-view runs/e001_box_sanity/latest --style tint --color yellow
sgroi-view runs/e001_box_sanity/latest --export-dir ~/Videos/roi      # also outside WSL
```

The viewing videos are re-encoded with x264 at visually lossless quality, so they play in any player;
all measurements use the original `.hevc` encodes.

**A new experiment** is a new folder in `experiments/` with a `config.yaml` (copy e001's) and a `README.md`
stating the question; record the conclusion there after running it. **A new method** is a new importance
source in `src/sgroi/importance/` (see the interface in its `__init__.py`); experiments refer to it by name.

Lower-level tools: `sgroi-qpmap`, `sgroi-encode-matched`, `sgroi-metrics`, `sgroi-view` (`--help` on each).

## Documentation

| File | Purpose |
|---|---|
| [docs/design.md](docs/design.md) | Research design: goal, method, evaluation plan, open questions |
| [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) | Current progress, next steps, blockers |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Engineering and process decisions, with reasons |
| [docs/encoder.md](docs/encoder.md) | How the ROI encoder works; x265 settings that matter; file formats |
| [experiments/README.md](experiments/README.md) | Index of experiments and their outcomes |
| [data/README.md](data/README.md) | Where data lives and how it's tracked |
| [AGENTS.md](AGENTS.md) | Rules for coding assistants working in this repository |
