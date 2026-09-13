import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .domain import blur_filter, crop_filter
from .jobs import JOBS, cleanup, new_job, process_job

router = APIRouter()


@router.post("/api/jobs")
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
    job = new_job(total=len(payload))
    asyncio.create_task(process_job(job, payload, vf, f"{w}x{h}"))
    return {"id": job.id}


@router.websocket("/api/ws/{job_id}")
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


@router.get("/api/jobs/{job_id}/download")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.status != "done" or not job.result or not job.result.exists():
        raise HTTPException(404)
    return FileResponse(
        job.result,
        media_type="application/zip" if job.is_zip else "video/mp4",
        filename=job.result.name,
        background=BackgroundTask(cleanup, job_id),
    )
