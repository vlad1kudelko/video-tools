import asyncio

from pydantic import BaseModel

from ..clip_assembly import Transition
from ..config import TMP
from ..pipeline.manifest import BlockInput, ModuleManifest
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .combinator import run_generate
from .jobs import new_job


class CombinatorParams(BaseModel):
    transition: Transition = "fade"
    transition_duration: float = 0.5


async def _start(blocks: list[BlockInput], params: CombinatorParams):
    if not blocks:
        raise ValueError("Комбинатор: нужен хотя бы один блок")
    blocks_files: list[list[tuple[str, bytes]]] = []
    block_repeats: list[int] = []
    for b in blocks:
        if b.input is None or b.input.data is None:
            raise ValueError("Комбинатор: у одного из блоков нет входного файла")
        blocks_files.append([(b.input.name or "media.zip", b.input.data)])
        block_repeats.append(max(1, b.count))

    job = new_job()
    workdir = TMP / job.id
    asyncio.create_task(run_generate(
        job, blocks_files, block_repeats,
        params.transition, params.transition_duration, workdir,
    ))
    return job


register(ModuleManifest(
    id="combinator",
    label="Комбинатор",
    params_model=CombinatorParams,
    block_input=PortType.FILE_LIST,
    output_port=PortType.VIDEO_FILE,
    start=_start,
    description=[
        "Несколько блоков с видео — у каждого блока своё количество повторов в ролике",
        "Клипы выбираются с учётом истории использования: реже использованные попадают чаще",
        "Между клипами — плавный переход, как в «Склейке»",
    ],
))
