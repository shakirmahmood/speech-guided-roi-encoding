"""Running an experiment: experiments/<id>/config.yaml -> one run folder.

For every clip and every bitrate:
  1. encode a baseline (no QP map) at the target bitrate;
  2. for each condition: importance source -> QP map -> encode, by default
     matched to the baseline's achieved bitrate;
  3. measure PSNR/SSIM inside each condition's ROI, in the background and
     full frame, for the condition and for the baseline on the same ROI.

Run folder layout (in addition to the record files, see record.py):
  clips/<clip>/maps/<condition>.qpm               QP map (shared by all bitrates)
  clips/<clip>/<kbps>k/<condition>/encode.hevc    encoded video
  clips/<clip>/<kbps>k/<condition>/summary.json   achieved bitrate, matching attempts
  debug/                                          with --debug: QP map overlays
  metrics.csv                                     one row per clip x bitrate x condition
  summary.md                                      readable results table
and the viewable videos (see sgroi/viewing/viewables.py):
  clips/<clip>/<kbps>k/<condition>/encode.mp4     each encode as an MP4
  clips/<clip>/<kbps>k/compare_<condition>.mp4    baseline | condition, ROI drawn
  clips/<clip>/<kbps>k/compare_all.mp4            all conditions (2 or more)
  viewing.json                                    videos made and where they were copied
"""

import csv
import filecmp
import math
import os
import traceback

import numpy as np

from ..config import compose, resolve_paths
from ..encode import encode, encode_matched
from ..evaluation import evaluate
from ..importance import get_source
from ..io.qpm import describe, roi_block_mask, write_qpm
from ..maps.conversion import DEFAULTS as QP_DEFAULTS
from ..maps.conversion import blocks_to_qp
from ..utils.repo import repo_root
from ..viewing import make_viewables, viewing_config
from .clips import prepare_clip
from .record import RunRecord

ENCODER_DEFAULTS = {"preset": "medium", "passes": 2, "x265_params": "log-level=warning",
                    "match": {"tolerance": 0.5, "max_iter": 4}}
METRICS_DEFAULTS = {"roi_threshold": -0.5, "ssim": True}

CSV_FIELDS = [
    "clip", "target_kbps", "condition", "kbps", "baseline_kbps", "bitrate_diff_percent", "match_ok",
    "roi_fraction", "roi_frames", "frames",
    "roi_psnr", "baseline_roi_psnr", "delta_roi_psnr",
    "bg_psnr", "baseline_bg_psnr", "delta_bg_psnr",
    "full_psnr", "baseline_full_psnr", "delta_full_psnr",
    "roi_ssim", "baseline_roi_ssim", "bg_ssim", "baseline_bg_ssim", "full_ssim", "baseline_full_ssim",
    "identical_to_baseline",
]


def load_experiment(exp_dir, overrides=(), clip_override=None):
    """Resolve an experiment's config. Returns (root, experiment id, cfg, blocks used)."""
    exp_dir = os.path.abspath(exp_dir)
    config_path = os.path.join(exp_dir, "config.yaml")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"no config.yaml in {exp_dir}")
    root = repo_root(exp_dir) or repo_root()
    if not root:
        raise RuntimeError("cannot find the repository root (pyproject.toml + configs/)")
    cfg, blocks = compose(config_path, os.path.join(root, "configs"), overrides)
    if clip_override:
        path = os.path.abspath(clip_override)
        spec = dict(cfg.get("clip_defaults") or {})
        spec.update(id=os.path.splitext(os.path.basename(path))[0], source=path)
        cfg["clips"] = [spec]
    else:
        defaults = cfg.get("clip_defaults") or {}
        cfg["clips"] = [{**defaults, **c} for c in (cfg.get("clips") or [])]
    if not cfg["clips"]:
        raise ValueError("experiment has no clips")
    if not cfg.get("bitrates_kbps"):
        raise ValueError("experiment needs bitrates_kbps")
    cfg["encoder"] = {**ENCODER_DEFAULTS, **(cfg.get("encoder") or {})}
    cfg["encoder"]["match"] = {**ENCODER_DEFAULTS["match"], **(cfg["encoder"].get("match") or {})}
    cfg["qpmap"] = {**QP_DEFAULTS, **(cfg.get("qpmap") or {})}
    cfg["metrics"] = {**METRICS_DEFAULTS, **(cfg.get("metrics") or {})}
    cfg["viewing"] = viewing_config(cfg)
    cfg["conditions"] = cfg.get("conditions") or {}
    for name in cfg["conditions"]:
        if name == "baseline":
            raise ValueError("'baseline' is always encoded; don't list it as a condition")
    return root, os.path.basename(exp_dir), cfg, blocks


