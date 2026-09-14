import asyncio

from fastapi import APIRouter, Form, HTTPException, WebSocket
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..config import TMP
from .jobs import JOBS, cleanup, new_job
from .record import run_record

router = APIRouter()


@router.post("/api/record/start")
async def start(
    url: str = Form(...),
    width: int = Form(1080),
    height: int = Form(1920),
    scroll_speed: float = Form(250.0),
    max_seconds: float = Form(60.0),
):
    if not url.strip() or width < 2 or height < 2 or scroll_speed <= 0 or max_seconds <= 0:
        raise HTTPException(400, "bad params")
    w, h = width - width % 2, height - height % 2
    job = new_job()
    workdir = TMP / job.id
    asyncio.create_task(run_record(job, url.strip(), w, h, workdir, scroll_speed, max_seconds))
    return {"id": job.id}


@router.websocket("/api/record/ws/{job_id}")
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


@router.get("/api/record/{job_id}/file")
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
