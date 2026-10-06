"""Multi-object ROI: annotation files, the `regions` importance source and the
two budget rules of the QP map conversion."""

import os
import shutil
import tempfile
import textwrap
import unittest

import numpy as np

from sgroi.importance import ClipInfo, get_source
from sgroi.importance.baselines.regions import box_coverage, object_plan
from sgroi.io.annotations import (AnnotationError, active_frames, clip_times, load_annotations, parse_active,
                                  pixel_boxes)
from sgroi.maps.conversion import block_average_frame, blocks_to_qp

NO_SMOOTHING = dict(dilate_blocks=0, blur_sigma_blocks=0, ramp_frames=1)

ANNOTATIONS = """
clip: test
objects:
  still:
    box: [0.25, 0.25, 0.25, 0.25]
  mover:
    label: moving thing
    keyframes:
      - {t: 1.0, box: [0.0, 0.5, 0.25, 0.25]}
      - {t: 3.0, box: [0.5, 0.5, 0.25, 0.25]}
"""


class Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sgroi_ann_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, text, name="ann.yaml"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(text))
        return path

    def clip(self, ann=None, w=640, h=360, frames=120, fps=30.0, start=0.0):
        return ClipInfo(id="test", path="", width=w, height=h, frames=frames, fps=fps,
                        source={"start": start} if start else {}, annotations=ann)


class TestAnnotationFile(Tmp):
    def test_static_and_keyframed_objects(self):
        ann = load_annotations(self.write(ANNOTATIONS))
        self.assertEqual(list(ann.objects), ["still", "mover"])
        self.assertEqual(ann.objects["mover"].label, "moving thing")
        self.assertEqual(ann.objects["still"].label, "still")
        m = ann.objects["mover"].boxes_at([0.0, 1.0, 2.0, 3.0, 9.0])
        np.testing.assert_allclose(m[:, 0], [0.0, 0.0, 0.25, 0.5, 0.5])   # held, interpolated, held
        np.testing.assert_allclose(m[:, 1], 0.5)
        s = ann.objects["still"].boxes_at([0.0, 5.0])
        np.testing.assert_allclose(s, [[0.25, 0.25, 0.25, 0.25]] * 2)

    def test_pixel_boxes_with_frame_size(self):
        a = load_annotations(self.write(ANNOTATIONS))
        b = load_annotations(self.write("""
            frame_size: [1920, 1080]
            objects:
              still: {box: [480, 270, 480, 270]}
            """, "px.yaml"))
        np.testing.assert_allclose(b.objects["still"].boxes, a.objects["still"].boxes)

    def test_track_csv_relative_to_file(self):
        with open(os.path.join(self.dir, "ball.csv"), "w", encoding="utf-8") as f:
            f.write("t,x,y,w,h\n0,0.1,0.1,0.2,0.2\n1,0.3,0.1,0.2,0.2\n")
        ann = load_annotations(self.write("objects:\n  ball: {track: ball.csv}\n"))
        np.testing.assert_allclose(ann.objects["ball"].boxes_at([0.5])[0], [0.2, 0.1, 0.2, 0.2])

    def test_errors_name_the_problem(self):
        cases = {
            "objects: {}\n": "objects",
            "objects:\n  a: {box: [0.5, 0.5, 0.6, 0.1]}\n": "outside the frame",
            "objects:\n  a: {box: [100, 100, 50, 50]}\n": "frame_size",
            "objects:\n  a: {box: [0.1, 0.1, 0, 0.1]}\n": "positive",
            "objects:\n  a: {box: [0.1, 0.1, 0.1]}\n": "[x, y, w, h]",
            "objects:\n  a: {box: [0, 0, 0.1, 0.1], keyframes: []}\n": "exactly one",
            "objects:\n  a:\n    keyframes:\n      - {t: 2, box: [0, 0, 0.1, 0.1]}\n"
            "      - {t: 1, box: [0, 0, 0.1, 0.1]}\n": "increasing",
            "objects:\n  a: {track: missing.csv}\n": "not found",
        }
        for text, words in cases.items():
            with self.subTest(text=text), self.assertRaises(AnnotationError) as cm:
                load_annotations(self.write(text, "bad.yaml"))
            self.assertIn(words, str(cm.exception))

    def test_times_are_source_seconds(self):
        clip = self.clip(frames=4, fps=2.0, start=10.0)          # a clip trimmed to start at 10 s
        np.testing.assert_allclose(clip_times(clip), [10.0, 10.5, 11.0, 11.5])
        np.testing.assert_array_equal(active_frames(clip, [(10.5, 11.5)]), [False, True, True, False])
        np.testing.assert_array_equal(active_frames(clip, None), [True] * 4)

    def test_parse_active(self):
        self.assertIsNone(parse_active(None))
        self.assertIsNone(parse_active("all"))
        self.assertEqual(parse_active([1, 2]), [(1.0, 2.0)])
        self.assertEqual(parse_active([[0, 1], [2, 3.5]]), [(0.0, 1.0), (2.0, 3.5)])
        for bad in ([[2, 1]], "sometimes", [[1, 2, 3]], []):
            with self.subTest(bad=bad), self.assertRaises(AnnotationError):
                parse_active(bad)

    def test_pixel_boxes_follow_the_object(self):
        ann = load_annotations(self.write(ANNOTATIONS))
        clip = self.clip(frames=91)                               # 0-3 s at 30 fps
        b = pixel_boxes(ann.objects["mover"], clip)
        self.assertEqual(b.shape, (91, 4))
        np.testing.assert_array_equal(b[0], [0, 180, 160, 270])
        np.testing.assert_array_equal(b[60], [160, 180, 320, 270])
        np.testing.assert_array_equal(b[90], [320, 180, 480, 270])


