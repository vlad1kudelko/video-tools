import asyncio

from fastapi import APIRouter, Form, WebSocket

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
            "filename": job.filename,
            "items": [{"url": i.url, "kind": i.kind, "source": i.source} for i in job.items],
        })
        if job.status != "scanning":
            break
        await asyncio.sleep(0.25)
    await sock.close()
    cleanup(job_id)
