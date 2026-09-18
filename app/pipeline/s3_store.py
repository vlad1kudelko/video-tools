import json
from uuid import uuid4

import boto3

from ..config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT, S3_REGION, S3_SECRET_KEY

PRESETS_PREFIX = "pipelines/presets/"
GRAPHS_PREFIX = "pipelines/graphs/"

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


def list_presets() -> list[str]:
    resp = _s3().list_objects_v2(Bucket=S3_BUCKET, Prefix=PRESETS_PREFIX)
    return sorted(
        obj["Key"][len(PRESETS_PREFIX):-len(".json")]
        for obj in resp.get("Contents", [])
        if obj["Key"].endswith(".json")
    )


def get_preset(name: str) -> dict | None:
    client = _s3()
    try:
        body = client.get_object(Bucket=S3_BUCKET, Key=f"{PRESETS_PREFIX}{name}.json")["Body"].read()
    except client.exceptions.NoSuchKey:
        return None
    return json.loads(body)


def save_preset(name: str, graph: dict) -> None:
    _s3().put_object(
        Bucket=S3_BUCKET, Key=f"{PRESETS_PREFIX}{name}.json",
        Body=json.dumps(graph, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def save_graph(graph: dict) -> str:
    graph_id = uuid4().hex[:12]
    _s3().put_object(
        Bucket=S3_BUCKET, Key=f"{GRAPHS_PREFIX}{graph_id}.json",
        Body=json.dumps(graph, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return graph_id


def get_graph(graph_id: str) -> dict | None:
    client = _s3()
    try:
        body = client.get_object(Bucket=S3_BUCKET, Key=f"{GRAPHS_PREFIX}{graph_id}.json")["Body"].read()
    except client.exceptions.NoSuchKey:
        return None
    return json.loads(body)
