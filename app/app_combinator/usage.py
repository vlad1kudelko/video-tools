import random
from datetime import datetime
from pathlib import Path

import boto3
import yaml

from ..config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT, S3_REGION, S3_SECRET_KEY

# A deliberately visible, hand-inspectable history of every generation: when it
# ran and which source files it picked. Lives in S3 rather than on the app's
# disk so it survives container recreation and stays readable from anywhere.
# Also doubles as the balancing signal — pick counts are tallied from this same
# log, so the same block pools stay used evenly across many separate runs.
USAGE_KEY = "combinator-usage.yaml"

_client = None


def _s3():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            region_name=S3_REGION,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
        )
    return _client


def load_log() -> list[dict]:
    client = _s3()
    try:
        body = client.get_object(Bucket=S3_BUCKET, Key=USAGE_KEY)["Body"].read()
    except client.exceptions.NoSuchKey:
        return []
    data = yaml.safe_load(body.decode("utf-8")) or []
    return data if isinstance(data, list) else []


def _save(log: list[dict]) -> None:
    _s3().put_object(
        Bucket=S3_BUCKET,
        Key=USAGE_KEY,
        Body=yaml.safe_dump(log, allow_unicode=True, sort_keys=False).encode("utf-8"),
        ContentType="text/yaml; charset=utf-8",
    )


def counts_from_log(log: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in log:
        for name in entry.get("files", []):
            counts[name] = counts.get(name, 0) + 1
    return counts


def least_used_pick(candidates: list[Path], counts: dict[str, int]) -> Path:
    """Pick randomly among whichever candidates have been used the fewest
    times so far (per the history log), so repeated generations from the same
    pool spread evenly across its files instead of favoring whatever
    random.choice happens to land on most often."""
    min_count = min(counts.get(p.name, 0) for p in candidates)
    least = [p for p in candidates if counts.get(p.name, 0) == min_count]
    return random.choice(least)


def record_usage(names: list[str]) -> None:
    log = load_log()
    log.append({"date": datetime.now().isoformat(timespec="seconds"), "files": names})
    _save(log)
