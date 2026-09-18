import asyncio
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ..config import TMP
from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .domain import rank_files

Mode = Literal["выкл", "понизить в выдаче", "полностью исключить"]


class FilterParams(BaseModel):
    density_mode: Mode = Field(default="выкл", title="Проверка плотности (иконки/логотипы)")
    density_threshold_kb_per_mp: float = Field(default=50.0, title="Порог плотности, КБ на мегапиксель")
    alpha_mode: Mode = Field(default="выкл", title="Проверка альфа-канала")
    square_mode: Mode = Field(default="выкл", title="Считать иконкой при отклонении от квадрата меньше")
    square_tolerance_pct: float = Field(default=15.0, title="Считать иконкой при отклонении от квадрата меньше, %")


@dataclass
class _Job:
    status: str = "processing"  # processing | done | error
    message: str = ""
    total: int = 0
    done: int = 0
    progress: float = 0.0
    result: Path | None = None


async def _run(job: _Job, data: bytes, name: str, params: FilterParams) -> None:
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
        ranked, vector = await rank_files(
            paths, job,
            density_mode=params.density_mode,
            density_threshold_kb_per_mp=params.density_threshold_kb_per_mp,
            alpha_mode=params.alpha_mode,
            square_mode=params.square_mode,
            square_tolerance_pct=params.square_tolerance_pct,
        )
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
    asyncio.create_task(_run(job, inp.data, inp.name or "input", params))
    return job


register(ModuleManifest(
    id="filter",
    label="Фильтрование",
    params_model=FilterParams,
    input_port=PortType.VIDEO_FILE_LIST,
    output_port=PortType.VIDEO_FILE_LIST,
    start=_start,
    description=[
        "Сортирует список файлов по разрешению кадра и по размеру — по убыванию",
        "Проверка плотности: низкая плотность (мало байт на мегапиксель) выдаёт плоскую графику вроде иконок и логотипов",
        "Проверка альфа-канала: помечает файлы с прозрачностью",
        "Проверка квадратности: помечает файлы, у которых отклонение от квадрата меньше заданного процента — например, 5% поймает только совсем квадратные и близкие к ним",
        "Для каждой проверки — либо просто понизить такие файлы в выдаче, либо исключить полностью",
    ],
))