class TestRegionsSource(Tmp):
    def test_box_coverage_matches_pixel_block_average(self):
        rng = np.random.default_rng(0)
        for w, h in ((640, 360), (650, 370)):                    # incl. partial edge blocks
            for _ in range(20):
                x0, x1 = sorted(rng.integers(0, w + 1, 2))
                y0, y1 = sorted(rng.integers(0, h + 1, 2))
                if rng.random() < 0.3:
                    x1, y1 = w, h                                 # touching the right/bottom edge
                if x1 <= x0 or y1 <= y0:
                    continue
                mask = np.zeros((h, w), np.float32)
                mask[y0:y1, x0:x1] = 1
                np.testing.assert_allclose(box_coverage(x0, y0, x1, y1, w, h), block_average_frame(mask),
                                           atol=1e-6, err_msg=f"{w}x{h} box {x0},{y0},{x1},{y1}")

    def test_single_static_object_equals_box_source(self):
        clip = self.clip(self.write(ANNOTATIONS), frames=10)
        a = get_source("regions")(clip, objects=["still"])
        b = get_source("box")(clip, box=[0.25, 0.25, 0.25, 0.25])
        np.testing.assert_allclose(a, b, atol=1e-6)

    def test_default_is_every_object_always(self):
        clip = self.clip(self.write(ANNOTATIONS), frames=10)
        b = get_source("regions")(clip)
        self.assertEqual(b.shape, (10, 23, 40))
        self.assertEqual(b[:, 8, 12].min(), 1.0)                  # inside "still"
        self.assertEqual(b[:, 13, 2].min(), 1.0)                  # inside "mover" (held before 1 s)
        self.assertEqual(b[:, 2, 30].max(), 0.0)                  # nothing there

    def test_timing_and_weights(self):
        clip = self.clip(self.write(ANNOTATIONS), frames=60)      # 0-2 s
        b = get_source("regions")(clip, objects={"still": {"active": [[0.5, 1.0]], "weight": 0.4},
                                                  "mover": {"weight": 0.0}})
        self.assertEqual(b[14, 8, 12], 0.0)                       # 0.47 s: not yet
        self.assertAlmostEqual(float(b[15, 8, 12]), 0.4, places=6)
        self.assertAlmostEqual(float(b[29, 8, 12]), 0.4, places=6)
        self.assertEqual(b[30, 8, 12], 0.0)                       # 1.0 s: interval end is exclusive
        self.assertEqual(b[:, 13, 2].max(), 0.0)                  # weight 0: never boosted

    def test_overlap_takes_the_highest(self):
        path = self.write("""
            objects:
              big:   {box: [0.0, 0.0, 0.5, 0.5]}
              small: {box: [0.1, 0.1, 0.1, 0.1]}
            """)
        clip = self.clip(path, frames=2)
        b = get_source("regions")(clip, objects={"big": {"weight": 0.5}, "small": {"weight": 0.9}})
        self.assertAlmostEqual(float(b[0, 3, 5]), 0.9, places=6)  # inside both
        self.assertAlmostEqual(float(b[0, 1, 1]), 0.5, places=6)  # big only

    def test_object_plan_errors(self):
        path = self.write(ANNOTATIONS)
        clip = self.clip(path)
        for objects, words in (({"cat": {}}, "not in"), ({"still": {"wieght": 1}}, "unknown"),
                               ({"still": {"weight": 2}}, "between 0 and 1"),
                               ({"still": {"active": [[3, 1]]}}, "ends before"), ("still", "mapping")):
            with self.subTest(objects=objects), self.assertRaises(AnnotationError) as cm:
                object_plan(clip, objects)
            self.assertIn(words, str(cm.exception))
        with self.assertRaises(AnnotationError) as cm:
            object_plan(self.clip(None))
        self.assertIn("no annotation file", str(cm.exception))

    def test_never_active_object_warns(self):
        clip = self.clip(self.write(ANNOTATIONS), frames=30)
        with self.assertLogs("sgroi.run", "WARNING") as cm:
            b = get_source("regions")(clip, objects={"still": {"active": [[50, 60]]}})
        self.assertIn("never active", cm.output[0])
        self.assertEqual(b.max(), 0.0)


