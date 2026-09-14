import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ..config import TMP


@dataclass
class ConcatJob:
    id: str
    status: str = "processing"  # processing | done | error
    message: str = ""
    warning: str = ""
    progress: float = 0.0
    result: Path | None = None


JOBS: dict[str, ConcatJob] = {}


def new_job() -> ConcatJob:
    job = ConcatJob(id=uuid4().hex[:12])
    JOBS[job.id] = job
    return job


def cleanup(job_id: str) -> None:
    JOBS.pop(job_id, None)
    shutil.rmtree(TMP / job_id, ignore_errors=True)
