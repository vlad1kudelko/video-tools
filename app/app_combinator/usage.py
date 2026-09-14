import random
from datetime import datetime
from pathlib import Path

import yaml

# Project root, not app/ — a deliberately visible, hand-inspectable history of
# every generation: when it ran and which source files it picked. Also doubles
# as the balancing signal — pick counts are tallied from this same log, so the
# same block pools stay used evenly across many separate "Сгенерировать" runs.
USAGE_FILE = Path(__file__).resolve().parents[2] / "combinator-usage.yaml"


def _load() -> list[dict]:
    if not USAGE_FILE.exists():
        return []
    data = yaml.safe_load(USAGE_FILE.read_text(encoding="utf-8")) or []
    return data if isinstance(data, list) else []


def _save(log: list[dict]) -> None:
    USAGE_FILE.write_text(yaml.safe_dump(log, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _counts(log: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in log:
        for name in entry.get("files", []):
            counts[name] = counts.get(name, 0) + 1
    return counts


def least_used_pick(candidates: list[Path]) -> Path:
    """Pick randomly among whichever candidates have been used the fewest
    times so far (per the history log), so repeated generations from the same
    pool spread evenly across its files instead of favoring whatever
    random.choice happens to land on most often."""
    counts = _counts(_load())
    min_count = min(counts.get(p.name, 0) for p in candidates)
    least = [p for p in candidates if counts.get(p.name, 0) == min_count]
    return random.choice(least)


def record_usage(names: list[str]) -> None:
    log = _load()
    log.append({"date": datetime.now().isoformat(timespec="seconds"), "files": names})
    _save(log)
