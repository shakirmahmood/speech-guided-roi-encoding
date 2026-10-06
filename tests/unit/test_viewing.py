import os
import unittest
from unittest import mock

import numpy as np

from sgroi.viewing import VIEWING_DEFAULTS, viewing_config
from sgroi.viewing import export
from sgroi.viewing.draw import COLORS_YUV, BlockMapper, Label, RoiPainter, grid_layout, outline
from sgroi.viewing.video import AudioSource


class TestLayout(unittest.TestCase):
    def test_one_and_two_panels_unscaled(self):
        self.assertEqual(grid_layout(1, 1280, 720, 2560), (1, 1, 1280, 720))
        self.assertEqual(grid_layout(2, 1280, 720, 2560), (2, 1, 1280, 720))

    def test_wide_rows_are_scaled_to_max_width(self):
        cols, rows, pw, ph = grid_layout(3, 1280, 720, 2560)
        self.assertEqual((cols, rows), (3, 1))
        self.assertLessEqual(cols * pw, 2560)
        self.assertEqual((pw % 2, ph % 2), (0, 0))

    def test_many_panels_form_a_grid(self):
        self.assertEqual(grid_layout(4, 1280, 720, 2560)[:2], (2, 2))
        self.assertEqual(grid_layout(5, 1280, 720, 2560)[:2], (3, 2))

    def test_no_panels(self):
        with self.assertRaises(ValueError):
            grid_layout(0, 1280, 720)


class TestDrawing(unittest.TestCase):
    def test_outline_is_a_ring(self):
        m = np.zeros((20, 20), bool)
        m[5:15, 5:15] = True
        e = outline(m, thickness=2)
        self.assertTrue(e[5, 10] and e[6, 10])          # border, 2 px thick
        self.assertFalse(e[7, 10] or e[10, 10])         # inside stays clear
        self.assertFalse(e[4, 10])                      # outside stays clear
        self.assertFalse(outline(np.zeros((8, 8), bool)).any())

    def test_block_mapper_scales(self):
        blocks = np.array([[1, 2], [3, 4]])
        px = BlockMapper(32, 32, 16, 16)(blocks)        # half-size panel
        self.assertEqual(px.shape, (16, 16))
        self.assertEqual((px[0, 0], px[0, 15], px[15, 0], px[15, 15]), (1, 2, 3, 4))

    def _planes(self, w=64, h=64, value=100):
        return (np.full((h, w), value, np.uint8), np.full((h // 2, w // 2), 128, np.uint8),
                np.full((h // 2, w // 2), 128, np.uint8))

    def test_outline_painted_only_where_roi_is(self):
        off = np.zeros((2, 4, 4), np.float32)
        off[0, 1:3, 1:3] = -5                           # ROI in frame 0 only
        p = RoiPainter(off, 64, 64, 64, 64, style="outline", color="red")
        y, u, v = self._planes()
        p.paint(y, u, v, 0)
        cy = COLORS_YUV["red"][0]
        self.assertEqual(y[16, 30], cy)                 # ROI border (blocks 1-2 = px 16-47)
        self.assertEqual(y[32, 32], 100)                # ROI inside untouched
        self.assertEqual(y[5, 5], 100)                  # background untouched
        y, u, v = self._planes()
        p.paint(y, u, v, 1)
        self.assertTrue(np.all(y == 100))               # no ROI, nothing drawn

    def test_tint_changes_roi_only(self):
        off = np.zeros((1, 4, 4), np.float32)
        off[0, 0, 0] = -8
        y, u, v = self._planes()
        RoiPainter(off, 64, 64, 64, 64, style="tint").paint(y, u, v, 0)
        self.assertNotEqual(y[8, 8], 100)
        self.assertEqual(y[40, 40], 100)

    def test_bad_style_or_colour(self):
        off = np.zeros((1, 4, 4), np.float32)
        with self.assertRaises(ValueError):
            RoiPainter(off, 64, 64, 64, 64, style="glow")
        with self.assertRaises(ValueError):
            RoiPainter(off, 64, 64, 64, 64, color="purple-ish")

    def test_label_drawn_in_corner(self):
        y, u, v = self._planes(320, 180)
        Label("box 977.4 kbps", 320, 180).paint(y, u, v)
        self.assertTrue((y[:30, :120] != 100).any())
        self.assertTrue(np.all(y[120:, 200:] == 100))


class TestExport(unittest.TestCase):
    def test_off(self):
        self.assertIsNone(export.resolve_export_dir(False))
        self.assertIsNone(export.resolve_export_dir("false"))

    def test_auto_outside_wsl_does_nothing(self):
        with mock.patch.object(export, "is_wsl", return_value=False):
            self.assertIsNone(export.resolve_export_dir("auto"))

    def test_auto_under_wsl_uses_windows_videos(self):
        with mock.patch.object(export, "is_wsl", return_value=True), \
                mock.patch.object(export, "windows_videos_dir", return_value="/mnt/c/Users/me/Videos"):
            self.assertEqual(export.resolve_export_dir("auto"), "/mnt/c/Users/me/Videos/sgroi")

    def test_auto_under_wsl_without_videos_folder(self):
        with mock.patch.object(export, "is_wsl", return_value=True), \
                mock.patch.object(export, "windows_videos_dir", return_value=None):
            self.assertIsNone(export.resolve_export_dir("auto"))

    def test_explicit_dir_and_forced_export(self):
        with mock.patch.object(export, "is_wsl", return_value=False):
            self.assertEqual(export.resolve_export_dir(True, "/tmp/views"), "/tmp/views")
            self.assertEqual(export.resolve_export_dir(True),
                             os.path.join(os.path.expanduser("~"), "Videos", "sgroi"))

    def test_bad_setting(self):
        with self.assertRaises(ValueError):
            export.resolve_export_dir("sometimes")

    def test_names_and_display(self):
        self.assertEqual(export.export_name("my_clip", "600k", "compare_box"), "my_clip_600k_compare_box.mp4")
        with mock.patch.object(export, "is_wsl", return_value=True):
            self.assertEqual(export.display_path("/mnt/c/Users/me/Videos"), "C:\\Users\\me\\Videos")


class TestConfig(unittest.TestCase):
    def test_defaults_and_overrides(self):
        self.assertEqual(viewing_config({}), VIEWING_DEFAULTS)
        v = viewing_config({"viewing": {"roi_style": "tint", "export": False}})
        self.assertEqual((v["roi_style"], v["export"], v["compare"]), ("tint", False, True))

    def test_audio_trim_arguments(self):
        self.assertEqual(AudioSource("a.mp4", 12.5, 5).input_args(), ["-ss", "12.5", "-t", "5", "-i", "a.mp4"])
        self.assertEqual(AudioSource("a.mp4").input_args(), ["-i", "a.mp4"])


if __name__ == "__main__":
    unittest.main()
