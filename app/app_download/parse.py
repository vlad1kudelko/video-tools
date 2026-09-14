from urllib.parse import urlparse

YOUTUBE_HOSTS = ("youtube.com", "youtu.be")


def is_youtube(url: str) -> bool:
    return any(h in urlparse(url).netloc.lower() for h in YOUTUBE_HOSTS)
