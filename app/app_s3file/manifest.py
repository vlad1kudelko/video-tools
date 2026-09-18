import asyncio
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from ..config import TMP
from ..pipeline import s3_store
from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType


class S3FileParams(BaseModel):
    key: str = Field(default="", title="Файл в S3")


@dataclass
class _Job:
    status: str = "processing"  # processing | done | error
    message: str = ""
    progress: float = 0.0
    result: Path | None = None


def _download_sync(key: str, out_path: Path, job: _Job) -> None:
    """Runs in a worker thread — boto3 is synchronous, and calling it
    directly from a coroutine would freeze the whole event loop (no WS
    updates, no other node progressing) for as long as the transfer takes.
    Streamed so a large file doesn't sit fully in memory and the progress
    bar actually moves."""
    client = s3_store._s3()
    resp = client.get_object(Bucket=s3_store.S3_BUCKET, Key=key)
    total = resp.get("ContentLength") or 0
    written = 0
    with open(out_path, "wb") as f:
        for chunk in resp["Body"].iter_chunks(chunk_size=1024 * 1024):
            f.write(chunk)
            written += len(chunk)
            if total:
                job.progress = min(written / total, 1.0)


async def _run(job: _Job, key: str) -> None:
    try:
        if not key:
            job.status, job.message = "error", "Не выбран файл"
            return
        workdir = TMP / uuid4().hex[:12]
        workdir.mkdir(parents=True, exist_ok=True)
        out_path = workdir / key.rsplit("/", 1)[-1]
        await asyncio.to_thread(_download_sync, key, out_path, job)
        job.result = out_path
        job.message = "загружено"
        job.progress = 1.0
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)


async def _start(inp: PipelineInput | None, params: S3FileParams):
    job = _Job()
    asyncio.create_task(_run(job, params.key))
    return job


register(ModuleManifest(
    id="s3file",
    label="Файл из S3",
    params_model=S3FileParams,
    output_port=PortType.FILE_LIST,
    start=_start,
    description="Выбирает уже загруженный в S3 файл (загружается через админку хостера) и передаёт его дальше по связи.",
))
