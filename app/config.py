import os
from pathlib import Path

TMP = Path("/tmp/video-tools")
STATIC = Path(__file__).parent / "static"
REFRAME_STATIC = Path(__file__).parent / "app_reframe" / "static"
MATERIALS_STATIC = Path(__file__).parent / "app_materials" / "static"
LIGHTPANDA_CDP_URL = os.environ.get("LIGHTPANDA_CDP_URL", "http://127.0.0.1:9222")
