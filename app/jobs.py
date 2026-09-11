import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from .config import TMP
from .domain import Job
from .ffmpeg import run_ffmpeg

JOBS: dict[str, Job] = {}


def new_job(total: int) -> Job:
    job = Job(id=uuid4().hex[:12], total=total)
    JOBS[job.id] = job
    return job


async def process_job(job: Job, payload: list[tuple[str, bytes]], vf: str, suffix: str) -> None:
    workdir = TMP / job.id
    workdir.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    try:
        for i, (name, data) in enumerate(payload):
            src = workdir / f"in{i}"
            src.write_bytes(data)
            dst = workdir / f"{Path(name).stem or 'video'}_{suffix}.mp4"
            job.progress = 0.0
            await run_ffmpeg(src, dst, vf, job)
            src.unlink(missing_ok=True)
            outs.append(dst)
            job.done = i + 1
        if len(outs) == 1:
            job.result, job.is_zip = outs[0], False
        else:
            zpath = workdir / "result.zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
                for o in outs:
                    z.write(o, o.name)
            job.result, job.is_zip = zpath, True
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)


def cleanup(job_id: str) -> None:
    JOBS.pop(job_id, None)
    shutil.rmtree(TMP / job_id, ignore_errors=True)
