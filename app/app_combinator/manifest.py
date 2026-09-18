import asyncio

from pydantic import BaseModel

from ..config import TMP
from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .combinator import run_generate
from .jobs import new_job


class CombinatorParams(BaseModel):
    transition: str = "fade"
    transition_duration: float = 0.5


async def _start(inp: PipelineInput | None, params: CombinatorParams):
    if inp is None or inp.data is None:
        raise ValueError("Комбинатор: нужен хотя бы один файл/архив")
    # Упрощение Фазы 1: пайплайн-порт соответствует ровно одному блоку с
    # повторением 1 — полноценный UI с динамическими блоками на холсте
    # появится отдельно (см. план), это не меняет саму run_generate.
    job = new_job()
    workdir = TMP / job.id
    blocks_files = [[(inp.name or "media.zip", inp.data)]]
    asyncio.create_task(run_generate(
        job, blocks_files, [1],
        params.transition, params.transition_duration, workdir,
    ))
    return job


register(ModuleManifest(
    id="combinator",
    label="Комбинатор",
    params_model=CombinatorParams,
    input_port=PortType.VIDEO_FILE_LIST,
    output_port=PortType.VIDEO_FILE,
    start=_start,
))
