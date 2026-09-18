import asyncio
from typing import Literal

from pydantic import BaseModel

from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .domain import blur_filter, crop_filter
from .jobs import new_job, process_archive_job, process_job

Gravity = Literal["center", "top", "bottom", "left", "right"]


class ReframeParams(BaseModel):
    width: int = 1080
    height: int = 1920
    mode: Literal["blur", "crop"] = "blur"
    gravity: Gravity = "center"
    duration: float = 3.0


async def _start(inp: PipelineInput | None, params: ReframeParams):
    if inp is None or inp.data is None:
        raise ValueError("Кадрирование: нужен входной файл или архив")
    w, h = params.width - params.width % 2, params.height - params.height % 2
    vf = crop_filter(w, h, params.gravity) if params.mode == "crop" else blur_filter(w, h)
    name = inp.name or "input"
    if name.lower().endswith(".zip"):
        job = new_job()
        asyncio.create_task(process_archive_job(job, inp.data, name, vf, params.duration))
    else:
        job = new_job(total=1)
        asyncio.create_task(process_job(job, [(name, inp.data)], vf, f"{w}x{h}", params.duration))
    return job


register(ModuleManifest(
    id="reframe",
    label="Кадрирование",
    params_model=ReframeParams,
    input_port=PortType.FILE_LIST,
    output_port=PortType.FILE_LIST,
    start=_start,
    description=[
        "Приводит видео и фото к заданному размеру (ширина × высота)",
        "Blur — вписывает кадр целиком, поля дополняет размытым фоном",
        "Crop — обрезает края по выбранной стороне",
        "Для статичных изображений задаётся длительность итогового ролика",
    ],
))
