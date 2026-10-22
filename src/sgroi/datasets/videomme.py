"""Video-MME (https://huggingface.co/datasets/lmms-lab/Video-MME): 900 YouTube
videos, 300 each short (< 2 min), medium (4-15 min) and long (30-60 min),
in 6 domains and 30 sub-categories. Academic use only; don't redistribute.

The videos ship inside 20 zips of ~5 GB. Only the chosen videos are read out
of them (ranged HTTP reads), never a whole zip. Needs `pip install -e .[videomme]`
and internet.
"""

import json
import os
import shutil
import zipfile

REPO = "lmms-lab/Video-MME"
PARQUET = "videomme/test-00000-of-00001.parquet"


def load_index(cache_dir):
    """One entry per video: id (YouTube ID), number ("001"), duration, domain,
    sub_category, url, and the zip and file inside it that hold the video.
    Built once from Hugging Face, then read from <cache_dir>/index.json."""
    path = os.path.join(cache_dir, "index.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem, hf_hub_download

    videos = {}
    for r in pq.read_table(hf_hub_download(REPO, PARQUET, repo_type="dataset")).to_pylist():
        videos.setdefault(r["videoID"], {
            "id": r["videoID"], "number": r["video_id"], "duration": r["duration"],
            "domain": r["domain"], "sub_category": r["sub_category"], "url": r["url"]})
    fs = HfFileSystem()
    zips = sorted(p for p in fs.ls(f"datasets/{REPO}", detail=False) if p.endswith(".zip")
                  and os.path.basename(p).startswith("videos_chunked_"))
    for zpath in zips:
        with fs.open(zpath, "rb", block_size=1 << 20) as f:
            for info in zipfile.ZipFile(f).infolist():
                vid = os.path.splitext(os.path.basename(info.filename))[0]
                if vid in videos:
                    videos[vid].update(zip=os.path.basename(zpath), member=info.filename,
                                       bytes=info.file_size)
    index = sorted(videos.values(), key=lambda v: v["number"])
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    return index


def select(index, duration=None, domain=None, sub_category=None):
    """Videos matching every filter given (case-insensitive)."""
    def ok(value, wanted):
        return wanted is None or value.lower() == wanted.lower()
    return [v for v in index if "zip" in v and ok(v["duration"], duration)
            and ok(v["domain"], domain) and ok(v["sub_category"], sub_category)]


def find(index, key):
    """The video whose number ("1", "001") or YouTube ID is `key`."""
    for v in index:
        if key == v["id"] or (key.isdigit() and int(key) == int(v["number"])):
            return v
    raise KeyError(f"no Video-MME video with number or ID '{key}'")


def name(video):
    """Folder and file name used in data/raw/: videomme_001."""
    return f"videomme_{video['number']}"


def target_path(video, raw_dir):
    return os.path.join(raw_dir, name(video), name(video) + ".mp4")


def copy_member(zip_file, member, dest):
    """Copy one file out of an open zip to `dest`, via a .part file so an
    interrupted copy never looks finished."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with zipfile.ZipFile(zip_file).open(member) as src, open(tmp, "wb") as out:
        shutil.copyfileobj(src, out, 8 << 20)
    os.replace(tmp, dest)


def download(video, raw_dir):
    """Download the video to data/raw/<name>/<name>.mp4 unless it is already
    there. Returns (path, True if downloaded now)."""
    dest = target_path(video, raw_dir)
    if os.path.isfile(dest):
        return dest, False
    if "zip" not in video:
        raise ValueError(f"Video-MME video {video['number']} is in no zip on Hugging Face")
    from huggingface_hub import HfFileSystem

    with HfFileSystem().open(f"datasets/{REPO}/{video['zip']}", "rb", block_size=8 << 20) as f:
        copy_member(f, video["member"], dest)
    return dest, True
