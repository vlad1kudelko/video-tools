from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".avif"}
GIF_EXT = {".gif"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv"}


def classify_media(name: str) -> str | None:
    """image | gif | video | None (not a recognized media type — left
    untouched when found inside an archive alongside real media files)."""
    ext = Path(name).suffix.lower()
    if ext in GIF_EXT:
        return "gif"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return None
