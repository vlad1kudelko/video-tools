import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".avif", ".bmp", ".tiff"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}
VIDEO_HOSTS = ("youtube.com", "youtu.be")  # by far the most common — not worth chasing others

_MD_IMAGE_RE = re.compile(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_MD_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_IMG_SRC_RE = re.compile(r'<img\b[^>]*?\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_VIDEO_SRC_RE = re.compile(r'<video\b[^>]*?\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_SOURCE_SRC_RE = re.compile(r'<source\b[^>]*?\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_SOURCE_SRCSET_RE = re.compile(r'<source\b[^>]*?\bsrcset=["\']([^"\']+)["\']', re.IGNORECASE)
_BARE_URL_RE = re.compile(r'https?://[^\s)>"\'<]+')


@dataclass
class MediaLink:
    url: str
    kind: str  # image | gif | video | other
    source: str  # readme | site


def classify_media_tag(url: str) -> str:
    """URL found in an <img>/<source>/markdown-image tag: already known to be an
    image, so don't require a recognizable extension (GitHub's own upload links,
    e.g. github.com/user-attachments/assets/<uuid>, carry none)."""
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    if ext == ".gif":
        return "gif"
    if ext in VIDEO_EXT:
        return "video"
    return "image"


def classify_link(url: str) -> str:
    """Plain text/markdown link, not inherently known to be media: image/gif/video
    only when a recognizable extension or YouTube says so; otherwise 'other' —
    kept for a human to skim rather than silently dropped."""
    if any(h in urlparse(url).netloc.lower() for h in VIDEO_HOSTS):
        return "video"
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    if ext == ".gif":
        return "gif"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return "other"


def extract_media(text: str, base_url: str, source: str) -> list["MediaLink"]:
    """Find links in markdown (README) or raw HTML (site) text. Media tags always
    become image/gif/video; every other link is still kept, tagged 'other', so
    nothing found gets silently thrown away."""
    media_tag_urls = (
        _MD_IMAGE_RE.findall(text)
        + _IMG_SRC_RE.findall(text)
        + _SOURCE_SRC_RE.findall(text)
        + [s.split(",")[0].strip().split(" ")[0] for s in _SOURCE_SRCSET_RE.findall(text)]
    )
    found: list[tuple[str, str]] = [(u, classify_media_tag(u)) for u in media_tag_urls]
    found += [(u, "video") for u in _VIDEO_SRC_RE.findall(text)]

    link_urls = _MD_LINK_RE.findall(text) + _BARE_URL_RE.findall(text)
    found += [(u, classify_link(u)) for u in link_urls]

    seen: set[str] = set()
    result: list[MediaLink] = []
    for raw, kind in found:
        url = urljoin(base_url, raw.strip().rstrip(").,"))
        if url in seen:
            continue
        seen.add(url)
        result.append(MediaLink(url=url, kind=kind, source=source))
    return result
