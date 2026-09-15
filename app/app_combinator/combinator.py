import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from ..clip_assembly import ClipInput, assemble_clips
from .jobs import CombinatorJob
from .usage import least_used_pick, record_usage

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".avif"}
GIF_EXT = {".gif"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv"}
IMAGE_CLIP_DURATION = 3.0


def _classify(name: str) -> str | None:
    ext = Path(name).suffix.lower()
    if ext in GIF_EXT:
        return "gif"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return None


def _gather_pool(files: list[tuple[str, bytes]], pool_dir: Path) -> list[Path]:
    """Unzip any archive among `files`, classify everything (direct uploads and
    archive contents alike), and return the paths of recognized media."""
    pool_dir.mkdir(parents=True, exist_ok=True)
    pool: list[Path] = []
    for name, data in files:
        if name.lower().endswith(".zip"):
            zpath = pool_dir / "src.zip"
            zpath.write_bytes(data)
            with zipfile.ZipFile(zpath) as z:
                for info in z.infolist():
                    if info.is_dir() or _classify(info.filename) is None:
                        continue
                    dst = pool_dir / Path(info.filename).name
                    with z.open(info) as src, open(dst, "wb") as out:
                        shutil.copyfileobj(src, out)
                    pool.append(dst)
            zpath.unlink(missing_ok=True)
        elif _classify(name) is not None:
            dst = pool_dir / name
            dst.write_bytes(data)
            pool.append(dst)
    return pool


async def run_generate(
    job: CombinatorJob, blocks_files: list[list[tuple[str, bytes]]], block_repeats: list[int],
    transition: str, transition_duration: float, workdir: Path,
) -> None:
    try:
        job.message = "Сбор пулов"
        pools = [_gather_pool(files, workdir / f"block{i}") for i, files in enumerate(blocks_files)]
        if any(not p for p in pools):
            job.status, job.message = "error", "В одном из блоков нет подходящих файлов"
            return

        job.message = "Выбор файлов"
        used_names: set[str] = set()
        picks: list[Path] = []
        for pool, repeat in zip(pools, block_repeats):
            for _ in range(repeat):
                candidates = [p for p in pool if p.name not in used_names] or pool
                chosen = least_used_pick(candidates)
                picks.append(chosen)
                used_names.add(chosen.name)

        clips = [
            ClipInput(path=p, forced_duration=IMAGE_CLIP_DURATION if _classify(p.name) == "image" else None)
            for p in picks
        ]

        job.message = "Склейка"
        out_path = workdir / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
        await assemble_clips(clips, transition, transition_duration, out_path, job)

        record_usage([p.name for p in picks])

        job.result = out_path
        job.message = "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)
