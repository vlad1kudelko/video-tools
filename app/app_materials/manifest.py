import asyncio
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic import BaseModel

from ..config import TMP
from ..pipeline.manifest import ModuleManifest, PipelineInput
from ..pipeline.registry import register
from ..pipeline.types import PortType
from .github import RepoNotFound, fetch_readme_text, fetch_repo_info, parse_repo
from .links import MediaLink, extract_media
from .site import fetch_rendered_html

MEDIA_KINDS = {"image", "gif", "video"}


class MaterialsParams(BaseModel):
    repo_url: str = ""


@dataclass
class _PipelineJob:
    """Separate from app_materials/jobs.py::MaterialsJob on purpose — that
    one's status vocabulary ("scanning") is tailored to the old interactive
    page's own WS handler, not the pipeline runner's "processing"/"done"/
    "error" polling contract."""

    status: str = "processing"
    message: str = ""
    result: Path | None = None


async def _media_size(client: httpx.AsyncClient, url: str) -> int:
    """Byte size via Content-Length from a HEAD request — one uniform,
    cheap metric across photos/videos/gifs alike, no download needed. A
    server that doesn't answer or doesn't report a length just sorts last
    (0), rather than dropping the link — it may still be perfectly valid
    media, just not size-rankable."""
    try:
        r = await client.head(url, timeout=10, follow_redirects=True)
        return int(r.headers.get("content-length") or 0)
    except Exception:  # noqa: BLE001
        return 0


async def _gather_media(repo_url: str) -> tuple[str, str, list[MediaLink]]:
    """Same sources as the interactive scan (README + homepage), minus the
    human-review step — every recognized media link is kept, nothing is
    picked by hand."""
    parsed = parse_repo(repo_url)
    if not parsed:
        raise ValueError("Некорректная ссылка на репозиторий")
    owner, repo = parsed

    items: list[MediaLink] = []
    seen: set[str] = set()

    def add(new_items: list[MediaLink]) -> None:
        for it in new_items:
            if it.url not in seen:
                items.append(it)
                seen.add(it.url)

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            info = await fetch_repo_info(client, owner, repo)
        except RepoNotFound:
            raise ValueError("Репозиторий не найден")

        readme = await fetch_readme_text(client, owner, repo)
        if readme:
            base = f"https://raw.githubusercontent.com/{owner}/{repo}/{info['default_branch']}/"
            add(extract_media(readme, base, "readme"))

        homepage = (info.get("homepage") or "").strip()
        if homepage:
            try:
                final_url, html = await fetch_rendered_html(homepage)
                add(extract_media(html, final_url, "site"))
            except Exception:  # noqa: BLE001
                pass

    return owner, repo, [it for it in items if it.kind in MEDIA_KINDS]


async def _run(job: _PipelineJob, repo_url: str) -> None:
    try:
        owner, repo, media = await _gather_media(repo_url)
        async with httpx.AsyncClient() as client:
            sizes = await asyncio.gather(*(_media_size(client, it.url) for it in media))
        ranked = sorted(zip(media, sizes), key=lambda pair: pair[1], reverse=True)

        workdir = TMP / uuid4().hex[:12]
        workdir.mkdir(parents=True, exist_ok=True)
        out_path = workdir / f"{owner}--{repo}.txt".lower()
        out_path.write_text("\n".join(f"{it.url} -> {size}" for it, size in ranked) + "\n", encoding="utf-8")

        job.result = out_path
        job.message = f"Готово, найдено {len(ranked)}"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)


async def _start(inp: PipelineInput | None, params: MaterialsParams):
    job = _PipelineJob()
    asyncio.create_task(_run(job, params.repo_url))
    return job


register(ModuleManifest(
    id="materials",
    label="Подготовка материала",
    params_model=MaterialsParams,
    output_port=PortType.TEXT_FILE,
    start=_start,
))
