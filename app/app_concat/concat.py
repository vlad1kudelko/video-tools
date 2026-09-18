import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from ..clip_assembly import ClipInput, assemble_clips
from .jobs import ConcatJob

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}


def _is_video(name: str) -> bool:
    return Path(name).suffix.lower() in VIDEO_EXT


async def run_concat(
    job: ConcatJob, zip_bytes: bytes, original_name: str,
    transition: str, transition_duration: float, workdir: Path,
) -> None:
    extract_dir = workdir / "in"
    extract_dir.mkdir(parents=True, exist_ok=True)
    src_zip = workdir / "upload.zip"
    src_zip.write_bytes(zip_bytes)

    try:
        job.message = "Распаковка архива"
        with zipfile.ZipFile(src_zip, "r") as zin:
            names = [i.filename for i in zin.infolist() if not i.is_dir()]
            zin.extractall(extract_dir)

        clip_names = sorted(n for n in names if _is_video(n))

        if not clip_names:
            job.status, job.message = "error", "В архиве не найдено видео для склейки"
            return

        clips = [ClipInput(path=extract_dir / n) for n in clip_names]

        job.message = "Склейка"
        out_path = workdir / f"app_concat-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"
        await assemble_clips(clips, transition, transition_duration, out_path, job)

        job.result = out_path
        job.message = "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)
