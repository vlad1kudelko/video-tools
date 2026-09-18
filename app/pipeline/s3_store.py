import json

import boto3

from ..config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT, S3_REGION, S3_SECRET_KEY

GRAPH_KEY = "system/graph.json"

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


def save_graph(graph: dict) -> None:
    _s3().put_object(
        Bucket=S3_BUCKET, Key=GRAPH_KEY,
        Body=json.dumps(graph, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def get_graph() -> dict | None:
    client = _s3()
    try:
        body = client.get_object(Bucket=S3_BUCKET, Key=GRAPH_KEY)["Body"].read()
    except client.exceptions.NoSuchKey:
        return None
    return json.loads(body)


def list_files() -> list[dict]:
    """Every object in the bucket except the app's own "system/" housekeeping
    (saved graph, combinator usage log) — i.e. whatever the user has uploaded
    through the hoster's own S3 admin panel, available to pick from a
    pipeline node."""
    client = _s3()
    files = []
    token = None
    while True:
        kwargs = {"Bucket": S3_BUCKET}
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.startswith("system/") or key.endswith("/"):
                continue
            files.append({"key": key, "name": key.rsplit("/", 1)[-1], "size": obj["Size"]})
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    files.sort(key=lambda f: f["key"])
    return files


def get_object(key: str) -> bytes:
    return _s3().get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
