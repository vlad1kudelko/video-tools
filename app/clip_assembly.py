import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .media_probe import probe


@dataclass
class ClipInput:
    path: Path
    forced_duration: float | None = None  # set for a still image: loop it into a clip this long


class _ProgressJob(Protocol):
    progress: float


async def assemble_clips(
    clips: list[ClipInput], transition: str, transition_duration: float,
    out_path: Path, job: _ProgressJob,
) -> None:
    """Normalize every clip to the first clip's resolution/fps, chain them with
    an `xfade` transition (or a plain concat if transition == "none"), and mux
    in audio — a real track where present, silence where not. Shared by
    "Склейка" and "Комбинатор", which only differ in how they pick the input
    clip list."""
    infos = []
    for c in clips:
        info = await probe(c.path)
        if c.forced_duration is not None:
            info["duration"] = c.forced_duration
        infos.append(info)
    durations = [info["duration"] or 0.1 for info in infos]

    w = infos[0]["width"] or 1280
    h = infos[0]["height"] or 720
    fps = infos[0]["r_frame_rate"]

    td = transition_duration
    if len(clips) > 1:
        td = min(td, 0.4 * min(durations))

    n = len(clips)
    input_args = []
    for c, info in zip(clips, infos):
        if c.forced_duration is not None:
            input_args += ["-loop", "1", "-t", str(c.forced_duration), "-i", str(c.path)]
        else:
            input_args += ["-i", str(c.path)]

    video_parts = [
        f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{i}]"
        for i in range(n)
    ]

    if n == 1:
        video_label = "v0"
        video_duration = durations[0]
    elif transition == "none":
        video_parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
        video_label = "vout"
        video_duration = sum(durations)
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
        video_duration = cumulative

    # Audio is a plain concat of every clip's *full* track (no crossfade), so
    # its natural length is the sum of all clip durations — longer than the
    # xfade-shortened video by the total transition overlap. Rather than
    # trimming the audio down to the video's length (which would chop the
    # last clip's tail, cutting off speech), pad the video out to match the
    # audio instead: freeze its last frame for the difference. Nothing in
    # either stream gets lost.
    total_duration = sum(durations)
    pad = total_duration - video_duration
    if pad > 0.01:
        video_parts.append(f"[{video_label}]tpad=stop_mode=clone:stop_duration={pad:.3f}[vpad]")
        video_label = "vpad"

    audio_parts = []
    for i, info in enumerate(infos):
        if info["has_audio"]:
            audio_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")
        else:
            audio_parts.append(f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={durations[i]:.3f}[a{i}]")
    audio_parts.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]")

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
