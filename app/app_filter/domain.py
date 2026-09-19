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
    still a picture, so it's kept) | "unsupported" (no visual resolution at
    all, e.g. .txt/.mp3 — dropped entirely, never offered as a candidate)."""
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
class Candidate:
    rel_path: str  # stable id — the zip-internal path, same across separate runs of the same input
    path: Path  # actual filesystem location for *this* run
    kind: str  # "raster" | "vector"
    width: int
    height: int
    size: int


async def gather_candidates(paths: list[Path], rel_names: list[str], job: _ProgressJob) -> list[Candidate]:
    """Probe every file, drop unsupported ones, sort raster candidates by
    resolution descending (file size as the tiebreak), vector images
    appended after in their original order — a sensible default arrangement
    for a human to then pick from and reorder by hand."""
    job.total = len(paths)
    raster: list[Candidate] = []
    vector: list[Candidate] = []
    for i, (path, rel) in enumerate(zip(paths, rel_names)):
        kind = classify(path.name)
        if kind == "vector":
            vector.append(Candidate(rel, path, "vector", 0, 0, path.stat().st_size))
        elif kind == "raster":
            info = await probe(path)
            w, h = info["width"], info["height"]
            if w and h:
                raster.append(Candidate(rel, path, "raster", w, h, path.stat().st_size))
        job.done = i + 1
        job.progress = job.done / job.total if job.total else 0.0
    raster.sort(key=lambda c: (-(c.width * c.height), -c.size))
    return raster + vector
