import asyncio

from fastapi import APIRouter, Form, HTTPException, WebSocket
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .jobs import JOBS, cleanup, new_job
from .scan import run_scan

router = APIRouter()


@router.post("/api/materials/scan")
async def create_scan(repo_url: str = Form(...)):
    job = new_job()
    asyncio.create_task(run_scan(job, repo_url))
    return {"id": job.id}


@router.websocket("/api/materials/ws/{job_id}")
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
            "items": [{"url": i.url, "kind": i.kind, "source": i.source} for i in job.items],
        })
        if job.status != "scanning":
            break
        await asyncio.sleep(0.25)
    await sock.close()


@router.get("/api/materials/{job_id}/download")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.status != "done" or not job.result or not job.result.exists():
        raise HTTPException(404)
    return FileResponse(
        job.result,
        media_type="text/plain",
        filename="links.txt",
        background=BackgroundTask(cleanup, job_id),
    )
