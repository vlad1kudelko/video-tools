import os
from pathlib import Path

TMP = Path("/tmp/video-tools")
STATIC = Path(__file__).parent / "static"
REFRAME_STATIC = Path(__file__).parent / "app_reframe" / "static"
MATERIALS_STATIC = Path(__file__).parent / "app_materials" / "static"
DOWNLOAD_STATIC = Path(__file__).parent / "app_download" / "static"
CONCAT_STATIC = Path(__file__).parent / "app_concat" / "static"
RECORD_STATIC = Path(__file__).parent / "app_record" / "static"
COMBINATOR_STATIC = Path(__file__).parent / "app_combinator" / "static"
LIGHTPANDA_CDP_URL = os.environ.get("LIGHTPANDA_CDP_URL", "http://127.0.0.1:9222")
WITH_BROWSER = os.environ.get("WITH_BROWSER", "false").lower() == "true"

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
S3_REGION = os.environ.get("S3_REGION", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
