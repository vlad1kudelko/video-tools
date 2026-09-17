import asyncio
import re
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


def _parse_fps(fps: str) -> float:
    """"30" or "30000/1001"-style ffprobe r_frame_rate strings -> float."""
    if "/" in fps:
        num, den = fps.split("/", 1)
        return float(num) / float(den)
    return float(fps)


async def assemble_clips(
    clips: list[ClipInput], transition: str, transition_duration: float,
    out_path: Path, job: _ProgressJob,
    target_size: tuple[int, int] | None = None,
    target_fps: str | None = None,
    video_bitrate: str | None = None,
    preset: str = "veryfast",
    gop_seconds: float | None = None,
) -> None:
    """Normalize every clip to the first clip's resolution/fps and chain them
    together, then mux in audio — a real track where present, silence where
    not. Shared by "Склейка" and "Комбинатор", which only differ in how they
    pick the input clip list.

    The transition (when not "none") is not an `xfade` overlap — an overlap
    necessarily shortens the video by the transition length while the audio
    (a plain concat) keeps its full length, so the two drift out of sync
    across a multi-clip chain and only line back up via an end-of-video patch.
    Instead, each clip's own trailing `td` seconds are replaced (not
    shortened away) by a "reverse echo": that tail played backwards
    cross-dissolves into the next clip's head also played backwards, landing
    on the next clip's first frame exactly at the cut, which then continues
    forward normally. Every clip still contributes exactly its own duration
    to the timeline, so the total video length is exactly sum(durations) —
    identical, by construction, to the plain audio concat's length. No
    trimming or padding needed to line them up.

    `target_size`/`target_fps` override the default of normalizing to the
    first clip's own resolution/fps — needed by callers (e.g. "Стрим") that
    render many separate, differently-ordered clip lists over time and must
    keep output geometry constant across all of them. `video_bitrate` (e.g.
    "4500k") pins the encode to a capped bitrate instead of the default
    CRF-driven one, needed for a stable live-stream feed. `preset` overrides
    the default "veryfast" x264 preset — a live-stream caller needs encoding
    to reliably outrun real-time playback, so it passes "ultrafast".
    `gop_seconds`, when given, forces a closed keyframe interval of that
    length instead of x264's own scene-cut-driven default (which can drift
    to several seconds between keyframes) — RTMP ingest (YouTube in
    particular) requires keyframes at most a few seconds apart or it warns
    about/struggles with buffering."""
    infos = []
    for c in clips:
        info = await probe(c.path)
        if c.forced_duration is not None:
            info["duration"] = c.forced_duration
        infos.append(info)
    durations = [info["duration"] or 0.1 for info in infos]
    total_duration = sum(durations)

    w, h = target_size if target_size else (infos[0]["width"] or 1280, infos[0]["height"] or 720)
    fps = target_fps or infos[0]["r_frame_rate"]

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
    elif transition == "none":
        video_parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
        video_label = "vout"
    else:
        # Each normalized clip stream [vi] feeds up to three downstream chains
        # (its own forward play, its reversed tail, and — as the *next*
        # clip's head — a reversed head for the previous junction), so it
        # needs an explicit `split` fan-out before any of those can read it.
        roles: dict[tuple[int, str], int] = {}
        for i in range(n):
            idx = 0
            roles[(i, "fwd")] = idx; idx += 1
            if i < n - 1:
                roles[(i, "tail")] = idx; idx += 1
            if i > 0:
                roles[(i, "head")] = idx; idx += 1
            outs = "".join(f"[vsp{i}_{k}]" for k in range(idx))
            video_parts.append(f"[v{i}]split={idx}{outs}")

        def copy(i: int, role: str) -> str:
            return f"vsp{i}_{roles[(i, role)]}"

        segments = []
        for i in range(n):
            is_last = i == n - 1
            if is_last:
                segments.append(copy(i, "fwd"))
            else:
                fwd = f"vf{i}"
                video_parts.append(f"[{copy(i, 'fwd')}]trim=start=0:end={durations[i] - td:.3f},setpts=PTS-STARTPTS[{fwd}]")
                segments.append(fwd)

                # `reverse` drops the constant-frame-rate flag, which `xfade`
                # below insists on — reassert it with an explicit `fps=`.
                revtail, revhead, junction = f"vrt{i}", f"vrh{i}", f"vj{i}"
                video_parts.append(f"[{copy(i, 'tail')}]trim=start={durations[i] - td:.3f}:end={durations[i]:.3f},setpts=PTS-STARTPTS,reverse,fps={fps}[{revtail}]")
                video_parts.append(f"[{copy(i + 1, 'head')}]trim=start=0:end={td:.3f},setpts=PTS-STARTPTS,reverse,fps={fps}[{revhead}]")
                video_parts.append(f"[{revtail}][{revhead}]xfade=transition={transition}:duration={td:.3f}:offset=0[{junction}]")
                segments.append(junction)
        video_label = "vout"
        video_parts.append("".join(f"[{s}]" for s in segments) + f"concat=n={len(segments)}:v=1:a=0[{video_label}]")

    audio_parts = []
    for i, info in enumerate(infos):
        if info["has_audio"]:
            audio_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")
        else:
            audio_parts.append(f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={durations[i]:.3f}[a{i}]")
    audio_parts.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]")

    filter_complex = ";".join(video_parts + audio_parts)

    bitrate_args = []
    if video_bitrate:
        m = re.match(r"^(\d+)([kKmM]?)$", video_bitrate)
        bufsize = f"{int(m.group(1)) * 2}{m.group(2)}" if m else video_bitrate
        bitrate_args = ["-b:v", video_bitrate, "-maxrate", video_bitrate, "-bufsize", bufsize]

    gop_args = []
    if gop_seconds:
        gop_frames = max(1, round(gop_seconds * _parse_fps(fps)))
        # sc_threshold 0 disables x264's scene-cut-adaptive keyframes, which
        # is what actually lets the interval drift past `-g` in the first
        # place — without it, a run of similar-looking clips can go many
        # seconds without a real scene cut and thus without a keyframe.
        gop_args = ["-g", str(gop_frames), "-keyint_min", str(gop_frames), "-sc_threshold", "0"]

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", *input_args, "-filter_complex", filter_complex,
        "-map", f"[{video_label}]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", preset, "-pix_fmt", "yuv420p", *bitrate_args, *gop_args,
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
