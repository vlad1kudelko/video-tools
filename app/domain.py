from dataclasses import dataclass
from pathlib import Path


@dataclass
class Job:
    id: str
    total: int
    done: int = 0
    progress: float = 0.0
    status: str = "processing"  # processing | done | error
    message: str = ""
    result: Path | None = None
    is_zip: bool = False


CROP_XY = {
    "center": "",
    "left": ":0:(ih-oh)/2",
    "right": ":iw-ow:(ih-oh)/2",
    "top": ":(iw-ow)/2:0",
    "bottom": ":(iw-ow)/2:ih-oh",
}


def blur_filter(w: int, h: int) -> str:
    """Scale the video to fit and fill the padding with a blurred cover of itself."""
    return (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},gblur=sigma=25,eq=brightness=-0.1[bg];"
        f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
    )


def crop_filter(w: int, h: int, gravity: str) -> str:
    """Scale to cover the target and crop the overflow toward the given edge."""
    return (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h}{CROP_XY.get(gravity, '')},setsar=1"
    )
