# The ROI encoder

`src/encoder/roi_x265_encode.c` encodes an 8-bit 4:2:0 Y4M file with libx265, giving each 16x16 block of
each frame a QP offset from a `.qpm` map. Negative offsets = finer quantization = more bits. Without a map
it produces the baseline with otherwise identical settings.

```
bin/roi_x265_encode -i in.y4m -o out.hevc --bitrate KBPS [--qpmap map.qpm] [--passes 2]
                    [--preset medium] [--x265-params k=v:k=v] [--summary out.json]
```

Both passes of 2-pass ABR run in one invocation, with the same map. The summary JSON records achieved
bitrate, frames, settings, map statistics and the x265 version. In experiments you don't call it directly:
`sgroi-run` does, through `sgroi.encode`.

## Settings that matter

From x265's documentation and source (`x265.h`, `encoder/slicetype.cpp`, `encoder/encoder.cpp`):

- **Adaptive quantization must be on** (`aq-mode` ≥ 1). With `aq-mode=0` x265 silently ignores the offsets;
  the encoder refuses that combination. **The `ultrafast` and `superfast` presets and `--tune grain` turn AQ
  off**: use `veryfast` or slower. `aq-strength=0` (also set by `--tune psnr`) keeps AQ "on" but disables its
  content-based part, so only the map acts; if you use it, use it for the baseline too.
- **`hevc-aq` must be off** (default): it ignores the offsets.
- **`qg-size` is forced to 16**, so QP can change every 16x16 block (x265's default 32 merges neighbours).
- **Identical maps in both passes.** In pass 2 x265 reuses pass-1 data for referenced frames instead of
  re-reading the offsets.
- **Every frame of an ROI encode gets a map** (zeros where nothing matters): x265 recycles frame buffers and
  only allocates offset storage if the first frames had a map.
- **Bitrate matching:** x265 lands a few percent off target and maps shift it; conditions are re-encoded to
  match the baseline's achieved bitrate. x265 takes whole kbps, so very low bitrates may only match to
  about ±0.3–0.7%. Longer clips match more accurately.

## File formats

**`.qpm`** (little-endian): `"QPM1"`, int32 block (16), int32 cols = ⌈W/16⌉, int32 rows = ⌈H/16⌉,
int32 nframes, then float32 offsets `[nframes][rows][cols]`, row-major. Read/write with `sgroi.io.qpm`;
`sgroi-qpmap info map.qpm` prints statistics.

**Importance maps** (for `sgroi-qpmap from-importance`): `.npy` `[frames, height, width]` (float 0–1 or uint8)
or a folder of greyscale PNGs, one per frame, same resolution as the video.

## Importance → QP offsets

`sgroi.maps.blocks_to_qp`, settings in `configs/qpmap/`: block-average importance onto the 16x16 grid;
dilate by `dilate_blocks` and blur with `blur_sigma_blocks` (soft edges, margin for motion); moving average
over `ramp_frames` (quality ramps in just before a region appears); then importance → offsets by one of two
budget rules (`budget`), clamped to `[qp_min, qp_max]`:

- `relative` (default): `dQP = −k·(S − mean(S))`. A small fully important region gets about −k (−6 QP roughly
  doubles a block's bits). In a busy frame, weakly important blocks can fall below the frame's average
  importance and get a positive offset.
- `background_pays`: `dQP = −k·S`, and every background block (importance below `background_threshold`)
  also gets the same positive offset `k·ΣS / N_background`. Important blocks never lose bits; a frame with
  no background left uses `relative` (with a warning).

Either way every frame is zero-mean, so a frame with no importance gets all zeros.

## Metrics

`sgroi.evaluation`: the ROI is the set of blocks with offset below `roi_threshold` (−0.5), upsampled to
pixels; the baseline is measured on the same ROI as each condition. PSNR-Y per frame, averaged; ROI numbers
only over frames where the ROI exists. SSIM-Y: Gaussian-window SSIM map averaged inside / outside the ROI.

**Per object** (clips with an annotation file): PSNR-Y (capped at 100 dB per frame) and SSIM-Y inside each
object's annotated box, frame by frame, for every condition and the baseline. `metrics_regions.csv` gives
the averages over all frames (`scope: all`) and, for `regions` conditions, over the frames in which the
condition boosts the object (`scope: active`).

## Watching encodes

A raw `.hevc` has no timestamps; give the frame rate when wrapping it:

```bash
ffmpeg -framerate 30 -i encode.hevc -c copy -tag:v hvc1 encode.mp4
ffmpeg -framerate 30 -i baseline/encode.hevc -framerate 30 -i box/encode.hevc \
  -filter_complex hstack -c:v libx264 -crf 10 compare.mp4            # side by side
```

(Automating this is planned; see PROJECT_STATE.md.)

## Windows

**WSL2 (recommended):** `wsl --install` in an administrator PowerShell, restart, open Ubuntu, and follow the
Ubuntu setup in the README. Keep the repository and data in your Linux home folder, not under `/mnt/c`
(much faster for large Y4M files); Explorer reaches it at `\\wsl$\Ubuntu\home\<you>`.

**Native with MSYS2 (untested):** in the *MSYS2 UCRT64* terminal:

```bash
pacman -S --needed make mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-pkgconf \
    mingw-w64-ucrt-x86_64-x265 mingw-w64-ucrt-x86_64-ffmpeg mingw-w64-ucrt-x86_64-python \
    mingw-w64-ucrt-x86_64-python-numpy mingw-w64-ucrt-x86_64-python-scipy \
    mingw-w64-ucrt-x86_64-python-pillow mingw-w64-ucrt-x86_64-python-yaml
make STATIC=1          # self-contained bin/roi_x265_encode.exe
```

## Building against x265 elsewhere

```bash
make X265_CFLAGS="-I$HOME/x265/include" X265_LIBS="-L$HOME/x265/lib -lx265"
export LD_LIBRARY_PATH=$HOME/x265/lib        # macOS: DYLD_LIBRARY_PATH
```

Building x265 from source: install `nasm` first (without it x265 has no SIMD and is several times slower),
then `git clone https://bitbucket.org/multicoreware/x265_git.git`, `cd x265_git/build/linux`,
`cmake ../../source -DCMAKE_INSTALL_PREFIX=$HOME/x265 && make -j && make install`.
