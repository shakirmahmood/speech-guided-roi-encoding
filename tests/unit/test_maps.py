import unittest

import numpy as np

from sgroi.importance import ClipInfo, get_source
from sgroi.maps.conversion import block_average_frame, blocks_to_qp, importance_to_qp


def clip(w=1280, h=720, frames=60):
    return ClipInfo(id="t", path="", width=w, height=h, frames=frames, fps=30.0)


class TestConversion(unittest.TestCase):
    def test_no_importance_gives_zero_map(self):
        q = blocks_to_qp(np.zeros((10, 45, 80)))
        self.assertTrue(np.all(q == 0))
        self.assertFalse(np.any(np.signbit(q)), "no -0.0 values")

    def test_box_gets_negative_offsets_and_frames_stay_zero_mean(self):
        q = blocks_to_qp(get_source("box")(clip()))
        self.assertLess(q[30, 22, 40], -5.0)            # centre of the box
        self.assertGreater(q[30, 0, 0], 0.0)            # background pays a little
        np.testing.assert_allclose(q.mean(axis=(1, 2)), 0.0, atol=1e-4)

    def test_clamp(self):
        b = np.zeros((1, 10, 10))
        b[0, 5, 5] = 1
        q = blocks_to_qp(b, k=100, qp_min=-8, qp_max=6, dilate_blocks=0, blur_sigma_blocks=0, ramp_frames=1)
        self.assertEqual(q.min(), -8)
        self.assertLessEqual(q.max(), 6)

    def test_ramp_starts_before_region_appears(self):
        b = get_source("box")(clip(), start=20, end=40)
        q = blocks_to_qp(b, ramp_frames=8)
        self.assertEqual(q[10, 22, 40], 0)              # well before
        self.assertLess(q[18, 22, 40], 0)               # quality ramps in before frame 20
        self.assertLess(q[30, 22, 40], q[18, 22, 40])   # full strength inside the interval
        self.assertEqual(q[55, 22, 40], 0)              # well after

    def test_pixel_path_matches_block_path(self):
        pix = np.zeros((20, 720, 1280), np.float32)
        pix[:, 270:450, 480:800] = 1
        a = importance_to_qp(pix)
        b = blocks_to_qp(get_source("box")(clip(frames=20)))
        np.testing.assert_allclose(a, b, atol=1e-5)

    def test_block_average_partial_blocks(self):
        f = np.zeros((32, 32))
        f[0:8, 0:16] = 1                                # half of the top-left block
        self.assertAlmostEqual(block_average_frame(f)[0, 0], 0.5)


class TestSources(unittest.TestCase):
    def test_zeros_shape(self):
        z = get_source("zeros")(clip(640, 360, 7))
        self.assertEqual(z.shape, (7, 23, 40))
        self.assertTrue(np.all(z == 0))

    def test_box_pixels_or_fractions(self):
        a = get_source("box")(clip(), box=[0.375, 0.375, 0.25, 0.25])
        b = get_source("box")(clip(), box="480,270,320,180")
        np.testing.assert_array_equal(a, b)

    def test_unknown_source(self):
        with self.assertRaises(KeyError):
            get_source("does-not-exist")


if __name__ == "__main__":
    unittest.main()
