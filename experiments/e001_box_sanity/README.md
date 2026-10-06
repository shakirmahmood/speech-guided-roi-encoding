# e001: box sanity check

**Status:** done on the synthetic clip; to repeat on real clips.

## Question

Does the ROI encoding setup work as intended?

1. An all-zero QP map produces a bitstream bit-identical to the baseline (the map path alone changes nothing).
2. A dummy box (centre, 1/16 of the frame) gains quality inside the box at the same bitrate as the baseline.

## How

`sgroi-run experiments/e001_box_sanity` (add `--clip <video>` for a real clip). Synthetic 720p clip,
5 s, x265 `medium`, 2-pass ABR; conditions `zeros` (same target bitrate) and `box` (matched to the
baseline's achieved bitrate within 0.5%); default QP map settings (k = 6).

## Results

Before the repository existed, the same procedure ran as `scripts/run_dummy_test.py` on the owner's
machine (WSL2, Ubuntu's x265), 2026-10-05:

| Target | Baseline kbps | Box kbps (vs baseline) | ΔPSNR box | ΔPSNR background | ΔPSNR full | Zero map |
|---|---|---|---|---|---|---|
| 1000 kbps | 978.9 | 977.4 (−0.15%) | **+1.65 dB** | −0.02 dB | +0.04 dB | bit-identical |
| 250 kbps | 260.9 | 259.1 (−0.66%, outside 0.5%) | **+1.18 dB** | −0.03 dB | +0.05 dB | bit-identical |

New runs go to `runs/e001_box_sanity/`.

## Conclusion

- **Verdict:** supported.
- **Evidence:** zero map bit-identical; box +1.65 dB (1000 kbps) and +1.18 dB (250 kbps) at matched bitrate.
- **Caveats:** synthetic clip, whose flat background costs almost nothing, so the background loss is
  unrealistically small. At 250 kbps the match missed the 0.5% tolerance (x265 takes whole kbps), but in the
  ROI's disfavour, so the comparison is conservative. The gain shrank at the lower bitrate with the same k.
- **Decision:** the setup is validated for building the baselines. Repeat on real clips across bitrates
  and check whether k should depend on bitrate.
