import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from ..config import TMP


@dataclass
class DownloadJob:
    id: str
    status: str = "processing"  # processing | done | error
    message: str = ""
    filename: str = "media.zip"
    total: int = 0
    done: int = 0
    current_name: str = ""
    current_progress: float = 0.0
    progress: float = 0.0  # overall fraction, (done + current_progress) / total — the pipeline reads this uniformly
    skipped_youtube: list[str] = field(default_factory=list)
    result: Path | None = None


JOBS: dict[str, DownloadJob] = {}


def new_job() -> DownloadJob:
    job = DownloadJob(id=uuid4().hex[:12])
    JOBS[job.id] = job
    return job


def cleanup(job_id: str) -> None:
    JOBS.pop(job_id, None)
    shutil.rmtree(TMP / job_id, ignore_errors=True)
