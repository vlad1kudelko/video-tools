import asyncio
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .downloader import run_download
from .jobs import JOBS, cleanup, new_job

router = APIRouter()


@router.post("/api/downloads/start")
async def start(file: UploadFile = File(...)):
    raw = (await file.read()).decode("utf-8", errors="ignore")
    job = new_job()
    job.filename = f"{Path(file.filename).stem}.zip" if file.filename else "media.zip"
    asyncio.create_task(run_download(job, raw))
    return {"id": job.id}


@router.websocket("/api/downloads/ws/{job_id}")
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
            "filename": job.filename,
            "total": job.total,
            "done": job.done,
            "current_name": job.current_name,
            "current_progress": round(job.current_progress, 3),
            "skipped_youtube": job.skipped_youtube,
        })
        if job.status != "processing":
            break
        await asyncio.sleep(0.25)
    await sock.close()


@router.get("/api/downloads/{job_id}/file")
def download_result(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.status != "done" or not job.result or not job.result.exists():
        raise HTTPException(404)
    return FileResponse(
        job.result,
        media_type="application/zip",
        filename=job.filename,
        background=BackgroundTask(cleanup, job_id),
    )
