import asyncio
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from ..config import TMP
from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .domain import gather_candidates


class FilterParams(BaseModel):
    # transient: a one-time confirmation, not durable config — see Canvas.jsx's serializeGraph.
    manual_selection: list[str] = Field(default_factory=list, title="Ручной отбор", json_schema_extra={"transient": True})


@dataclass
class _Job:
    status: str = "processing"  # processing | waiting | done | error
    message: str = ""
    total: int = 0
    done: int = 0
    progress: float = 0.0
    result: Path | None = None
    candidates: list[dict] | None = None  # only set when status == "waiting"
    workdir: Path | None = None  # only set when status == "waiting" — where the runner can serve candidate bytes from


def _extract(workdir: Path, data: bytes, name: str) -> tuple[list[Path], list[str], Path]:
    """Returns (paths, rel_names, base_dir) — rel_names are stable across
    separate runs of the same input (the zip-internal path, or the bare
    filename for a single non-archive upload), used as each candidate's id;
    base_dir is the one directory every path lives under, so a candidate id
    always resolves back to a real file via base_dir / rel_name."""
    base_dir = workdir / "in"
    base_dir.mkdir(parents=True, exist_ok=True)
    if name.lower().endswith(".zip"):
        src_zip = workdir / "upload.zip"
        src_zip.write_bytes(data)
        with zipfile.ZipFile(src_zip, "r") as zin:
            rel_names = [i.filename for i in zin.infolist() if not i.is_dir()]
            zin.extractall(base_dir)
        return [base_dir / n for n in rel_names], rel_names, base_dir
    rel_name = name or "input"
    (base_dir / rel_name).write_bytes(data)
    return [base_dir / rel_name], [rel_name], base_dir


async def _run(job: _Job, data: bytes, name: str, params: FilterParams) -> None:
    workdir = TMP / uuid4().hex[:12]
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        paths, rel_names, base_dir = _extract(workdir, data, name)

        if not params.manual_selection:
            job.message = "Анализ разрешения"
            candidates = await gather_candidates(paths, rel_names, job)
            if not candidates:
                job.status, job.message = "error", "Нет файлов с разрешением — нечего выбирать"
                return
            job.candidates = [
                {"id": c.rel_path, "name": Path(c.rel_path).name, "kind": c.kind, "width": c.width, "height": c.height, "size": c.size}
                for c in candidates
            ]
            job.workdir = base_dir
            job.message = f"ожидает отбора: {len(candidates)}"
            job.status = "waiting"
            return

        by_rel = dict(zip(rel_names, paths))
        ordered = [by_rel[rid] for rid in params.manual_selection if rid in by_rel]
        if not ordered:
            job.status, job.message = "error", "Выбранные файлы не найдены во входных данных"
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if len(ordered) == 1 and len(paths) == 1:
            renamed = ordered[0].with_name(f"app_filter-{timestamp}{ordered[0].suffix}")
            ordered[0].rename(renamed)
            job.result = renamed
        else:
            zpath = workdir / f"app_filter-{timestamp}.zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zout:
                for i, p in enumerate(ordered):
                    zout.write(p, f"{i + 1:03d}{p.suffix}")
            job.result = zpath

        job.message = f"отфильтровано {len(ordered)}"
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
    input_port=PortType.FILE_LIST,
    output_port=PortType.FILE_LIST,
    start=_start,
    description=[
        "Останавливается и показывает превью всех файлов на входе",
        "Вы вручную выбираете нужные и порядок, в котором их отправить дальше — по клику",
        "После нажатия «Продолжить» отдаёт только выбранное, в выбранном порядке",
    ],
))
