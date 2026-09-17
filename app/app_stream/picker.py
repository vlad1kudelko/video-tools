import random
from pathlib import Path


class PassPicker:
    """Picks one shuffled "pass" (list of clips) at a time from the blocks'
    pools, held only in memory for the life of the running stream — no file
    or S3 bookkeeping, unlike "Комбинатор"'s persistent usage history.

    Each block contributes `count` files per pass. Within a pass, a file
    already picked (from this block or another) is avoided as long as any
    unused file remains anywhere in that block's own pool; once a block's
    pool is exhausted (count > its size, or heavy overlap with other blocks'
    pools), further picks for it fall back to repeating — same fallback
    "Комбинатор" already uses for the analogous cross-block case."""

    def __init__(self, block_pools: list[list[Path]], block_counts: list[int]):
        self._block_pools = block_pools
        self._block_counts = block_counts

    def build_pass(self) -> list[Path]:
        used_names: set[str] = set()
        picks: list[Path] = []
        for pool, count in zip(self._block_pools, self._block_counts):
            for _ in range(count):
                candidates = [p for p in pool if p.name not in used_names] or pool
                chosen = random.choice(candidates)
                picks.append(chosen)
                used_names.add(chosen.name)
        random.shuffle(picks)
        return picks
