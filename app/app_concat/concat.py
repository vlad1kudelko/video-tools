import asyncio
import shutil
import zipfile
from pathlib import Path

from .jobs import ConcatJob
from .probe import probe

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}


def _is_video(name: str) -> bool:
    return Path(name).suffix.lower() in VIDEO_EXT


async def _run_ffmpeg_concat(
    clips: list[Path], infos: list[dict], durations: list[float],
    w: int, h: int, fps: str, transition: str, td: float,
    out_path: Path, job: ConcatJob,
) -> None:
    n = len(clips)
    input_args = []
    for c in clips:
        input_args += ["-i", str(c)]

    video_parts = [
        f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{i}]"
        for i in range(n)
    ]

    if n == 1:
        video_label = "v0"
        total_duration = durations[0]
    elif transition == "none":
        video_parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
        video_label = "vout"
        total_duration = sum(durations)
    else:
        cumulative = durations[0]
        prev_label = "v0"
        for i in range(1, n):
            offset = max(cumulative - td, 0)
            out_label = f"vx{i}" if i < n - 1 else "vout"
            video_parts.append(f"[{prev_label}][v{i}]xfade=transition={transition}:duration={td}:offset={offset:.3f}[{out_label}]")
            cumulative = cumulative + durations[i] - td
            prev_label = out_label
        video_label = prev_label
        total_duration = cumulative

    audio_parts = []
    for i, info in enumerate(infos):
        if info["has_audio"]:
            audio_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")
        else:
            audio_parts.append(f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={durations[i]:.3f}[a{i}]")
    audio_parts.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[araw]")
    # Transitions overlap clips, shortening the video below the sum of clip
    # durations — trim the (plainly concatenated) audio to match, otherwise
    # the container duration follows the longer, untrimmed audio track.
    audio_parts.append(f"[araw]atrim=duration={total_duration:.3f},asetpts=PTS-STARTPTS[aout]")

    filter_complex = ";".join(video_parts + audio_parts)

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", *input_args, "-filter_complex", filter_complex,
        "-map", f"[{video_label}]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats", str(out_path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    async for raw in proc.stdout:
        line = raw.decode().strip()
        if line.startswith("out_time=") and total_duration:
            try:
                hh, mm, ss = line.split("=", 1)[1].split(":")
                job.progress = min((int(hh) * 3600 + int(mm) * 60 + float(ss)) / total_duration, 1.0)
            except ValueError:
                pass
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg concat failed")
    job.progress = 1.0


async def run_concat(
    job: ConcatJob, zip_bytes: bytes, original_name: str,
    transition: str, transition_duration: float, workdir: Path,
) -> None:
    extract_dir = workdir / "in"
    extract_dir.mkdir(parents=True, exist_ok=True)
    src_zip = workdir / "upload.zip"
    src_zip.write_bytes(zip_bytes)

    try:
        job.message = "Распаковка архива"
        with zipfile.ZipFile(src_zip, "r") as zin:
            names = [i.filename for i in zin.infolist() if not i.is_dir()]
            zin.extractall(extract_dir)

        clip_names = sorted(n for n in names if _is_video(n))

        if not clip_names:
            job.status, job.message = "error", "В архиве не найдено видео для склейки"
            return

        clips = [extract_dir / n for n in clip_names]

        job.message = "Анализ клипов"
        infos = [await probe(c) for c in clips]
        durations = [info["duration"] or 0.1 for info in infos]

        w = infos[0]["width"] or 1280
        h = infos[0]["height"] or 720
        fps = infos[0]["r_frame_rate"]

        td = transition_duration
        if len(clips) > 1:
            td = min(td, 0.4 * min(durations))

        out_path = workdir / f"{Path(original_name).stem}[concat].mp4"

        job.message = "Склейка"
        await _run_ffmpeg_concat(clips, infos, durations, w, h, fps, transition, td, out_path, job)

        job.result = out_path
        job.message = "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)
