import asyncio

from pydantic import BaseModel

from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .downloader import run_download
from .jobs import new_job


class DownloadParams(BaseModel):
    pass  # links.txt content is the whole input — no scalar params today


async def _start(inp: PipelineInput | None, params: DownloadParams):
    if inp is None or inp.text is None:
        raise ValueError("Скачивание: нужен текстовый файл со ссылками")
    job = new_job()
    job.filename = "media.zip"
    asyncio.create_task(run_download(job, inp.text))
    return job


register(ModuleManifest(
    id="download",
    label="Скачивание медиа",
    params_model=DownloadParams,
    input_port=PortType.TEXT_FILE,
    output_port=PortType.FILE_LIST,
    start=_start,
    description=[
        "Скачивает файлы по списку ссылок — одна ссылка на строку",
        "Ссылки на YouTube пропускает, не скачивая",
        "Все скачанные файлы упаковывает в один архив",
    ],
))
