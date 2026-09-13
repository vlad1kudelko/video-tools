from pathlib import Path

import httpx

from ..config import TMP
from .github import RepoNotFound, fetch_readme_text, fetch_repo_info, parse_repo
from .jobs import MaterialsJob
from .links import extract_media

_SITE_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; video-tools-materials-bot/1.0)"}


def _add(job: MaterialsJob, new_items: list) -> None:
    existing = {it.url for it in job.items}
    for it in new_items:
        if it.url not in existing:
            job.items.append(it)
            existing.add(it.url)


def _write_links_txt(job: MaterialsJob) -> Path:
    workdir = TMP / job.id
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / "links.txt"
    lines: list[str] = []
    for kind, title in (("image", "images"), ("gif", "gifs"), ("video", "videos")):
        urls = [it.url for it in job.items if it.kind == kind]
        if not urls:
            continue
        lines.append(f"# {title}")
        lines.extend(urls)
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


async def run_scan(job: MaterialsJob, repo_url: str) -> None:
    parsed = parse_repo(repo_url)
    if not parsed:
        job.status, job.message = "error", "Некорректная ссылка на репозиторий"
        return
    owner, repo = parsed
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            job.message = "Проверка репозитория"
            try:
                info = await fetch_repo_info(client, owner, repo)
            except RepoNotFound:
                job.status, job.message = "error", "Репозиторий не найден"
                return

            job.message = "Чтение README"
            readme = await fetch_readme_text(client, owner, repo)
            if readme:
                base = f"https://raw.githubusercontent.com/{owner}/{repo}/{info['default_branch']}/"
                _add(job, extract_media(readme, base, "readme"))

            homepage = (info.get("homepage") or "").strip()
            warning = None
            if homepage:
                job.message = "Загрузка сайта"
                try:
                    r = await client.get(homepage, headers=_SITE_HEADERS, follow_redirects=True)
                    r.raise_for_status()
                    _add(job, extract_media(r.text, str(r.url), "site"))
                except httpx.HTTPError:
                    warning = "Сайт недоступен — использованы только данные README"

        job.result = _write_links_txt(job)
        job.message = warning or "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
