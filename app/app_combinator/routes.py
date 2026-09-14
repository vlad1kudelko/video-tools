import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..config import TMP
from .combinator import run_generate
from .jobs import JOBS, cleanup, new_job

router = APIRouter()


@router.post("/api/combinator/generate")
async def generate(
    files: list[UploadFile] = File(...),
    blocks: list[str] = Form(...),
    repeats: list[str] = Form(...),
    transition: str = Form("fade"),
    transition_duration: float = Form(0.5),
):
    if len(files) != len(blocks) or not files:
        raise HTTPException(400, "bad params")
    n_blocks = max(int(b) for b in blocks) + 1
    if len(repeats) != n_blocks:
        raise HTTPException(400, "bad params")
    block_repeats = [max(1, int(r)) for r in repeats]
    blocks_files: list[list[tuple[str, bytes]]] = [[] for _ in range(n_blocks)]
    for f, b in zip(files, blocks):
        blocks_files[int(b)].append((f.filename or "file", await f.read()))
    if any(not bf for bf in blocks_files):
        raise HTTPException(400, "every block needs at least one file")

    job = new_job()
    workdir = TMP / job.id
    asyncio.create_task(run_generate(job, blocks_files, block_repeats, transition, transition_duration, workdir))
    return {"id": job.id}


@router.websocket("/api/combinator/ws/{job_id}")
async def ws(job_id: str, sock: WebSocket):
    await sock.accept()
    job = JOBS.get(job_id)
    if not job:
        await sock.send_json({"status": "error", "message": "unknown job"})
        return await sock.close()
    while True:
        await sock.send_json({
            "status": job.status,
            "message": job.message,
            "progress": round(job.progress, 3),
        })
        if job.status != "processing":
            break
        await asyncio.sleep(0.25)
    await sock.close()


@router.get("/api/combinator/{job_id}/file")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.status != "done" or not job.result or not job.result.exists():
        raise HTTPException(404)
    return FileResponse(
        job.result,
        media_type="video/mp4",
        filename=job.result.name,
        background=BackgroundTask(cleanup, job_id),
    )
