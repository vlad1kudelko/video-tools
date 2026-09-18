import shutil
from datetime import datetime
from pathlib import Path

from ..clip_assembly import ClipInput, assemble_clips
from ..media_pool import IMAGE_CLIP_DURATION, classify_media, gather_pool
from .jobs import CombinatorJob
from .usage import counts_from_log, least_used_pick, load_log, record_usage


async def run_generate(
    job: CombinatorJob, blocks_files: list[list[tuple[str, bytes]]], block_repeats: list[int],
    transition: str, transition_duration: float, workdir: Path,
) -> None:
    try:
        job.message = "Сбор пулов"
        pools = [gather_pool(files, workdir / f"block{i}") for i, files in enumerate(blocks_files)]
        if any(not p for p in pools):
            job.status, job.message = "error", "В одном из блоков нет подходящих файлов"
            return

        job.message = "Выбор файлов"
        counts = counts_from_log(load_log())
        used_names: set[str] = set()
        picks: list[Path] = []
        for pool, repeat in zip(pools, block_repeats):
            for _ in range(repeat):
                candidates = [p for p in pool if p.name not in used_names] or pool
                chosen = least_used_pick(candidates, counts)
                picks.append(chosen)
                used_names.add(chosen.name)

        clips = [
            ClipInput(path=p, forced_duration=IMAGE_CLIP_DURATION if classify_media(p.name) == "image" else None)
            for p in picks
        ]

        job.message = "Склейка"
        out_path = workdir / f"app_combinator-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"
        await assemble_clips(clips, transition, transition_duration, out_path, job)

        record_usage([p.name for p in picks])

        job.result = out_path
        job.message = "Готово"
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "error", str(exc)
        shutil.rmtree(workdir, ignore_errors=True)
