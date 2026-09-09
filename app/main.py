import asyncio
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

TMP = Path("/tmp/video-tools")
STATIC = Path(__file__).parent / "static"
JOBS: dict[str, "Job"] = {}


@dataclass
class Job:
    id: str
    total: int
    done: int = 0
    progress: float = 0.0
    status: str = "processing"  # processing | done | error
    message: str = ""
    result: Path | None = None
    is_zip: bool = False


CROP_XY = {
    "center": "",
    "left": ":0:(ih-oh)/2",
    "right": ":iw-ow:(ih-oh)/2",
    "top": ":(iw-ow)/2:0",
    "bottom": ":(iw-ow)/2:ih-oh",
}


def blur_filter(w: int, h: int) -> str:
    """Scale the video to fit and fill the padding with a blurred cover of itself."""
    return (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},gblur=sigma=25,eq=brightness=-0.1[bg];"
        f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
    )


def crop_filter(w: int, h: int, gravity: str) -> str:
    """Scale to cover the target and crop the overflow toward the given edge."""
    return (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h}{CROP_XY.get(gravity, '')},setsar=1"
    )


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


async def process_job(job: Job, payload: list[tuple[str, bytes]], vf: str, suffix: str) -> None:
    workdir = TMP / job.id
    workdir.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    try:
        for i, (name, data) in enumerate(payload):
            src = workdir / f"in{i}"
            src.write_bytes(data)
            dst = workdir / f"{Path(name).stem or 'video'}_{suffix}.mp4"
            job.progress = 0.0
            await run_ffmpeg(src, dst, vf, job)
            src.unlink(missing_ok=True)
            outs.append(dst)
            job.done = i + 1
        if len(outs) == 1:
            job.result, job.is_zip = outs[0], False
        else:
            zpath = workdir / "result.zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
                for o in outs:
                    z.write(o, o.name)
            job.result, job.is_zip = zpath, True
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)


def _cleanup(job_id: str) -> None:
    JOBS.pop(job_id, None)
    shutil.rmtree(TMP / job_id, ignore_errors=True)


app = FastAPI()


@app.post("/api/jobs")
async def create_job(
    width: int = Form(...),
    height: int = Form(...),
    mode: str = Form("blur"),
    gravity: str = Form("center"),
    files: list[UploadFile] = File(...),
):
    if width < 2 or height < 2 or not files:
        raise HTTPException(400, "bad params")
    w, h = width - width % 2, height - height % 2
    vf = crop_filter(w, h, gravity) if mode == "crop" else blur_filter(w, h)
    payload = [(f.filename or "video", await f.read()) for f in files]
    job = Job(id=uuid4().hex[:12], total=len(payload))
    JOBS[job.id] = job
    asyncio.create_task(process_job(job, payload, vf, f"{w}x{h}"))
    return {"id": job.id}


@app.websocket("/api/ws/{job_id}")
async def ws(job_id: str, sock: WebSocket):
    await sock.accept()
    job = JOBS.get(job_id)
    if not job:
        await sock.send_json({"status": "error", "message": "unknown job"})
        return await sock.close()
    while True:
        await sock.send_json({
            "status": job.status, "done": job.done, "total": job.total,
            "progress": round(job.progress, 3), "message": job.message,
            "is_zip": job.is_zip,
        })
        if job.status != "processing":
            break
        await asyncio.sleep(0.25)
    await sock.close()


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.status != "done" or not job.result or not job.result.exists():
        raise HTTPException(404)
    return FileResponse(
        job.result,
        media_type="application/zip" if job.is_zip else "video/mp4",
        filename=job.result.name,
        background=BackgroundTask(_cleanup, job_id),
    )


@app.on_event("startup")
def _startup() -> None:
    TMP.mkdir(parents=True, exist_ok=True)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
