import os
import tempfile
import unittest

import yaml

from sgroi.config import compose, deep_merge, parse_override, resolve_paths


class TestConfig(unittest.TestCase):
    def test_deep_merge(self):
        a = {"encoder": {"preset": "medium", "match": {"tolerance": 0.5}}, "x": 1}
        b = {"encoder": {"match": {"tolerance": 1.0}}, "x": [2]}
        m = deep_merge(a, b)
        self.assertEqual(m, {"encoder": {"preset": "medium", "match": {"tolerance": 1.0}}, "x": [2]})
        self.assertEqual(a["encoder"]["match"]["tolerance"], 0.5, "inputs untouched")

    def test_overrides_are_yaml(self):
        self.assertEqual(parse_override("bitrates_kbps=[300, 600]"), ("bitrates_kbps", [300, 600]))
        self.assertEqual(parse_override("encoder.preset=slow"), ("encoder.preset", "slow"))
        self.assertEqual(parse_override("metrics.ssim=false"), ("metrics.ssim", False))
        with self.assertRaises(ValueError):
            parse_override("no-equals-sign")

    def test_compose(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "configs", "encoder"))
            with open(os.path.join(d, "configs", "encoder", "base.yaml"), "w") as f:
                yaml.safe_dump({"preset": "medium", "passes": 2}, f)
            exp = os.path.join(d, "config.yaml")
            with open(exp, "w") as f:
                yaml.safe_dump({"defaults": {"encoder": "base"}, "encoder": {"passes": 1}, "bitrates_kbps": [1]}, f)
            cfg, used = compose(exp, os.path.join(d, "configs"), ["encoder.preset=slow"])
        self.assertEqual(cfg["encoder"], {"preset": "slow", "passes": 1})
        self.assertEqual(used, [os.path.join("configs", "encoder", "base.yaml")])

    def test_missing_block(self):
        with tempfile.TemporaryDirectory() as d:
            exp = os.path.join(d, "config.yaml")
            with open(exp, "w") as f:
                yaml.safe_dump({"defaults": {"encoder": "nope"}}, f)
            with self.assertRaises(FileNotFoundError):
                compose(exp, os.path.join(d, "configs"))

    def test_resolve_paths(self):
        p = resolve_paths({"data_root": "data", "runs_root": "/abs/runs"}, "/repo")
        self.assertEqual(p["data_root"], os.path.normpath("/repo/data"))
        self.assertEqual(p["runs_root"], "/abs/runs")
        self.assertEqual(p["cache_root"], os.path.join("/repo", "cache"))


if __name__ == "__main__":
    unittest.main()
