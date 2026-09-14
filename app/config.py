import os
from pathlib import Path

TMP = Path("/tmp/video-tools")
STATIC = Path(__file__).parent / "static"
VIDEO_STATIC = Path(__file__).parent / "video" / "static"
MATERIALS_STATIC = Path(__file__).parent / "materials" / "static"
LIGHTPANDA_CDP_URL = os.environ.get("LIGHTPANDA_CDP_URL", "http://127.0.0.1:9222")