def _fmt(v, digits=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    return f"{v:+.{digits}f}" if isinstance(v, float) else str(v)


def _debug_overlay(clip, offsets, path, frame):
    """Grey luma with a red tint where the map gives extra bits (stronger = more)."""
    from PIL import Image

    from ..io.y4m import Y4M

    y = next(f for i, f in enumerate(Y4M(clip.path).luma_frames()) if i == frame)
    tint = np.kron(np.clip(-offsets[frame] / 8.0, 0, 1), np.ones((16, 16)))[:clip.height, :clip.width]
    rgb = np.stack([y, y, y], axis=-1).astype(np.float32)
    rgb[..., 0] = rgb[..., 0] * (1 - tint) + 255 * tint
    rgb[..., 1:] *= (1 - 0.6 * tint[..., None])
    Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).save(path)


def run_experiment(exp_dir, overrides=(), clip_override=None, runs_root=None, debug=False, argv=None):
    root, exp_id, cfg, blocks = load_experiment(exp_dir, overrides, clip_override)
    paths = resolve_paths(cfg.get("paths"), root)
    cfg["paths"] = paths
    rec = RunRecord(runs_root or paths["runs_root"], exp_id, cfg, root, argv or [], blocks)
    log = rec.log.info
    log(f"run {rec.meta['run_id']} -> {rec.dir}")
    if rec.git.get("dirty"):
        log("note: uncommitted changes; saved to source.patch")
    try:
        rows = _execute(cfg, paths, rec, debug, log)
        _write_outputs(rec, cfg, rows)
        _viewables(rec, cfg, log)
        rec.finish("succeeded")
        print(f"\nresults: {rec.path('summary.md')}")
        return rec.dir
    except BaseException as e:
        rec.log.error(traceback.format_exc())
        rec.finish("failed" if not isinstance(e, KeyboardInterrupt) else "interrupted",
                   error=f"{type(e).__name__}: {e}")
        raise


