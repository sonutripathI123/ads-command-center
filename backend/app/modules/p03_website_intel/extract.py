"""P03 — extract landing-page signals from HTML (stdlib html.parser only; no JavaScript execution).

Pages built entirely client-side will look thin here; that is itself a useful signal for ads landing pages.
"""
import json
import re
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

CTA_WORDS = re.compile(r"\b(book|booking|reserve|quote|enquir|inquir|get a price|call|contact|request|order now)\w*", re.I)
PHONE = re.compile(r"(?:\+?61|0)[\s\-()]*[2-478](?:[\s\-()]*\d){8}|1[38]00(?:[\s\-]*\d){6}")
SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}


@dataclass
class PageSignals:
    url: str
    title: str = ""
    meta_description: str = ""
    canonical: str | None = None
    robots_meta: str = ""
    viewport: bool = False
    lang: str = ""
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    word_count: int = 0
    ctas: list[str] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)       # [{"action":..., "fields":[names]}]
    phones: list[str] = field(default_factory=list)
    tel_links: int = 0
    emails: int = 0
    schema_types: list[str] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: int = 0
    images: int = 0
    images_without_alt: int = 0

    def to_json(self) -> str:
        d = asdict(self)
        d["internal_links"] = d["internal_links"][:200]
        return json.dumps(d)


def normalise_url(url: str) -> str:
    """Canonical key for a page: https, lower-case host without "www.", no query/fragment, no trailing slash
    (except root). www and non-www are the same site for our purposes; requests follow redirects anyway."""
    p = urlparse(url)
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunparse(("https" if p.scheme.lower() in ("http", "https") else p.scheme.lower(),
                       p.netloc.lower().removeprefix("www."), path, "", "", ""))


def same_site(host_a: str, host_b: str) -> bool:
    strip = lambda h: h.lower().removeprefix("www.")  # noqa: E731
    return strip(host_a) == strip(host_b)


class _Parser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.host = urlparse(base_url).netloc
        self.s = PageSignals(url=base_url)
        self._stack: list[str] = []
        self._skip = 0
        self._capture: str | None = None  # title | h1 | h2 | a | button | jsonld
        self._buf: list[str] = []
        self._text: list[str] = []
        self._form: dict | None = None
        self._internal: set[str] = set()

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag in SKIP_TAGS:
            if tag == "script" and a.get("type", "").lower() == "application/ld+json":
                self._capture, self._buf = "jsonld", []
            self._skip += 1
            return
        if tag == "html":
            self.s.lang = a.get("lang", "")
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name == "description":
                self.s.meta_description = a.get("content", "").strip()
            elif name == "robots":
                self.s.robots_meta = a.get("content", "").lower()
            elif name == "viewport":
                self.s.viewport = True
        elif tag == "link" and "canonical" in a.get("rel", "").lower():
            self.s.canonical = urljoin(self.base, a.get("href", ""))
        elif tag in ("title", "h1", "h2"):
            self._capture, self._buf = tag, []
        elif tag == "button":
            if self._capture is None:
                self._capture, self._buf = "button", []
        elif tag == "a":
            href = a.get("href", "").strip()
            if self._capture is None:  # a link inside a heading keeps the heading capture
                self._capture, self._buf = "a", []
            if href.startswith("tel:"):
                self.s.tel_links += 1
            elif href.startswith("mailto:"):
                self.s.emails += 1
            elif href and not href.startswith(("#", "javascript:")):
                u = urljoin(self.base, href)
                pu = urlparse(u)
                if pu.scheme in ("http", "https"):
                    if same_site(pu.netloc, self.host):
                        self._internal.add(normalise_url(u))
                    else:
                        self.s.external_links += 1
        elif tag == "form":
            self._form = {"action": urljoin(self.base, a.get("action", "")), "fields": []}
        elif tag in ("input", "select", "textarea") and self._form is not None:
            if a.get("type", "").lower() not in ("hidden", "submit", "button"):
                self._form["fields"].append(a.get("name") or a.get("id") or a.get("type") or tag)
            if a.get("type", "").lower() == "submit" and a.get("value"):
                self._maybe_cta(a["value"])
        elif tag == "img":
            self.s.images += 1
            if not a.get("alt", "").strip():
                self.s.images_without_alt += 1

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            if tag == "script" and self._capture == "jsonld":
                self._jsonld("".join(self._buf))
                self._capture = None
            return
        if tag == "form" and self._form is not None:
            self.s.forms.append(self._form)
            self._form = None
        if self._capture == tag:
            text = " ".join("".join(self._buf).split())
            if tag == "title":
                self.s.title = text
            elif tag == "h1" and text:
                self.s.h1.append(text)
            elif tag == "h2" and text:
                self.s.h2.append(text)
            elif tag in ("a", "button"):
                self._maybe_cta(text)
            self._capture = None

    def handle_data(self, data):
        if self._capture:
            self._buf.append(data)
        if not self._skip:
            self._text.append(data)

    def _maybe_cta(self, text: str):
        text = " ".join(text.split())
        if text and len(text) <= 60 and CTA_WORDS.search(text) and text not in self.s.ctas:
            self.s.ctas.append(text)

    def _jsonld(self, raw: str):
        try:
            data = json.loads(raw)
        except ValueError:
            return
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if isinstance(it, dict):
                t = it.get("@type")
                for x in t if isinstance(t, list) else [t]:
                    if x and x not in self.s.schema_types:
                        self.s.schema_types.append(str(x))

    def result(self) -> PageSignals:
        text = " ".join(" ".join(self._text).split())
        self.s.word_count = len(text.split())
        self.s.phones = sorted({re.sub(r"\D", "", m) for m in PHONE.findall(text)})[:5]
        self.s.internal_links = sorted(self._internal)
        self.text = text
        return self.s


def extract(html: str, url: str) -> tuple[PageSignals, str]:
    """→ (signals, visible text lower-cased)."""
    p = _Parser(url)
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: BLE001 — malformed HTML: keep what was parsed
        pass
    s = p.result()
    return s, p.text.lower()


ISSUE_LABELS = {
    "http_error": "Page returns an error status",
    "noindex": "Page is set to noindex",
    "missing_title": "Missing <title>",
    "missing_meta_description": "Missing meta description",
    "missing_h1": "No H1 heading",
    "multiple_h1": "More than one H1",
    "thin_content": "Very little text (< 200 words)",
    "no_cta": "No booking / quote / call button found",
    "no_form_or_phone": "No enquiry form and no phone number",
    "no_viewport": "Not set up for mobile (no viewport tag)",
    "slow": "Slow response (> 3 s)",
    "no_service_mention": "No service you offer is mentioned",
}


def page_issues(s: PageSignals, status: int | None, response_ms: float | None, services: list[str]) -> list[str]:
    if status is None or status >= 400:
        return ["http_error"]
    out = []
    if "noindex" in s.robots_meta:
        out.append("noindex")
    if not s.title:
        out.append("missing_title")
    if not s.meta_description:
        out.append("missing_meta_description")
    if not s.h1:
        out.append("missing_h1")
    elif len(s.h1) > 1:
        out.append("multiple_h1")
    if s.word_count < 200:
        out.append("thin_content")
    if not s.ctas:
        out.append("no_cta")
    if not s.forms and not s.phones and not s.tel_links:
        out.append("no_form_or_phone")
    if not s.viewport:
        out.append("no_viewport")
    if response_ms is not None and response_ms > 3000:
        out.append("slow")
    if not services:
        out.append("no_service_mention")
    return out
