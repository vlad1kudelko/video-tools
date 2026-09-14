import os
from pathlib import Path

TMP = Path("/tmp/video-tools")
STATIC = Path(__file__).parent / "static"
REFRAME_STATIC = Path(__file__).parent / "app_reframe" / "static"
MATERIALS_STATIC = Path(__file__).parent / "app_materials" / "static"
DOWNLOAD_STATIC = Path(__file__).parent / "app_download" / "static"
CONCAT_STATIC = Path(__file__).parent / "app_concat" / "static"
RECORD_STATIC = Path(__file__).parent / "app_record" / "static"
LIGHTPANDA_CDP_URL = os.environ.get("LIGHTPANDA_CDP_URL", "http://127.0.0.1:9222")
