from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..media_probe import probe

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".avif"}
GIF_EXT = {".gif"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv"}
VECTOR_EXT = {".svg", ".eps", ".ai"}


def classify(name: str) -> str:
    """"raster" (has a real pixel resolution, readable via ffprobe) |
    "vector" (an image format with no fixed resolution — SVG and friends;
    still a picture, so it's kept, just always ranked last) | "unsupported"
    (no visual resolution at all, e.g. .txt/.mp3 — dropped entirely)."""
    ext = Path(name).suffix.lower()
    if ext in VECTOR_EXT:
        return "vector"
    if ext in IMAGE_EXT or ext in GIF_EXT or ext in VIDEO_EXT:
        return "raster"
    return "unsupported"


class _ProgressJob(Protocol):
    total: int
    done: int
    progress: float


@dataclass
class _Ranked:
    path: Path
    area: int
    size: int
    is_square: bool


async def rank_files(
    paths: list[Path], job: _ProgressJob, move_square_to_end: bool = True
) -> tuple[list[Path], list[Path]]:
    """Sort by resolution descending, file size as the tiebreak. Vector
    images (no fixed resolution but still pictures) are kept and appended
    after, in their original order. Anything with no visual resolution at
    all — a non-media file, or a raster file ffprobe couldn't read — is
    dropped. Perfectly square rasters (width == height — usually icons,
    avatars, thumbnails rather than footage) are, when `move_square_to_end`
    is set, pushed after every non-square one, still ahead of vectors."""
    job.total = len(paths)
    ranked: list[_Ranked] = []
    vector: list[Path] = []
    for i, path in enumerate(paths):
        kind = classify(path.name)
        if kind == "vector":
            vector.append(path)
        elif kind == "raster":
            info = await probe(path)
            w, h = info["width"], info["height"]
            if w and h:
                ranked.append(_Ranked(path, w * h, path.stat().st_size, w == h))
        job.done = i + 1
        job.progress = job.done / job.total if job.total else 0.0
    ranked.sort(key=lambda r: (-r.area, -r.size))
    if move_square_to_end:
        ranked.sort(key=lambda r: r.is_square)  # stable: keeps the ranking above within each group
    return [r.path for r in ranked], vector
