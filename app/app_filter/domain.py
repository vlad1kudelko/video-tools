from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..media_probe import probe

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".avif"}
GIF_EXT = {".gif"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv"}
VECTOR_EXT = {".svg", ".eps", ".ai"}

ALPHA_PIX_FMTS = {
    "rgba", "bgra", "argb", "abgr", "ya8", "ya16le", "ya16be", "gbrap",
    "yuva420p", "yuva422p", "yuva444p", "rgba64le", "rgba64be",
}

OFF, DEMOTE, EXCLUDE = "выкл", "понизить в выдаче", "полностью исключить"


def classify(name: str) -> str:
    """"image" or "video" (both have a real pixel resolution, readable via
    ffprobe — kept as separate kinds since the density check below only
    means anything for a still image) | "vector" (no fixed resolution —
    SVG and friends; still a picture, so it's kept, just always ranked
    last) | "unsupported" (no visual resolution at all, e.g. .txt/.mp3 —
    dropped entirely)."""
    ext = Path(name).suffix.lower()
    if ext in VECTOR_EXT:
        return "vector"
    if ext in VIDEO_EXT:
        return "video"
    if ext in IMAGE_EXT or ext in GIF_EXT:
        return "image"
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
    density_kb_per_mp: float  # bytes per pixel — flat icon graphics compress far smaller than real photo content at the same resolution; meaningless for video, see is_video below
    aspect_deviation_pct: float  # 0 = perfect square; icons/logos are usually near-square, screenshots and video frames aren't
    has_alpha: bool
    is_video: bool


async def rank_files(
    paths: list[Path],
    job: _ProgressJob,
    density_mode: str = OFF,
    density_threshold_kb_per_mp: float = 50.0,
    alpha_mode: str = OFF,
    square_mode: str = OFF,
    square_tolerance_pct: float = 15.0,
) -> tuple[list[Path], list[Path]]:
    """Sort by resolution descending, file size as the tiebreak. Vector
    images (no fixed resolution but still pictures) are kept and appended
    after, in their original order. Anything with no visual resolution at
    all — a non-media file, or a raster file ffprobe couldn't read — is
    dropped. The three `*_mode` checks (each "выкл"/"понизить в выдаче"/
    "полностью исключить") flag likely-icon raster files — either pushed
    after the genuinely-ranked ones or dropped outright."""
    job.total = len(paths)
    ranked: list[_Ranked] = []
    vector: list[Path] = []
    for i, path in enumerate(paths):
        kind = classify(path.name)
        if kind == "vector":
            vector.append(path)
        elif kind in ("image", "video"):
            info = await probe(path)
            w, h = info["width"], info["height"]
            if w and h:
                area = w * h
                size = path.stat().st_size
                density = (size / 1024) / (area / 1_000_000)
                deviation_pct = (max(w, h) / min(w, h) - 1) * 100
                has_alpha = info.get("pix_fmt") in ALPHA_PIX_FMTS
                ranked.append(_Ranked(path, area, size, density, deviation_pct, has_alpha, kind == "video"))
        job.done = i + 1
        job.progress = job.done / job.total if job.total else 0.0
    ranked.sort(key=lambda r: (-r.area, -r.size))

    kept: list[_Ranked] = []
    demoted: list[_Ranked] = []
    for r in ranked:
        flags = []
        if density_mode != OFF and not r.is_video and r.density_kb_per_mp < density_threshold_kb_per_mp:
            flags.append(density_mode)
        if alpha_mode != OFF and r.has_alpha:
            flags.append(alpha_mode)
        if square_mode != OFF and r.aspect_deviation_pct < square_tolerance_pct:
            flags.append(square_mode)
        if EXCLUDE in flags:
            continue
        (demoted if DEMOTE in flags else kept).append(r)

    return [r.path for r in kept] + [r.path for r in demoted], vector
