import random
from pathlib import Path

import yaml

# Project root, not app/ — a deliberately visible, hand-inspectable record of
# which source files have been used, so the same block pools stay balanced
# across many separate "Сгенерировать" runs.
USAGE_FILE = Path(__file__).resolve().parents[2] / "combinator-usage.yaml"


def _load() -> dict[str, int]:
    if not USAGE_FILE.exists():
        return {}
    data = yaml.safe_load(USAGE_FILE.read_text(encoding="utf-8")) or {}
    return {str(k): int(v) for k, v in data.items()}


def _save(counts: dict[str, int]) -> None:
    USAGE_FILE.write_text(yaml.safe_dump(counts, allow_unicode=True, sort_keys=True), encoding="utf-8")


def least_used_pick(candidates: list[Path]) -> Path:
    """Pick randomly among whichever candidates have been used the fewest
    times so far, so repeated generations from the same pool spread evenly
    across its files instead of favoring whatever random.choice happens to
    land on most often."""
    counts = _load()
    min_count = min(counts.get(p.name, 0) for p in candidates)
    least = [p for p in candidates if counts.get(p.name, 0) == min_count]
    return random.choice(least)


def record_usage(names: list[str]) -> None:
    counts = _load()
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    _save(counts)
