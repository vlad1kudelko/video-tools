import asyncio
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from ..config import TMP
from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .domain import rank_files


class FilterParams(BaseModel):
    pass  # a fixed resolution-descending sort — nothing to configure


@dataclass
class _Job:
    status: str = "processing"  # processing | done | error
    message: str = ""
    total: int = 0
    done: int = 0
    progress: float = 0.0
    result: Path | None = None


async def _run(job: _Job, data: bytes, name: str) -> None:
    workdir = TMP / uuid4().hex[:12]
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        if name.lower().endswith(".zip"):
            extract_dir = workdir / "in"
            extract_dir.mkdir(parents=True, exist_ok=True)
            src_zip = workdir / "upload.zip"
            src_zip.write_bytes(data)
            with zipfile.ZipFile(src_zip, "r") as zin:
                names = [i.filename for i in zin.infolist() if not i.is_dir()]
                zin.extractall(extract_dir)
            paths = [extract_dir / n for n in names]
            came_as_archive = True
        else:
            src = workdir / (name or "input")
            src.write_bytes(data)
            paths = [src]
            came_as_archive = False

        job.message = "Анализ разрешения"
        ranked, vector = await rank_files(paths, job)
        ordered = ranked + vector

        if not ordered:
            job.status, job.message = "error", "Нет файлов с разрешением — всё отфильтровано"
            return

        if len(ordered) == 1 and not came_as_archive:
            job.result = ordered[0]
        else:
            zpath = workdir / f"{Path(name).stem}[filtered].zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zout:
                for i, p in enumerate(ordered):
                    zout.write(p, f"{i + 1:03d}{p.suffix}")
            job.result = zpath

        job.message = f"Готово, {len(ordered)} файлов"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)


async def _start(inp: PipelineInput | None, params: FilterParams):
    if inp is None or inp.data is None:
        raise ValueError("Фильтрование: нужен входной файл или архив")
    job = _Job()
    asyncio.create_task(_run(job, inp.data, inp.name or "input"))
    return job


register(ModuleManifest(
    id="filter",
    label="Фильтрование",
    params_model=FilterParams,
    input_port=PortType.VIDEO_FILE_LIST,
    output_port=PortType.VIDEO_FILE_LIST,
    start=_start,
    description="Сортирует список файлов по разрешению кадра и по размеру — по убыванию.",
))
