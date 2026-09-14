import asyncio
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from .jobs import RecordJob

TICK_SECONDS = 0.05


async def _probe_duration(path: Path) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nk=1:nw=1", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    try:
        return float(out.decode().strip())
    except ValueError:
        return 0.0


async def _to_mp4(src: Path, dst: Path, job: RecordJob) -> None:
    dur = await _probe_duration(src)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats", str(dst),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    async for raw in proc.stdout:
        line = raw.decode().strip()
        if line.startswith("out_time=") and dur:
            try:
                hh, mm, ss = line.split("=", 1)[1].split(":")
                job.progress = min((int(hh) * 3600 + int(mm) * 60 + float(ss)) / dur, 1.0)
            except ValueError:
                pass
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg convert failed")
    job.progress = 1.0


async def run_record(
    job: RecordJob, url: str, width: int, height: int, workdir: Path,
    scroll_speed: float, max_seconds: float,
) -> None:
    """Load the page in a real (rendering) Chromium, record the context video
    while scrolling smoothly to the bottom, then re-encode the result to mp4."""
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        job.message = "Открытие страницы"
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                context = await browser.new_context(
                    viewport={"width": width, "height": height},
                    record_video_dir=str(workdir),
                    record_video_size={"width": width, "height": height},
                )
                page = await context.new_page()
                await page.goto(url, wait_until="load", timeout=30000)

                job.message = "Запись и прокрутка"
                step = scroll_speed * TICK_SECONDS
                started = time.monotonic()
                while True:
                    state = await page.evaluate(
                        "() => ({y: window.scrollY, h: document.body.scrollHeight, vh: window.innerHeight})"
                    )
                    job.progress = min(state["y"] / max(state["h"] - state["vh"], 1), 1.0)
                    elapsed = time.monotonic() - started
                    if state["y"] + state["vh"] >= state["h"] - 2 or elapsed > max_seconds:
                        break
                    await page.evaluate("(step) => window.scrollBy(0, step)", step)
                    await asyncio.sleep(TICK_SECONDS)

                video = page.video
                await context.close()
                webm_path = Path(await video.path())
            finally:
                await browser.close()

        job.message = "Конвертация видео"
        job.progress = 0.0
        host = urlparse(url).hostname or "record"
        out_path = workdir / f"{host}[record].mp4"
        await _to_mp4(webm_path, out_path, job)

        job.result = out_path
        job.message = "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
