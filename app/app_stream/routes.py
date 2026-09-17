import asyncio
from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket

from ..config import TMP
from . import runner
from .state import STREAM

router = APIRouter()


@router.get("/api/stream/status")
def status():
    return asdict(STREAM)


@router.post("/api/stream/start")
async def start(
    files: list[UploadFile] = File(...),
    blocks: list[str] = Form(...),
    counts: list[str] = Form(...),
    rtmp_url: str = Form(...),
    stream_key: str = Form(...),
    width: int = Form(1920),
    height: int = Form(1080),
    fps: int = Form(30),
    video_bitrate: str = Form("4500k"),
):
    if STREAM.status in ("starting", "live"):
        raise HTTPException(409, "стрим уже идёт")
    if len(files) != len(blocks) or not files or not rtmp_url.strip() or not stream_key.strip():
        raise HTTPException(400, "bad params")
    n_blocks = max(int(b) for b in blocks) + 1
    if len(counts) != n_blocks:
        raise HTTPException(400, "bad params")
    block_counts = [max(1, int(c)) for c in counts]
    blocks_files: list[list[tuple[str, bytes]]] = [[] for _ in range(n_blocks)]
    for f, b in zip(files, blocks):
        blocks_files[int(b)].append((f.filename or "file", await f.read()))
    if any(not bf for bf in blocks_files):
        raise HTTPException(400, "every block needs at least one file")

    workdir = TMP / "stream" / uuid4().hex[:8]
    asyncio.create_task(runner.start(
        blocks_files, block_counts, rtmp_url.strip(), stream_key.strip(),
        width, height, fps, video_bitrate, workdir,
    ))
    return {"ok": True}


@router.post("/api/stream/stop")
async def stop():
    await runner.stop()
    return {"ok": True}


@router.websocket("/api/stream/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    while True:
        await sock.send_json(asdict(STREAM))
        if STREAM.status not in ("starting", "live", "stopping"):
            break
        await asyncio.sleep(0.5)
    await sock.close()
