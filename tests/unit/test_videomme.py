import io
import json
import os
import tempfile
import unittest
import zipfile

from sgroi.cli import videomme as cli
from sgroi.datasets import videomme

INDEX = [
    {"id": "aaa", "number": "001", "duration": "short", "domain": "Life Record",
     "sub_category": "Cooking", "url": "", "zip": "videos_chunked_01.zip",
     "member": "data/aaa.mp4", "bytes": 3},
    {"id": "bbb", "number": "002", "duration": "long", "domain": "Knowledge",
     "sub_category": "Astronomy", "url": "", "zip": "videos_chunked_02.zip",
     "member": "data/bbb.mp4", "bytes": 3},
]


class TestVideoMME(unittest.TestCase):
    def test_select_and_find(self):
        self.assertEqual([v["id"] for v in videomme.select(INDEX, duration="SHORT")], ["aaa"])
        self.assertEqual([v["id"] for v in videomme.select(INDEX, domain="knowledge")], ["bbb"])
        self.assertEqual(videomme.find(INDEX, "2")["id"], "bbb")
        self.assertEqual(videomme.find(INDEX, "aaa")["number"], "001")
        with self.assertRaises(KeyError):
            videomme.find(INDEX, "999")

    def test_target_path(self):
        self.assertEqual(videomme.target_path(INDEX[0], "raw"),
                         os.path.join("raw", "videomme_001", "videomme_001.mp4"))

    def test_copy_member(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("data/aaa.mp4", b"abc")
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "videomme_001", "videomme_001.mp4")
            videomme.copy_member(buf, "data/aaa.mp4", dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"abc")
            self.assertEqual(os.listdir(os.path.dirname(dest)), ["videomme_001.mp4"])

    def test_existing_video_is_not_downloaded(self):
        with tempfile.TemporaryDirectory() as d:
            dest = videomme.target_path(INDEX[0], d)
            os.makedirs(os.path.dirname(dest))
            open(dest, "wb").close()
            self.assertEqual(videomme.download(INDEX[0], d), (dest, False))

    def test_cli_list_reads_cached_index(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "configs", "paths"))
            open(os.path.join(d, "pyproject.toml"), "w").close()
            with open(os.path.join(d, "configs", "paths", "default.yaml"), "w") as f:
                f.write("data_root: data\ncache_root: cache\n")
            os.makedirs(os.path.join(d, "cache", "videomme"))
            with open(os.path.join(d, "cache", "videomme", "index.json"), "w") as f:
                json.dump(INDEX, f)
            os.environ["SGROI_ROOT"] = d
            try:
                self.assertEqual(cli.main(["--list", "--duration", "short"]), 0)
                self.assertEqual(cli.main(["--list", "--domain", "nothing"]), 1)
                self.assertEqual(cli.main([]), 1)
            finally:
                del os.environ["SGROI_ROOT"]


if __name__ == "__main__":
    unittest.main()
