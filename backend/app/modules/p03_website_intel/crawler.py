"""P03 — polite, robots-aware crawler for the business's own websites.

- Honours robots.txt (our user agent, then *), including Crawl-delay (capped).
- URL discovery: sitemaps from robots.txt / /sitemap.xml (incl. sitemap indexes), else same-site link crawl.
- Same-site only (www/non-www treated as one site), HTML only, page cap, per-request timeout, delay between requests.
"""
import time
import xml.etree.ElementTree as ET
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.modules.p03_website_intel.extract import PageSignals, extract, normalise_url, same_site

USER_AGENT = "PPCCommandCenterBot/0.1 (site owner's audit tool)"
SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".mp4", ".mp3", ".doc", ".docx",
            ".xls", ".xlsx", ".css", ".js", ".xml", ".ico")
MAX_SITEMAPS = 10


@dataclass
class Fetched:
    url: str
    status: int | None
    final_url: str | None
    response_ms: float | None
    signals: PageSignals | None
    text: str = ""
    error: str | None = None


@dataclass
class CrawlResult:
    source: str
    discovered: int
    pages: list[Fetched] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _robots(http: httpx.Client, base: str) -> RobotFileParser:
    rp = RobotFileParser()
    try:
        r = http.get(urljoin(base, "/robots.txt"))
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except httpx.HTTPError:
        rp.parse([])
    return rp


def _sitemap_urls(http: httpx.Client, base: str, rp: RobotFileParser, errors: list[str]) -> list[str]:
    queue = list(rp.site_maps() or []) or [urljoin(base, "/sitemap.xml"), urljoin(base, "/sitemap_index.xml")]
    seen, pages = set(), []
    while queue and len(seen) < MAX_SITEMAPS:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            r = http.get(sm)
            if r.status_code != 200 or b"<" not in r.content[:200]:
                continue
            root = ET.fromstring(r.content)
        except (httpx.HTTPError, ET.ParseError) as e:
            errors.append(f"sitemap {sm}: {e.__class__.__name__}")
            continue
        tag = root.tag.split("}")[-1]
        locs = [el.text.strip() for el in root.iter() if el.tag.split("}")[-1] == "loc" and el.text]
        if tag == "sitemapindex":
            queue.extend(locs)
        else:
            pages.extend(locs)
    return pages


def _allowed(url: str, host: str, rp: RobotFileParser) -> bool:
    p = urlparse(url)
    return (p.scheme in ("http", "https") and same_site(p.netloc, host)
            and not p.path.lower().endswith(SKIP_EXT) and rp.can_fetch(USER_AGENT, url))


def fetch(http: httpx.Client, url: str) -> Fetched:
    t0 = time.perf_counter()
    try:
        r = http.get(url)
    except httpx.HTTPError as e:
        return Fetched(url, None, None, None, None, error=f"{e.__class__.__name__}: {str(e)[:120]}")
    ms = round((time.perf_counter() - t0) * 1000, 1)
    ctype = r.headers.get("content-type", "")
    if "html" not in ctype:
        return Fetched(url, r.status_code, str(r.url), ms, None, error=f"not HTML ({ctype[:40]})")
    signals, text = extract(r.text, str(r.url))
    return Fetched(url, r.status_code, str(r.url), ms, signals, text)


def crawl(base_url: str, *, max_pages: int = 50, delay: float = 0.5,
          http_factory: Callable[[], httpx.Client] | None = None,
          sleep: Callable[[float], None] = time.sleep) -> CrawlResult:
    make = http_factory or (lambda: httpx.Client(timeout=15, follow_redirects=True,
                                                 headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"}))
    host = urlparse(base_url).netloc
    errors: list[str] = []
    with make() as http:
        rp = _robots(http, base_url)
        cd = rp.crawl_delay(USER_AGENT)
        delay = max(delay, min(float(cd), 5.0)) if cd else delay
        home = normalise_url(base_url)
        from_sitemap = [normalise_url(u) for u in _sitemap_urls(http, base_url, rp, errors)]
        candidates = list(dict.fromkeys([home] + [u for u in from_sitemap if _allowed(u, host, rp)]))
        source = "sitemap" if len(candidates) > 1 else "links"
        result = CrawlResult(source=source, discovered=len(candidates))
        queue, seen = deque(candidates), set(candidates)
        while queue and len(result.pages) < max_pages:
            url = queue.popleft()
            if not rp.can_fetch(USER_AGENT, url):
                continue
            if result.pages:
                sleep(delay)
            f = fetch(http, url)
            result.pages.append(f)
            if f.error:
                errors.append(f"{url}: {f.error}")
            if source == "links" and f.signals:
                for link in f.signals.internal_links:
                    if link not in seen and _allowed(link, host, rp):
                        seen.add(link)
                        queue.append(link)
        result.discovered = max(result.discovered, len(seen))
        result.errors = errors[:50]
    return result
