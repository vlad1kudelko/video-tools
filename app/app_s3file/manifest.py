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


async def _run(job: _Job, key: str) -> None:
    try:
        if not key:
            job.status, job.message = "error", "Не выбран файл"
            return
        data = s3_store.get_object(key)
        workdir = TMP / uuid4().hex[:12]
        workdir.mkdir(parents=True, exist_ok=True)
        out_path = workdir / key.rsplit("/", 1)[-1]
        out_path.write_bytes(data)
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
