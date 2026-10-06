"""End-to-end smoke tests. They need the built encoder (make) and ffmpeg,
and are skipped otherwise. A small synthetic clip keeps them under a minute or two."""

import json
import os
import shutil
import tempfile
import unittest

from sgroi.encode import EncoderError, find_encoder

HERE = os.path.dirname(os.path.abspath(__file__))
SMOKE = os.path.join(HERE, "..", "fixtures", "experiments", "smoke")


def encoder_available():
    try:
        find_encoder()
    except EncoderError:
        return False
    return shutil.which("ffmpeg") is not None


@unittest.skipUnless(encoder_available(), "encoder not built (run make) or ffmpeg missing")
class TestSmokeExperiment(unittest.TestCase):
    """Runs tests/fixtures/experiments/smoke: zero map must be bit-identical to the
    baseline; the box must gain quality inside the box at a matched bitrate; the
    annotated objects of the `regions` condition must gain while they are boosted."""

    @classmethod
    def setUpClass(cls):
        from sgroi.runner.experiment import run_experiment
        cls.tmp = tempfile.mkdtemp(prefix="sgroi_test_")
        cls.run_dir = run_experiment(SMOKE, overrides=[f"paths.cache_root={cls.tmp}/cache"],
                                     runs_root=os.path.join(cls.tmp, "runs"), argv=["test"])
        with open(os.path.join(cls.run_dir, "viewing.json"), encoding="utf-8") as f:
            cls.viewing = json.load(f)            # as made by the run (sgroi-view test rewrites it)
        import csv
        with open(os.path.join(cls.run_dir, "metrics.csv"), encoding="utf-8") as f:
            cls.rows = {r["condition"]: r for r in csv.DictReader(f)}
        with open(os.path.join(cls.run_dir, "metrics_regions.csv"), encoding="utf-8") as f:
            cls.obj_rows = {(r["condition"], r["object"], r["scope"]): r for r in csv.DictReader(f)}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_run_record_complete(self):
        for name in ("resolved_config.yaml", "metadata.json", "inputs.json", "commands.txt",
                     "logs/run.log", "metrics.csv", "metrics_regions.csv", "summary.md",
                     "clips/smoke/maps/box.qpm", "clips/smoke/maps/regions.qpm",
                     "clips/smoke/300k/baseline/encode.hevc", "clips/smoke/300k/box/summary.json"):
            self.assertTrue(os.path.isfile(os.path.join(self.run_dir, name)), name)
        with open(os.path.join(self.run_dir, "metadata.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["status"], "succeeded")

    def test_zero_map_is_bit_identical(self):
        self.assertEqual(self.rows["zeros"]["identical_to_baseline"], "True")

    def test_box_gains_at_matched_bitrate(self):
        r = self.rows["box"]
        self.assertLess(abs(float(r["bitrate_diff_percent"])), 3.0)
        self.assertGreater(float(r["delta_roi_psnr"]), 0.5)

    def test_regions_gain_where_and_when_boosted(self):
        r = self.rows["regions"]
        self.assertLess(abs(float(r["bitrate_diff_percent"])), 3.0)
        o = self.obj_rows
        self.assertEqual(int(o["regions", "left", "active"]["frames"]), 30)     # [0, 1) s at 30 fps
        self.assertEqual(int(o["regions", "mover", "active"]["frames"]), 60)    # always
        self.assertGreater(float(o["regions", "left", "active"]["delta_psnr"]), 0.5)
        self.assertGreater(float(o["regions", "mover", "all"]["delta_psnr"]), 0.5)
        # boosted for the first half only: the gain over the whole clip is smaller
        self.assertLess(float(o["regions", "left", "all"]["delta_psnr"]),
                        float(o["regions", "left", "active"]["delta_psnr"]))

    def test_per_object_rows_for_every_condition(self):
        o = self.obj_rows
        for cond in ("zeros", "box", "regions"):
            for obj in ("left", "mover"):
                self.assertIn((cond, obj, "all"), o)
        self.assertNotIn(("box", "left", "active"), o)                         # not a regions condition
        self.assertEqual(float(o["zeros", "left", "all"]["delta_psnr"]), 0.0)   # identical encode
        with open(os.path.join(self.run_dir, "summary.md"), encoding="utf-8") as f:
            self.assertIn("| regions | left |", f.read())

    def test_region_preview(self):
        from sgroi.cli.preview import main
        from sgroi.viewing.video import probe
        out = os.path.join(self.tmp, "preview.mp4")
        self.assertEqual(main([SMOKE, "--condition", "regions", "--no-export", "--no-audio", "-o", out,
                               "--set", f"paths.cache_root={self.tmp}/cache"]), 0)
        w, h, frames, _, _ = probe(out)
        self.assertEqual((w, h, frames), (640, 360, 60))
        self.assertEqual(main([SMOKE, "--condition", "nope", "--no-export"]), 1)

    def test_viewable_videos(self):
        from sgroi.viewing.video import probe
        k = os.path.join(self.run_dir, "clips", "smoke", "300k")
        w, h, frames, _, _ = probe(os.path.join(k, "compare_box.mp4"))
        self.assertEqual((w, h, frames), (1280, 360, 60))          # baseline | box, 2 s @ 30 fps
        for cond in ("baseline", "box"):
            self.assertEqual(probe(os.path.join(k, cond, "encode.mp4"))[2], 60)
        self.assertFalse(os.path.exists(os.path.join(k, "zeros", "encode.mp4")))   # identical: skipped
        w, h, frames, _, _ = probe(os.path.join(k, "compare_all.mp4"))
        self.assertEqual((w, h, frames), (1920, 360, 60))          # baseline | box | regions
        self.assertEqual((self.viewing["status"], self.viewing["exported"]), ("ok", []))   # export off in tests
        with open(os.path.join(self.run_dir, "metadata.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["viewing"]["status"], "ok")

    def test_sgroi_view_remakes_and_exports(self):
        from sgroi.cli.view import main
        dest = os.path.join(self.tmp, "exported")
        self.assertEqual(main([self.run_dir, "--style", "tint", "--export-dir", dest]), 0)
        with open(os.path.join(self.run_dir, "viewing.json"), encoding="utf-8") as f:
            info = json.load(f)
        self.assertTrue(info["export_dir"].startswith(dest))
        names = sorted(os.path.basename(p) for p in info["exported"])
        self.assertEqual(names, ["smoke_300k_baseline.mp4", "smoke_300k_box.mp4", "smoke_300k_compare_all.mp4",
                                 "smoke_300k_compare_box.mp4", "smoke_300k_compare_regions.mp4",
                                 "smoke_300k_regions.mp4"])
        for p in info["exported"]:
            self.assertGreater(os.path.getsize(p), 0)

    def test_audio_from_source_clip(self):
        from sgroi.utils import proc
        from sgroi.viewing.video import AudioSource, probe, to_mp4
        src = os.path.join(self.tmp, "with_audio.mp4")
        proc.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
                  "-f", "lavfi", "-i", "sine=frequency=440", "-t", "3", "-c:v", "libx264", "-c:a", "aac",
                  "-shortest", src])
        hevc = os.path.join(self.run_dir, "clips", "smoke", "300k", "baseline", "encode.hevc")
        # audio shorter than the video (1.5 s of 2 s) must not shorten the video
        out = to_mp4(hevc, os.path.join(self.tmp, "a.mp4"), 30, 1, AudioSource(src, 1.5, 1.5), seconds=2.0)
        _, _, frames, duration, has_audio = probe(out)
        self.assertTrue(has_audio)
        self.assertEqual(frames, 60)
        self.assertAlmostEqual(duration, 2.0, delta=0.1)

    def test_mp4_pictures_are_exact_at_crf0(self):
        import hashlib
        import subprocess
        from sgroi.viewing.video import to_mp4
        hevc = os.path.join(self.run_dir, "clips", "smoke", "300k", "box", "encode.hevc")
        out = to_mp4(hevc, os.path.join(self.tmp, "exact.mp4"), 30, 1, crf=0)

        def decoded(path):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "yuv420p",
                                  "-"], stdout=subprocess.PIPE, check=True).stdout
            return len(raw), hashlib.sha256(raw).hexdigest()
        self.assertEqual(decoded(out), decoded(hevc))


if __name__ == "__main__":
    unittest.main()
