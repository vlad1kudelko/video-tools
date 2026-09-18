import mimetypes
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ..config import TMP
from .jobs import DownloadJob
from .parse import is_youtube

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; video-tools-download-bot/1.0)"}


def _ext_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix
    return suffix if 1 < len(suffix) <= 6 else ""


def _sync_progress(job: DownloadJob) -> None:
    job.progress = min((job.done + job.current_progress) / job.total, 1.0) if job.total else 0.0


async def download_all(job: DownloadJob, lines: list[str], workdir: Path) -> tuple[list[Path], list[str]]:
    """Download the URL on each line to workdir/media-<line-number>.ext — the
    number is the line's position in the source file, not a running count, so
    a filename always maps back to the exact line it came from, even if other
    lines were skipped or failed. YouTube links are recorded but not
    downloaded; anything else that fails (bad URL, blank line, network error)
    is silently skipped — no separate parsing/filtering pass needed."""
    workdir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    skipped_youtube: list[str] = []
    job.total = len(lines)
    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
        for line_no, raw in enumerate(lines, start=1):
            # "Материалы" emits "<url> -> <size>" lines; a plain links.txt
            # (no " -> ") is untouched by the split.
            url = raw.split(" -> ", 1)[0].strip()
            name = f"media-{line_no:03d}"
            job.current_name = name
            job.current_progress = 0.0
            _sync_progress(job)
            if is_youtube(url):
                skipped_youtube.append(url)
            else:
                try:
                    async with client.stream("GET", url) as r:
                        r.raise_for_status()
                        content_type = (r.headers.get("content-type") or "").split(";")[0].strip()
                        ext = _ext_from_url(url) or mimetypes.guess_extension(content_type) or ""
                        dst = workdir / f"{name}{ext}"
                        total_bytes = int(r.headers.get("content-length") or 0)
                        written = 0
                        with open(dst, "wb") as f:
                            async for chunk in r.aiter_bytes():
                                f.write(chunk)
                                written += len(chunk)
                                if total_bytes:
                                    job.current_progress = min(written / total_bytes, 1.0)
                                    _sync_progress(job)
                        saved.append(dst)
                except Exception:  # noqa: BLE001
                    pass
            job.done = line_no
            job.current_progress = 1.0
            _sync_progress(job)
    return saved, skipped_youtube


async def run_download(job: DownloadJob, raw_text: str) -> None:
    try:
        lines = raw_text.splitlines()
        workdir = TMP / job.id
        job.message = "Скачивание"
        saved, skipped_youtube = await download_all(job, lines, workdir)
        job.skipped_youtube = skipped_youtube

        if not saved and not skipped_youtube:
            job.status, job.message = "error", "Не удалось скачать ни одной ссылки"
            return

        zpath = workdir / f"app_download-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for p in saved:
                z.write(p, p.name)
            z.writestr("links.txt", raw_text)

        job.result = zpath
        failed = job.total - len(saved) - len(skipped_youtube)
        job.message = "Готово" if failed <= 0 else f"Готово, не удалось скачать: {failed}"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
