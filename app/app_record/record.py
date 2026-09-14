import asyncio
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from .jobs import RecordJob

TICK_SECONDS = 0.05
FPS = round(1 / TICK_SECONDS)


async def _frames_to_mp4(frames_dir: Path, total: int, dst: Path, job: RecordJob) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png"),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats", str(dst),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    async for raw in proc.stdout:
        line = raw.decode().strip()
        if line.startswith("frame=") and total:
            try:
                job.progress = min(int(line.split("=", 1)[1]) / total, 1.0)
            except ValueError:
                pass
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg assemble failed")
    job.progress = 1.0


async def run_record(
    job: RecordJob, url: str, width: int, height: int, workdir: Path,
    scroll_speed: float, max_seconds: float,
) -> None:
    """Load the page in a real (rendering) Chromium, take a viewport screenshot
    every tick while scrolling smoothly to the bottom, then assemble the frames
    into an mp4 at a fixed frame rate — deterministic pacing, unlike Playwright's
    own context video recorder, whose screencast frame rate isn't guaranteed and
    can stutter under load."""
    workdir.mkdir(parents=True, exist_ok=True)
    frames_dir = workdir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    try:
        job.message = "Открытие страницы"
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                context = await browser.new_context(viewport={"width": width, "height": height})
                page = await context.new_page()
                await page.goto(url, wait_until="load", timeout=30000)

                job.message = "Запись и прокрутка"
                step = scroll_speed * TICK_SECONDS
                started = time.monotonic()
                frame_i = 0
                while True:
                    await page.screenshot(path=str(frames_dir / f"f{frame_i:05d}.png"))
                    frame_i += 1
                    state = await page.evaluate(
                        "() => ({y: window.scrollY, h: document.body.scrollHeight, vh: window.innerHeight})"
                    )
                    job.progress = min(state["y"] / max(state["h"] - state["vh"], 1), 1.0)
                    elapsed = time.monotonic() - started
                    if state["y"] + state["vh"] >= state["h"] - 2 or elapsed > max_seconds:
                        break
                    await page.evaluate("(step) => window.scrollBy(0, step)", step)
                    await asyncio.sleep(TICK_SECONDS)
            finally:
                await browser.close()

        job.message = "Сборка видео"
        job.progress = 0.0
        host = urlparse(url).hostname or "record"
        out_path = workdir / f"{host}[record].mp4"
        await _frames_to_mp4(frames_dir, frame_i, out_path, job)
        shutil.rmtree(frames_dir, ignore_errors=True)

        job.result = out_path
        job.message = "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
