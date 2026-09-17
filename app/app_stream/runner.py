import asyncio
import shutil
from pathlib import Path
from typing import Iterator

from ..clip_assembly import ClipInput, assemble_clips
from ..media_pool import IMAGE_CLIP_DURATION, classify_media, gather_pool
from .picker import PassPicker
from .state import STREAM

# How many clips to keep pre-rendered ahead of what's currently being fed.
# The render loop races ahead independently of the feed loop (bounded by this
# queue's maxsize), so a single slow render doesn't stall the RTMP feed —
# YouTube's "not receiving enough video" warning is exactly what happens when
# there's no such cushion and any one clip's encode can't outrun its own
# playback duration.
QUEUE_SIZE = 3

_task: asyncio.Task | None = None
_muxer: asyncio.subprocess.Process | None = None
_feeder: asyncio.subprocess.Process | None = None
_picker: PassPicker | None = None


class _NullJob:
    """Satisfies clip_assembly's `_ProgressJob` protocol — per-clip renders
    here don't drive a UI progress bar, so nothing ever reads this."""

    progress: float = 0.0


_null_job = _NullJob()


def _clip_source(picker: PassPicker) -> Iterator[Path]:
    """Infinite stream of source paths, building a fresh pass (and bumping
    STREAM.pass_number) each time the previous one runs out. Crossing a pass
    boundary is transparent to callers — they just keep pulling paths."""
    while True:
        pass_files = picker.build_pass()
        STREAM.pass_number += 1
        yield from pass_files


async def _render_clip(src: Path, seq: int, workdir: Path, width: int, height: int, fps: int, video_bitrate: str) -> Path:
    clip = ClipInput(path=src, forced_duration=IMAGE_CLIP_DURATION if classify_media(src.name) == "image" else None)
    out_path = workdir / f"clip-{seq}.mp4"
    await assemble_clips(
        [clip], "none", 0, out_path, _null_job,
        target_size=(width, height), target_fps=str(fps), video_bitrate=video_bitrate,
        preset="ultrafast", gop_seconds=2.0,
    )
    return out_path


async def _render_loop(queue: "asyncio.Queue[tuple[Path, Path]]", workdir: Path, width: int, height: int, fps: int, video_bitrate: str) -> None:
    """Continuously renders clips into `queue`, independently of feed pace.
    `queue`'s maxsize provides backpressure — once it's full, rendering just
    waits, so disk usage stays bounded regardless of how far ahead this gets."""
    seq = 0
    for src in _clip_source(_picker):
        seq += 1
        rendered = await _render_clip(src, seq, workdir, width, height, fps, video_bitrate)
        await queue.put((src, rendered))


async def _feed_clip(path: Path, muxer: asyncio.subprocess.Process) -> None:
    global _feeder
    feeder = await asyncio.create_subprocess_exec(
        "ffmpeg", "-re", "-i", str(path), "-c", "copy", "-f", "mpegts", "pipe:1",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    _feeder = feeder
    try:
        while True:
            chunk = await feeder.stdout.read(65536)
            if not chunk:
                break
            muxer.stdin.write(chunk)
            await muxer.stdin.drain()
    finally:
        # On cancellation (mid `-re` playback) the feeder is still very much
        # alive — awaiting it without terminating first would hang forever.
        if feeder.returncode is None:
            feeder.terminate()
        await feeder.wait()
        _feeder = None
    if feeder.returncode not in (0, None):
        raise RuntimeError("feeder ffmpeg failed")


async def _feed_loop(queue: "asyncio.Queue[tuple[Path, Path]]", rtmp_target: str) -> None:
    global _muxer
    STREAM.message = "Подключение к RTMP"
    muxer = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-f", "mpegts", "-i", "pipe:0", "-c", "copy", "-f", "flv", rtmp_target,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _muxer = muxer

    stderr_tail: list[bytes] = []

    async def _drain_stderr() -> None:
        async for line in muxer.stderr:
            stderr_tail.append(line)
            del stderr_tail[:-40]

    drain_task = asyncio.create_task(_drain_stderr())
    try:
        while True:
            src, rendered = await queue.get()
            if muxer.returncode is not None:
                raise RuntimeError("RTMP-соединение оборвалось: " + b"".join(stderr_tail).decode(errors="replace")[-500:])
            STREAM.current_file = src.name
            STREAM.status = "live"
            STREAM.message = ""
            await _feed_clip(rendered, muxer)
            rendered.unlink(missing_ok=True)
    finally:
        drain_task.cancel()
        if muxer.returncode is None:
            try:
                muxer.stdin.close()
            except Exception:  # noqa: BLE001
                pass
            muxer.terminate()
            await muxer.wait()


async def _run(rtmp_target: str, width: int, height: int, fps: int, video_bitrate: str, workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    STREAM.status = "starting"
    STREAM.message = "Подготовка буфера"

    queue: "asyncio.Queue[tuple[Path, Path]]" = asyncio.Queue(maxsize=QUEUE_SIZE)
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_render_loop(queue, workdir, width, height, fps, video_bitrate))
            tg.create_task(_feed_loop(queue, rtmp_target))
    except* Exception as eg:  # noqa: BLE001
        # A plain CancelledError from an external stop() propagates straight
        # through here untouched (it isn't an Exception, so no `except*`
        # clause matches it) — this only fires for genuine failures.
        first = eg.exceptions[0] if eg.exceptions else None
        STREAM.status, STREAM.message = "error", (str(first) if first else "неизвестная ошибка")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        if STREAM.status != "error":
            STREAM.status = "idle"
        STREAM.current_file = ""


async def start(
    blocks_files: list[list[tuple[str, bytes]]], block_counts: list[int],
    rtmp_url: str, stream_key: str, width: int, height: int, fps: int, video_bitrate: str,
    workdir: Path,
) -> None:
    global _task, _picker
    STREAM.status, STREAM.message, STREAM.pass_number, STREAM.current_file = "starting", "Сбор пулов", 0, ""

    pools = [gather_pool(files, workdir / f"block{i}") for i, files in enumerate(blocks_files)]
    if any(not p for p in pools):
        STREAM.status, STREAM.message = "error", "В одном из блоков нет подходящих файлов"
        shutil.rmtree(workdir, ignore_errors=True)
        return

    _picker = PassPicker(pools, block_counts)
    target = rtmp_url.rstrip("/") + "/" + stream_key.lstrip("/")
    _task = asyncio.create_task(_run(target, width, height, fps, video_bitrate, workdir))


async def stop() -> None:
    global _task, _muxer, _feeder
    if STREAM.status not in ("starting", "live", "error"):
        return
    STREAM.status = "stopping"
    if _feeder is not None and _feeder.returncode is None:
        _feeder.terminate()
    if _muxer is not None and _muxer.returncode is None:
        try:
            _muxer.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        _muxer.terminate()
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
    _muxer = None
    _feeder = None
    STREAM.status, STREAM.message, STREAM.current_file = "idle", "", ""
