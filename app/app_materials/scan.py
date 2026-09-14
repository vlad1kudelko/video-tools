import httpx

from .github import RepoNotFound, fetch_readme_text, fetch_repo_info, parse_repo
from .jobs import MaterialsJob
from .links import extract_media
from .site import fetch_rendered_html


def _add(job: MaterialsJob, new_items: list) -> None:
    existing = {it.url for it in job.items}
    for it in new_items:
        if it.url not in existing:
            job.items.append(it)
            existing.add(it.url)


async def run_scan(job: MaterialsJob, repo_url: str) -> None:
    parsed = parse_repo(repo_url)
    if not parsed:
        job.status, job.message = "error", "Некорректная ссылка на репозиторий"
        return
    owner, repo = parsed
    job.filename = f"{owner}/{repo}".lower().replace("/", "--") + ".txt"
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
                    final_url, html = await fetch_rendered_html(homepage)
                    _add(job, extract_media(html, final_url, "site"))
                except Exception:  # noqa: BLE001
                    warning = "Сайт недоступен — использованы только данные README"

        job.message = warning or "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
