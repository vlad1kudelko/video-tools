import asyncio

from pydantic import BaseModel

from ..clip_assembly import Transition
from ..config import TMP
from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .concat import run_concat
from .jobs import new_job


class ConcatParams(BaseModel):
    transition: Transition = "fade"
    transition_duration: float = 0.5


async def _start(inp: PipelineInput | None, params: ConcatParams):
    if inp is None or inp.data is None:
        raise ValueError("Склейка: нужен zip-архив с видео")
    job = new_job()
    workdir = TMP / job.id
    asyncio.create_task(run_concat(
        job, inp.data, inp.name or "video.zip",
        params.transition, params.transition_duration, workdir,
    ))
    return job


register(ModuleManifest(
    id="concat",
    label="Склейка видео",
    params_model=ConcatParams,
    input_port=PortType.FILE_LIST,
    output_port=PortType.VIDEO_FILE,
    start=_start,
    description=[
        "Склеивает видео из архива в один ролик, в порядке файлов внутри архива",
        "Между клипами — плавный переход заданной длительности",
    ],
))
