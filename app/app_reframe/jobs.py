import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ..config import TMP
from .domain import Job, sync_progress
from .ffmpeg import run_ffmpeg
from .media import classify_media

JOBS: dict[str, Job] = {}


def new_job(total: int = 0) -> Job:
    job = Job(id=uuid4().hex[:12], total=total)
    JOBS[job.id] = job
    return job


async def _reframe_one(src: Path, dst: Path, vf: str, duration: float, job: Job) -> None:
    """Run one media file through the filter — a still image is looped into a
    `duration`-second clip; a gif or video is read as-is (already time-based)."""
    kind = classify_media(src.name)
    image_duration = duration if kind == "image" else None
    await run_ffmpeg(src, dst, vf, job, image_duration=image_duration)


async def process_job(job: Job, payload: list[tuple[str, bytes]], vf: str, suffix: str, duration: float) -> None:
    """Direct upload(s): each item becomes one reframed video, zipped together
    if there's more than one."""
    workdir = TMP / job.id
    workdir.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    try:
        for i, (name, data) in enumerate(payload):
            src = workdir / f"in{i}{Path(name).suffix}"
            src.write_bytes(data)
            dst = workdir / f"{Path(name).stem or 'media'}_{suffix}.mp4"
            job.current_progress = 0.0
            job.message = f"{i + 1} / {job.total} файлов"
            sync_progress(job)
            await _reframe_one(src, dst, vf, duration, job)
            src.unlink(missing_ok=True)
            outs.append(dst)
            job.done = i + 1
            sync_progress(job)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if len(outs) == 1:
            renamed = outs[0].with_name(f"app_reframe-{timestamp}.mp4")
            outs[0].rename(renamed)
            job.result, job.is_zip = renamed, False
        else:
            zpath = workdir / f"app_reframe-{timestamp}.zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
                for o in outs:
                    z.write(o, o.name)
            job.result, job.is_zip = zpath, True
        job.message = f"обработано {len(outs)}"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)


async def process_archive_job(job: Job, zip_bytes: bytes, original_name: str, vf: str, duration: float) -> None:
    """A zip of media, possibly mixed with unrelated files: reframe every
    recognized media file in place, copy everything else through untouched,
    and repack under the same names."""
    workdir = TMP / job.id
    extract_dir = workdir / "in"
    out_dir = workdir / "out"
    extract_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    src_zip = workdir / "upload.zip"
    src_zip.write_bytes(zip_bytes)

    try:
        with zipfile.ZipFile(src_zip, "r") as zin:
            infos = [i for i in zin.infolist() if not i.is_dir()]
            zin.extractall(extract_dir)

        job.total = len(infos)
        for i, info in enumerate(infos):
            rel = info.filename
            src = extract_dir / rel
            kind = classify_media(rel)
            job.message = f"{i + 1} / {job.total} файлов"
            if kind is None:
                dst = out_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            else:
                dst = (out_dir / rel).with_suffix(".mp4")
                dst.parent.mkdir(parents=True, exist_ok=True)
                job.current_progress = 0.0
                sync_progress(job)
                await _reframe_one(src, dst, vf, duration, job)
            job.done = i + 1
            sync_progress(job)

        zpath = workdir / f"app_reframe-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zout:
            for f in sorted(out_dir.rglob("*")):
                if f.is_file():
                    zout.write(f, f.relative_to(out_dir))

        job.result, job.is_zip = zpath, True
        job.message = f"обработано {job.total}"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)


def cleanup(job_id: str) -> None:
    JOBS.pop(job_id, None)
    shutil.rmtree(TMP / job_id, ignore_errors=True)
