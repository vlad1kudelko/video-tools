import shutil
import zipfile
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".avif"}
GIF_EXT = {".gif"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv"}
IMAGE_CLIP_DURATION = 3.0


def classify_media(name: str) -> str | None:
    ext = Path(name).suffix.lower()
    if ext in GIF_EXT:
        return "gif"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return None


def gather_pool(files: list[tuple[str, bytes]], pool_dir: Path) -> list[Path]:
    """Unzip any archive among `files`, classify everything (direct uploads and
    archive contents alike), and return the paths of recognized media."""
    pool_dir.mkdir(parents=True, exist_ok=True)
    pool: list[Path] = []
    for name, data in files:
        if name.lower().endswith(".zip"):
            zpath = pool_dir / "src.zip"
            zpath.write_bytes(data)
            with zipfile.ZipFile(zpath) as z:
                for info in z.infolist():
                    if info.is_dir() or classify_media(info.filename) is None:
                        continue
                    dst = pool_dir / Path(info.filename).name
                    with z.open(info) as src, open(dst, "wb") as out:
                        shutil.copyfileobj(src, out)
                    pool.append(dst)
            zpath.unlink(missing_ok=True)
        elif classify_media(name) is not None:
            dst = pool_dir / name
            dst.write_bytes(data)
            pool.append(dst)
    return pool
