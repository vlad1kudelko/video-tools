import asyncio
from pathlib import Path

from .domain import Job


async def probe_duration(src: Path) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nk=1:nw=1", str(src),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    try:
        return float(out.decode().strip())
    except ValueError:
        return 0.0


async def run_ffmpeg(src: Path, dst: Path, vf: str, job: Job) -> None:
    dur = await probe_duration(src)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src), "-filter_complex", vf,
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
        raise RuntimeError(f"ffmpeg failed: {src.name}")
    job.progress = 1.0
