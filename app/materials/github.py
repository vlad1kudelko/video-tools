import re

import httpx

API = "https://api.github.com"

_REPO_RE = re.compile(
    r"^(?:https?://github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$"
)


class RepoNotFound(Exception):
    pass


def parse_repo(url: str) -> tuple[str, str] | None:
    m = _REPO_RE.match(url.strip())
    return (m.group(1), m.group(2)) if m else None


async def fetch_repo_info(client: httpx.AsyncClient, owner: str, repo: str) -> dict:
    r = await client.get(f"{API}/repos/{owner}/{repo}", headers={"Accept": "application/vnd.github+json"})
    if r.status_code == 404:
        raise RepoNotFound(f"{owner}/{repo}")
    r.raise_for_status()
    return r.json()


async def fetch_readme_text(client: httpx.AsyncClient, owner: str, repo: str) -> str | None:
    r = await client.get(
        f"{API}/repos/{owner}/{repo}/readme",
        headers={"Accept": "application/vnd.github.raw"},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.text
