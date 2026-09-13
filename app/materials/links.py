import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".avif", ".bmp", ".tiff"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}
VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com")
BADGE_HOSTS = ("shields.io", "badge.fury.io", "codecov.io", "coveralls.io")
BADGE_PATH_RE = re.compile(r"/(?:workflows|actions/workflows)/[^/]+/badge\.svg")

_MD_IMAGE_RE = re.compile(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_MD_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_HTML_SRC_RE = re.compile(r'<(?:img|source|video)\b[^>]*?\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_HTML_SRCSET_RE = re.compile(r'<source\b[^>]*?\bsrcset=["\']([^"\']+)["\']', re.IGNORECASE)
_BARE_URL_RE = re.compile(r'https?://[^\s)>"\'<]+')


@dataclass
class MediaLink:
    url: str
    kind: str  # image | gif | video
    source: str  # readme | site


def classify(url: str) -> str | None:
    """Video hosts win regardless of extension; otherwise classify by file extension."""
    host = urlparse(url).netloc.lower()
    if any(h in host for h in VIDEO_HOSTS):
        return "video"
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    if ext == ".gif":
        return "gif"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return None


def is_badge(url: str) -> bool:
    parsed = urlparse(url)
    if any(h in parsed.netloc.lower() for h in BADGE_HOSTS):
        return True
    return bool(BADGE_PATH_RE.search(parsed.path))


def extract_media(text: str, base_url: str, source: str) -> list["MediaLink"]:
    """Find media links in markdown (README) or raw HTML (site) text.

    Same extractor for both: markdown image syntax simply won't match HTML
    and vice versa, so it's safe to run every pattern against either input.
    """
    candidates: list[str] = []
    candidates += _MD_IMAGE_RE.findall(text)
    candidates += _HTML_SRC_RE.findall(text)
    candidates += [srcset.split(",")[0].strip().split(" ")[0] for srcset in _HTML_SRCSET_RE.findall(text)]
    candidates += _MD_LINK_RE.findall(text)
    candidates += _BARE_URL_RE.findall(text)

    seen: set[str] = set()
    result: list[MediaLink] = []
    for raw in candidates:
        url = urljoin(base_url, raw.strip().rstrip(").,"))
        if url in seen or is_badge(url):
            continue
        kind = classify(url)
        if kind is None:
            continue
        seen.add(url)
        result.append(MediaLink(url=url, kind=kind, source=source))
    return result
