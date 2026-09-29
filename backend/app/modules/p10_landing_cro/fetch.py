"""P10 — polite single-page fetch of the business's own ad landing pages (robots-aware, timed, HTML only)."""
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "PPCCommandCenterBot/0.1 (site owner's landing-page check)"
MOBILE_HINT = "Mozilla/5.0 (Linux; Android 14) Mobile"  # appended so mobile variants are served where sites vary
MAX_BYTES = 5_000_000


@dataclass
class Page:
    url: str
    status_code: int | None
    final_url: str | None
    elapsed_ms: float | None
    html: str
    error: str | None = None


def _robots(http: httpx.Client, url: str) -> RobotFileParser:
    rp = RobotFileParser()
    try:
        r = http.get(urljoin(url, "/robots.txt"))
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except httpx.HTTPError:
        rp.parse([])
    return rp


def default_client() -> httpx.Client:
    return httpx.Client(timeout=20, follow_redirects=True,
                        headers={"User-Agent": f"{USER_AGENT} {MOBILE_HINT}", "Accept": "text/html,*/*"})


def fetch_pages(urls: list[str], *, http_factory: Callable[[], httpx.Client] | None = None, delay: float = 1.0) -> list[Page]:
    out: list[Page] = []
    robots: dict[str, RobotFileParser] = {}
    with (http_factory or default_client)() as http:
        for i, url in enumerate(urls):
            host = urlparse(url).netloc.lower()
            if host not in robots:
                robots[host] = _robots(http, url)
            if not robots[host].can_fetch(USER_AGENT, url):
                out.append(Page(url, None, None, None, "", "Blocked by robots.txt"))
                continue
            if i:
                time.sleep(delay)
            t0 = time.perf_counter()
            try:
                r = http.get(url)
                ms = round((time.perf_counter() - t0) * 1000, 1)
                ctype = r.headers.get("content-type", "")
                html = r.text[:MAX_BYTES] if "html" in ctype or not ctype else ""
                out.append(Page(url, r.status_code, str(r.url), ms, html, None if html else f"Not an HTML page ({ctype})"))
            except httpx.HTTPError as e:
                out.append(Page(url, None, None, None, "", f"Could not load: {type(e).__name__}"))
    return out