class TestBudgetRules(unittest.TestCase):
    def busy_frame(self):
        b = np.zeros((1, 10, 10), np.float32)
        b[0, :5, :8] = 1.0                       # 40% of the frame: strong object
        b[0, 6:9, 6:9] = 0.3                     # weak object
        return b

    def test_relative_formula(self):
        b = self.busy_frame()
        q = blocks_to_qp(b, k=6, qp_min=-50, qp_max=50, **NO_SMOOTHING)
        np.testing.assert_allclose(q, -6 * (b - b.mean()), atol=1e-5)
        self.assertGreater(q[0, 7, 7], 0)        # busy frame: the weak object ends up below average

    def test_background_pays(self):
        b = self.busy_frame()
        q = blocks_to_qp(b, k=6, qp_min=-50, qp_max=50, budget="background_pays", **NO_SMOOTHING)
        self.assertAlmostEqual(float(q[0, 0, 0]), -6.0, places=5)   # importance 1 -> -k exactly
        self.assertAlmostEqual(float(q[0, 7, 7]), -1.8, places=5)   # weak object still gains
        bg = q[0][b[0] == 0]
        self.assertTrue(np.all(bg > 0))
        self.assertAlmostEqual(float(bg.std()), 0.0, places=5)      # one uniform payment
        self.assertAlmostEqual(float(q.mean()), 0.0, places=5)      # budget-neutral

    def test_background_pays_without_background_falls_back(self):
        b = np.full((1, 4, 4), 0.5, np.float32)
        b[0, 0, 0] = 1.0
        kw = dict(k=6, qp_min=-50, qp_max=50, **NO_SMOOTHING)
        with self.assertLogs("sgroi.run", "WARNING"):
            q = blocks_to_qp(b, budget="background_pays", **kw)
        np.testing.assert_allclose(q, blocks_to_qp(b, **kw), atol=1e-6)

    def test_both_rules_leave_empty_frames_alone(self):
        for budget in ("relative", "background_pays"):
            q = blocks_to_qp(np.zeros((3, 5, 5)), budget=budget)
            self.assertTrue(np.all(q == 0))
            self.assertFalse(np.any(np.signbit(q)))

    def test_with_smoothing_frames_stay_budget_neutral(self):
        b = np.zeros((20, 23, 40), np.float32)
        b[:, 5:10, 5:12] = 1.0
        b[:, 15:18, 25:30] = 0.3
        q = blocks_to_qp(b, budget="background_pays")
        np.testing.assert_allclose(q.mean(axis=(1, 2)), 0.0, atol=1e-4)
        self.assertLess(q[10, 16, 27], 0)

    def test_unknown_rule(self):
        with self.assertRaises(ValueError):
            blocks_to_qp(np.zeros((1, 2, 2)), budget="everyone_pays")


if __name__ == "__main__":
    unittest.main()
