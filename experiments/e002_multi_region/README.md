# e002: several objects, timing, weights and budget rules

**Status:** ready to run (pipeline checked at reduced settings; no results yet).

## Question

With several annotated objects in a clip, one of them moving, at the baseline's bitrate:

1. **Timing:** does boosting only the object being talked about ("active from its mention until the next
   mention") give it more quality while it is mentioned than boosting every object all the time?
   What does each cost the background?
2. **Weights:** do different weights (car 1.0, mug 0.6, keys 0.3) give gains in the same order?
3. **Budget rule:** under `relative`, does the weakly weighted object lose quality in a frame full of
   important objects, and does `background_pays` prevent that?
4. **Placement:** does boosting the same total area in the wrong place (`wrong_place`, bookshelf) lower the
   objects' quality, i.e. are the gains due to where the bits go?

## Clip

`car_cup_keys` (`data/raw/car_cup_keys.mp4`, AI-generated, 1920x1080, 30 fps, 10 s, ~1.3 Mbps; see
`data/manifests/clips.csv`): a red mug, a blue toy car and keys on a table, static camera. The car is still
until ~2.0 s, then rolls to the right and away until ~6.6 s. Object boxes:
`data/annotations/car_cup_keys.yaml` (measured by hand; the car has keyframes).

Speech (from silence detection): 0.00–1.66, 2.48–3.89, 4.78–5.60, 6.51–7.53, 8.29–9.57 s. The narrator
mentions the mug, then the car, then the keys, and last a phone that is not in the picture. Activity times
in `timed` start at the beginning of the sentence that mentions the object (not word-level timestamps):

| object | active (s) |
|---|---|
| mug | 0.00–2.48 |
| car | 2.48–6.51 |
| keys | 6.51–8.29 |
| (phone, not visible) | 8.29–end: nothing boosted, all-zero map |

## How

```bash
sgroi-preview-regions experiments/e002_multi_region --condition timed   # check boxes and timing first
sgroi-run experiments/e002_multi_region
```

Native 1920x1080, whole clip, x265 `medium`, 2-pass ABR at 600 and 300 kbps (the source itself is only
~1.3 Mbps), every condition matched to the baseline's achieved bitrate; default QP map settings (k = 6).

| condition | importance | budget |
|---|---|---|
| `timed` | each object only while it is talked about, weight 1 | relative |
| `all_on` | all three objects, whole clip, weight 1 | relative |
| `all_on_weighted` | car 1.0, mug 0.6, keys 0.3, whole clip | relative |
| `all_on_weighted_bg` | same weights | background_pays |
| `wrong_place` | box on the bookshelf, ~7% of the frame (about the objects' total area) | relative |

Look at: `summary.md` (ROI / background / full frame, and the per-object table), `metrics_regions.csv`
(`scope: active` = frames in which a condition boosts the object), and `compare_all.mp4`.

### Pipeline check (not a result)

Before committing, the experiment was run once at reduced settings to test the pipeline
(640x360, `veryfast`, 150 kbps, this repository's sandbox with x265 3.4). Numbers are only indicative:
`timed` gained +2.2 to +2.8 dB on each object while it was active, `all_on` +1.6 to +1.8 dB; with
`relative` weighting the keys (0.3) gained nothing (−0.01 dB) and with `background_pays` +0.11 dB;
`wrong_place` lost 0.6–0.9 dB on the objects. Two matches missed the 0.5% tolerance (whole-kbps limit at a
very low bitrate).

## Results

To be filled after the run (record the run folder, commit, and both bitrates).

## Conclusion

- **Verdict:**
- **Evidence:**
- **Caveats:** one AI-generated clip with a smooth, low-detail picture; hand-measured boxes; sentence-level
  timing.
- **Decision:**
