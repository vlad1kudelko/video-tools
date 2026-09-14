import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..config import TMP
from .concat import run_concat
from .jobs import JOBS, cleanup, new_job

router = APIRouter()


@router.post("/api/concat/start")
async def start(
    file: UploadFile = File(...),
    transition: str = Form("fade"),
    transition_duration: float = Form(0.5),
):
    data = await file.read()
    job = new_job()
    workdir = TMP / job.id
    asyncio.create_task(run_concat(job, data, file.filename or "video", transition, transition_duration, workdir))
    return {"id": job.id}


@router.websocket("/api/concat/ws/{job_id}")
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
            "warning": job.warning,
            "progress": round(job.progress, 3),
        })
        if job.status != "processing":
            break
        await asyncio.sleep(0.25)
    await sock.close()


@router.get("/api/concat/{job_id}/file")
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
