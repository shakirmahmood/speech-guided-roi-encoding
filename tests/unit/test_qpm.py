import os
import tempfile
import unittest

import numpy as np

from sgroi.io.qpm import grid_shape, read_qpm, roi_block_mask, write_qpm


class TestQpm(unittest.TestCase):
    def test_round_trip(self):
        offsets = np.random.default_rng(0).normal(size=(5, 68, 120)).astype(np.float32)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.qpm")
            write_qpm(p, offsets)
            back, block = read_qpm(p)
        self.assertEqual(block, 16)
        np.testing.assert_array_equal(back, offsets)

    def test_grid_shape_rounds_up(self):
        self.assertEqual(grid_shape(1920, 1080), (68, 120))
        self.assertEqual(grid_shape(1280, 720), (45, 80))
        self.assertEqual(grid_shape(640, 360), (23, 40))

    def test_rejects_nan(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                write_qpm(os.path.join(d, "m.qpm"), np.full((1, 2, 2), np.nan, np.float32))

    def test_rejects_other_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.qpm")
            with open(p, "wb") as f:
                f.write(b"NOPE" + bytes(16))
            with self.assertRaises(ValueError):
                read_qpm(p)

    def test_roi_mask_threshold(self):
        m = roi_block_mask(np.array([[[-1.0, -0.4, 0.5]]]))
        np.testing.assert_array_equal(m, [[[True, False, False]]])


if __name__ == "__main__":
    unittest.main()
