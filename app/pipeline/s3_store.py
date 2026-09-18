import json

import boto3

from ..config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT, S3_REGION, S3_SECRET_KEY

GRAPH_KEY = "pipelines/graph.json"

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
