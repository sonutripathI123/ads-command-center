"""P11 — polite research of a competitor's PUBLIC website: robots.txt honoured, sitemap-led page choice (service/location
pages first), small page cap, delay between requests. Google result pages are never scraped (against Google's terms);
SERP observations are entered by the user."""
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "PPCCommandCenterBot/0.1 (public competitor research; respects robots.txt)"
MAX_SITEMAPS = 5
SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".mp4", ".css", ".js", ".xml", ".ico")
SKIP_PATH = re.compile(r"/(tag|category|author|wp-|feed|cart|checkout|account|login|privacy|terms|page/\d)", re.I)
PRICE_RE = re.compile(r"(?:from\s+)?\$\s?\d{2,4}(?:\.\d{2})?(?:\s*(?:per|/)\s*(?:hour|hr|trip|way))?", re.I)
CTA_RE = re.compile(r"\b(book|reserve|quote|enquire|call|contact|check availability|get started)\b", re.I)
TRUST_RE = {"reviews": r"\b(reviews?|testimonials?|rated|stars?)\b", "experience": r"\b\d{1,2}\+? years?\b|\bsince (19|20)\d\d\b",
            "accreditation": r"\b(accredited|licen[cs]ed|insured|certified)\b", "fixed_price": r"\bfixed (price|rate|fare)s?\b",
            "guarantee": r"\b(guarantee[d]?|on[- ]time|no hidden (fees|costs))\b", "awards": r"\b(award|winner)\b"}
SKIP_TEXT = {"script", "style", "noscript", "svg", "template"}


@dataclass
class CompetitorPage:
    url: str
    status_code: int | None
    title: str = ""
    meta_description: str = ""
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    ctas: list[str] = field(default_factory=list)
    prices: list[str] = field(default_factory=list)
    trust: list[str] = field(default_factory=list)
    word_count: int = 0
    text: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["text"] = d["text"][:4000]
        return d


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.h1, self.h2, self.ctas, self.text = "", "", [], [], [], []
        self._stack: list[str] = []
        self._cap: str | None = None
        self._buf: list[str] = []
        self._link: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self._stack.append(tag)
        if tag == "meta" and a.get("name", "").lower() == "description":
            self.meta = a.get("content", "").strip()
        elif tag in ("title", "h1", "h2"):
            self._cap, self._buf = tag, []
        elif tag in ("a", "button"):
            self._link = []

    def handle_endtag(self, tag):
        if tag == self._cap:
            t = " ".join("".join(self._buf).split())
            if tag == "title":
                self.title = t
            elif t:
                (self.h1 if tag == "h1" else self.h2).append(t[:200])
            self._cap = None
        if tag in ("a", "button") and self._link is not None:
            t = " ".join("".join(self._link).split())
            if t and len(t) <= 40 and "@" not in t and "/" not in t and ".com" not in t and CTA_RE.search(t):
                self.ctas.append(t)
            self._link = None
        while self._stack and self._stack.pop() != tag:
            pass

    def handle_data(self, data):
        if self._cap:
            self._buf.append(data)
        if self._link is not None:
            self._link.append(data)
        if not any(t in SKIP_TEXT for t in self._stack) and data.strip():
            self.text.append(data.strip())


def _unique_ci(items: list[str]) -> list[str]:
    seen, out = set(), []
    for i in items:
        if i.lower() not in seen:
            seen.add(i.lower())
            out.append(i)
    return out


def parse(url: str, status: int | None, html: str) -> CompetitorPage:
    p = _Parser()
    p.feed(html)
    text = " ".join(p.text)
    low = text.lower()
    return CompetitorPage(url=url, status_code=status, title=p.title, meta_description=p.meta, h1=p.h1[:5], h2=p.h2[:20],
                          ctas=_unique_ci(p.ctas)[:10],prices=list(dict.fromkeys(m.group(0).strip() for m in PRICE_RE.finditer(text)))[:10],
                          trust=[k for k, v in TRUST_RE.items() if re.search(v, low)], word_count=len(text.split()), text=text)


def _robots(http: httpx.Client, base: str) -> RobotFileParser:
    rp = RobotFileParser()
    try:
        r = http.get(urljoin(base, "/robots.txt"))
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except httpx.HTTPError:
        rp.parse([])
    return rp


def _sitemap(http: httpx.Client, base: str, rp: RobotFileParser) -> list[str]:
    queue = list(rp.site_maps() or []) or [urljoin(base, "/sitemap.xml"), urljoin(base, "/sitemap_index.xml")]
    seen, out = set(), []
    while queue and len(seen) < MAX_SITEMAPS:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            r = http.get(sm)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
        except (httpx.HTTPError, ET.ParseError):
            continue
        locs = [e.text.strip() for e in root.iter() if e.tag.split("}")[-1] == "loc" and e.text]
        (queue if root.tag.split("}")[-1] == "sitemapindex" else out).extend(locs)
    return out


def choose_pages(candidates: list[str], base: str, keywords: list[str], limit: int) -> list[str]:
    """Homepage first, then URLs whose path mentions a service/location keyword, then the shortest other paths."""
    host = urlparse(base).netloc.lower().removeprefix("www.")
    seen, scored = set(), []
    for u in candidates:
        p = urlparse(u)
        key = p.path.rstrip("/") or "/"
        if (p.netloc.lower().removeprefix("www.") != host or key in seen or p.path.lower().endswith(SKIP_EXT)
                or SKIP_PATH.search(p.path)):
            continue
        seen.add(key)
        path = p.path.lower().replace("-", " ").replace("_", " ")
        hits = sum(1 for k in keywords if k in path)
        scored.append((0 if key == "/" else 1, 0 if hits else 1, len(key), u))  # any keyword hit counts once; short paths
        # (service pages) before long blog slugs
    return [u for *_, u in sorted(scored)[:limit]]


def research(base_url: str, keywords: list[str], *, max_pages: int = 12, delay: float = 1.5,
             http_factory: Callable[[], httpx.Client] | None = None) -> tuple[list[CompetitorPage], list[str]]:
    notes: list[str] = []
    make = http_factory or (lambda: httpx.Client(timeout=20, follow_redirects=True,
                                                 headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"}))
    with make() as http:
        rp = _robots(http, base_url)
        if not rp.can_fetch(USER_AGENT, base_url):
            return [], ["robots.txt does not allow automated visits — nothing was fetched."]
        urls = _sitemap(http, base_url, rp)
        home_html = ""
        if not urls:
            notes.append("No sitemap found — pages were picked from the homepage links.")
            try:
                r = http.get(base_url)
                home_html = r.text if "html" in r.headers.get("content-type", "") else ""
            except httpx.HTTPError:
                pass
            urls = [urljoin(base_url, h) for h in re.findall(r'href=["\']([^"\'#]+)', home_html)]
        picked = [u for u in choose_pages([base_url, *urls], base_url, keywords, max_pages) if rp.can_fetch(USER_AGENT, u)]
        pages = []
        for i, u in enumerate(picked):
            if i:
                time.sleep(delay)
            try:
                r = http.get(u)
                html = r.text if "html" in r.headers.get("content-type", "") else ""
                pages.append(parse(str(r.url), r.status_code, html) if html else CompetitorPage(u, r.status_code, error="not HTML"))
            except httpx.HTTPError as e:
                pages.append(CompetitorPage(u, None, error=type(e).__name__))
    return pages, notes
