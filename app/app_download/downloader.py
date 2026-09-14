import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .jobs import DownloadJob
from .parse import is_youtube

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; video-tools-download-bot/1.0)"}


def _ext_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix
    return suffix if 1 < len(suffix) <= 6 else ""


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
            url = raw.strip()
            name = f"media-{line_no:03d}"
            job.current_name = name
            job.current_progress = 0.0
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
                        saved.append(dst)
                except Exception:  # noqa: BLE001
                    pass
            job.done = line_no
            job.current_progress = 1.0
    return saved, skipped_youtube
