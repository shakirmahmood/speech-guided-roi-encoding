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
    baseline; the box must gain quality inside the box at a matched bitrate."""

    @classmethod
    def setUpClass(cls):
        from sgroi.runner.experiment import run_experiment
        cls.tmp = tempfile.mkdtemp(prefix="sgroi_test_")
        cls.run_dir = run_experiment(SMOKE, overrides=[f"paths.cache_root={cls.tmp}/cache"],
                                     runs_root=os.path.join(cls.tmp, "runs"), argv=["test"])
        import csv
        with open(os.path.join(cls.run_dir, "metrics.csv"), encoding="utf-8") as f:
            cls.rows = {r["condition"]: r for r in csv.DictReader(f)}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_run_record_complete(self):
        for name in ("resolved_config.yaml", "metadata.json", "inputs.json", "commands.txt",
                     "logs/run.log", "metrics.csv", "summary.md", "clips/smoke/maps/box.qpm",
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


if __name__ == "__main__":
    unittest.main()