def _execute(cfg, paths, rec, debug, log):
    enc, qp_cfg, met = cfg["encoder"], cfg["qpmap"], cfg["metrics"]
    enc_kwargs = dict(preset=enc["preset"], passes=enc["passes"], x265_params=enc["x265_params"])
    rows = []
    for spec in cfg["clips"]:
        clip, input_rec = prepare_clip(spec, paths["data_root"], paths["cache_root"], log=log)
        rec.add_input(input_rec)
        log(f"clip {clip.id}: {clip.width}x{clip.height}, {clip.frames} frames @ {clip.fps:.3f} fps")
        clip_dir = rec.path("clips", clip.id)
        os.makedirs(os.path.join(clip_dir, "maps"), exist_ok=True)

        # importance -> QP map, once per condition (independent of bitrate)
        maps, masks = {}, {}
        for name, cond in cfg["conditions"].items():
            imp = dict(cond.get("importance") or {})
            source = get_source(imp.pop("type"))
            blocks = source(clip, **imp)
            offsets = blocks_to_qp(blocks, **{**qp_cfg, **(cond.get("qpmap") or {})})
            path = os.path.join(clip_dir, "maps", f"{name}.qpm")
            write_qpm(path, offsets)
            maps[name] = path
            masks[name] = roi_block_mask(offsets, met["roi_threshold"])
            log(f"  map {name}: {describe(offsets)}")
            if debug:
                os.makedirs(rec.path("debug"), exist_ok=True)
                for fr in sorted({0, clip.frames // 2, clip.frames - 1}):
                    _debug_overlay(clip, offsets, rec.path("debug", f"{clip.id}_{name}_f{fr:05d}.png"), fr)

        for kbps in cfg["bitrates_kbps"]:
            kdir = os.path.join(clip_dir, f"{kbps}k")
            log(f"clip {clip.id} @ {kbps} kbps")
            bdir = os.path.join(kdir, "baseline")
            os.makedirs(bdir, exist_ok=True)
            base = encode(clip.path, os.path.join(bdir, "encode.hevc"), kbps,
                          os.path.join(bdir, "summary.json"), **enc_kwargs)
            rec.set_tool("x265", base.get("x265_version"))
            log(f"  baseline: {base['kbps']:.2f} kbps (target {kbps})")

            results = {}
            for name, cond in cfg["conditions"].items():
                cdir = os.path.join(kdir, name)
                os.makedirs(cdir, exist_ok=True)
                out, summ = os.path.join(cdir, "encode.hevc"), os.path.join(cdir, "summary.json")
                if cond.get("match_bitrate", True):
                    log(f"  {name}: matching baseline bitrate")
                    s = encode_matched(clip.path, out, base["kbps"], summ, qpmap=maps[name],
                                       tolerance=enc["match"]["tolerance"], max_iter=enc["match"]["max_iter"],
                                       log=log, **enc_kwargs)
                else:
                    s = encode(clip.path, out, kbps, summ, qpmap=maps[name], **enc_kwargs)
                    s["match_ok"] = None
                identical = None
                if cond.get("expect_identical_to_baseline"):
                    identical = filecmp.cmp(out, os.path.join(bdir, "encode.hevc"), shallow=False)
                    log(f"  {name}: {'bit-identical to baseline (OK)' if identical else 'DIFFERS from baseline'}")
                results[name] = (s, identical)

            log("  measuring quality")
            base_m = evaluate(clip.path, os.path.join(bdir, "encode.hevc"), masks, ssim=met["ssim"])
            rows.append(_row(clip, kbps, "baseline", base, base, base_m["full"], None, base_m["full"], None, None))
            for name, (s, identical) in results.items():
                m = evaluate(clip.path, os.path.join(kdir, name, "encode.hevc"), {name: masks[name]},
                             ssim=met["ssim"])
                rows.append(_row(clip, kbps, name, s, base, m["full"], m[name], base_m["full"],
                                 base_m[name], identical))
    return rows


def _viewables(rec, cfg, log):
    """Viewable videos. A failure here is reported but doesn't fail the run:
    the results are already complete, and `sgroi-view` can redo this step."""
    if not cfg["viewing"]["enabled"]:
        return
    log("making viewable videos")
    try:
        info = make_viewables(rec.dir, cfg, log=log)
        rec.set_meta("viewing", {k: info.get(k) for k in ("status", "export_dir")})
    except Exception as e:  # noqa: BLE001
        rec.log.warning(f"viewable videos failed: {type(e).__name__}: {e}\n"
                        f"  results are unaffected; retry with: sgroi-view {rec.dir}")
        rec.set_meta("viewing", {"status": "failed", "error": f"{type(e).__name__}: {e}"})


def _row(clip, kbps, name, s, base, full, region, base_full, base_region, identical):
    r = {"clip": clip.id, "target_kbps": kbps, "condition": name, "kbps": s["kbps"],
         "baseline_kbps": base["kbps"], "bitrate_diff_percent": 100 * (s["kbps"] / base["kbps"] - 1),
         "match_ok": s.get("match_ok"), "frames": full["frames"],
         "full_psnr": full["psnr"], "baseline_full_psnr": base_full["psnr"],
         "delta_full_psnr": full["psnr"] - base_full["psnr"],
         "full_ssim": full["ssim"], "baseline_full_ssim": base_full["ssim"],
         "identical_to_baseline": identical}
    if region is not None:
        r.update(roi_fraction=region["roi_fraction"], roi_frames=region["roi_frames"],
                 roi_psnr=region["roi_psnr"], baseline_roi_psnr=base_region["roi_psnr"],
                 delta_roi_psnr=region["roi_psnr"] - base_region["roi_psnr"],
                 bg_psnr=region["bg_psnr"], baseline_bg_psnr=base_region["bg_psnr"],
                 delta_bg_psnr=region["bg_psnr"] - base_region["bg_psnr"],
                 roi_ssim=region["roi_ssim"], baseline_roi_ssim=base_region["roi_ssim"],
                 bg_ssim=region["bg_ssim"], baseline_bg_ssim=base_region["bg_ssim"])
    return r


def _write_outputs(rec, cfg, rows):
    with open(rec.path("metrics.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    lines = [f"# {rec.meta['experiment']}: run {rec.meta['run_id']}", ""]
    if cfg.get("description"):
        lines += [str(cfg["description"]).strip(), ""]
    git = rec.meta["git"]
    if git.get("available"):
        lines += [f"Commit `{git['commit'][:10]}` on `{git['branch']}`"
                  + (" **with uncommitted changes** (see source.patch)" if git["dirty"] else ""), ""]
    lines += [f"Encoder: preset `{cfg['encoder']['preset']}`, {cfg['encoder']['passes']}-pass ABR; "
              f"bitrate match tolerance {cfg['encoder']['match']['tolerance']}%. "
              f"ROI = blocks with QP offset < {cfg['metrics']['roi_threshold']}.", ""]
    for clip in dict.fromkeys(r["clip"] for r in rows):
        for kbps in dict.fromkeys(r["target_kbps"] for r in rows if r["clip"] == clip):
            sub = [r for r in rows if r["clip"] == clip and r["target_kbps"] == kbps]
            base = sub[0]
            lines += [f"## {clip} @ {kbps} kbps", "",
                      f"Baseline: {base['kbps']:.1f} kbps, full-frame PSNR {base['full_psnr']:.2f} dB", "",
                      "| condition | kbps | vs baseline | ROI area | ΔPSNR ROI | ΔPSNR background | ΔPSNR full | check |",
                      "|---|---|---|---|---|---|---|---|"]
            for r in sub[1:]:
                checks = []
                if r.get("match_ok") is False:
                    checks.append("bitrate outside tolerance")
                if r.get("identical_to_baseline") is True:
                    checks.append("identical to baseline ✓")
                elif r.get("identical_to_baseline") is False:
                    checks.append("NOT identical to baseline ✗")
                area = r.get("roi_fraction")
                lines.append(
                    f"| {r['condition']} | {r['kbps']:.1f} | {r['bitrate_diff_percent']:+.2f}% | "
                    f"{'–' if area is None else f'{100 * area:.1f}%'} | {_fmt(r.get('delta_roi_psnr'))} dB | "
                    f"{_fmt(r.get('delta_bg_psnr'))} dB | {_fmt(r.get('delta_full_psnr'))} dB | "
                    f"{'; '.join(checks) or 'ok'} |")
            lines.append("")
    with open(rec.path("summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n" + "\n".join(lines))
