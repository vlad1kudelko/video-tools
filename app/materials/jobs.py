import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from ..config import TMP
from .links import MediaLink


@dataclass
class MaterialsJob:
    id: str
    status: str = "scanning"  # scanning | done | error
    message: str = ""
    items: list[MediaLink] = field(default_factory=list)
    result: Path | None = None


JOBS: dict[str, MaterialsJob] = {}


def new_job() -> MaterialsJob:
    job = MaterialsJob(id=uuid4().hex[:12])
    JOBS[job.id] = job
    return job


def cleanup(job_id: str) -> None:
    JOBS.pop(job_id, None)
    shutil.rmtree(TMP / job_id, ignore_errors=True)
