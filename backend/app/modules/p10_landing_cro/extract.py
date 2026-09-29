"""P10 — CRO signals from one landing page's HTML (stdlib parser, no JS rendering).

Different purpose from P03's SEO extraction: form fields, CTA wording/position, trust signals, prices, tracking tags."""
import re
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser

CTA_RE = re.compile(r"\b(book|reserve|get (a |an |your |my )?(free |instant )?(quote|price|estimate)|request|enquire|inquire|call|contact|check availability|"
                    r"get started|instant quote)\b", re.I)
TRUST_PATTERNS = {
    "reviews": r"\b(reviews?|testimonials?|rated|rating|stars?|★)\b",
    "google_reviews": r"google (reviews?|rating)",
    "experience": r"\b\d{1,2}\+? years?\b|\bsince (19|20)\d\d\b|\bestablished\b",
    "accreditation": r"\b(accredited|licensed|licenced|insured|certified|vic ?roads|cpvv|safe transport victoria|abn)\b",
    "guarantee": r"\b(guarantee[d]?|on[- ]time|no hidden (fees|costs)|fixed (price|rate|fare)s?|free cancell?ation)\b",
    "awards": r"\b(award|winner|finalist)\b",
    "clients": r"\b(trusted by|our clients|corporate clients|as seen)\b",
}
PRICE_RE = re.compile(r"(\$|aud\s?)\s?\d{2,4}", re.I)
GA4_RE = re.compile(r"(gtag/js\?id=G-|googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]{4,})", re.I)
ADS_TAG_RE = re.compile(r"(gtag/js\?id=AW-|['\"]AW-\d{6,})", re.I)
SKIP_TEXT = {"script", "style", "noscript", "svg", "template"}
EARLY_CHARS = 1200  # "above the fold" approximation: the first ~1200 visible characters


@dataclass
class Form:
    fields: list[dict] = field(default_factory=list)  # [{"name", "type", "required"}]
    submit_text: str = ""


@dataclass
class CroSignals:
    title: str = ""
    meta_description: str = ""
    viewport: bool = False
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    text: str = ""                                     # visible text (truncated), for intent matching
    word_count: int = 0
    ctas: list[str] = field(default_factory=list)
    early_cta: bool = False
    tel_links: int = 0
    booking_links: int = 0
    forms: list[Form] = field(default_factory=list)
    trust: dict[str, bool] = field(default_factory=dict)
    prices: bool = False
    schema_types: list[str] = field(default_factory=list)
    has_ga4_or_gtm: bool = False
    has_ads_tag: bool = False
    scripts: int = 0
    images: int = 0
    images_without_alt: int = 0
    html_bytes: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["text"] = d["text"][:6000]
        return d


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.s = CroSignals()
        self._stack: list[str] = []
        self._capture: str | None = None
        self._buf: list[str] = []
        self._text: list[str] = []
        self._text_len = 0
        self._form: Form | None = None
        self._button: list[str] | None = None
        self._link: tuple[str, list[str]] | None = None
        self._ld = False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self._stack.append(tag)
        if tag == "meta":
            name = a.get("name", "").lower()
            if name == "viewport" and "width" in a.get("content", ""):
                self.s.viewport = True
            elif name == "description":
                self.s.meta_description = a.get("content", "").strip()
        elif tag in ("title", "h1", "h2"):
            self._capture, self._buf = tag, []
        elif tag == "script":
            self.s.scripts += 1
            if "ld+json" in a.get("type", ""):
                self._ld = True
        elif tag == "img":
            self.s.images += 1
            if not a.get("alt", "").strip():
                self.s.images_without_alt += 1
        elif tag == "form":
            self._form = Form()
        elif tag in ("input", "select", "textarea") and self._form is not None:
            t = a.get("type", tag).lower() if tag == "input" else tag
            if t in ("hidden", "submit", "button", "image", "reset"):
                if t in ("submit", "button") and a.get("value"):
                    self._form.submit_text = a["value"].strip()
                return
            self._form.fields.append({"name": a.get("name") or a.get("id") or a.get("placeholder") or t, "type": t,
                                      "required": "required" in a or a.get("aria-required") == "true"})
        elif tag == "button":
            self._button = []
        elif tag == "a":
            href = a.get("href", "")
            if href.lower().startswith("tel:"):
                self.s.tel_links += 1
            if re.search(r"book|reserv|quote|enquir", href, re.I):
                self.s.booking_links += 1
            self._link = (href, [])
        for k in ("itemtype",):
            if a.get(k):
                self.s.schema_types.append(a[k].rstrip("/").rsplit("/", 1)[-1])

    def handle_endtag(self, tag):
        if tag == self._capture:
            text = " ".join("".join(self._buf).split())
            if tag == "title":
                self.s.title = text
            elif text:
                getattr(self.s, tag).append(text)
            self._capture = None
        if tag == "form" and self._form is not None:
            self.s.forms.append(self._form)
            self._form = None
        if tag == "button" and self._button is not None:
            text = " ".join("".join(self._button).split())
            if self._form is not None and text:
                self._form.submit_text = text
            self._cta(text)
            self._button = None
        if tag == "a" and self._link is not None:
            self._cta(" ".join("".join(self._link[1]).split()))
            self._link = None
        if tag == "script":
            self._ld = False
        while self._stack and self._stack.pop() != tag:
            pass

    def _cta(self, text: str):
        if text and len(text) <= 60 and "@" not in text and not text.endswith("?") and CTA_RE.search(text):
            self.s.ctas.append(text)
            if self._text_len <= EARLY_CHARS:
                self.s.early_cta = True

    def handle_data(self, data):
        if self._ld:
            self.s.schema_types += re.findall(r'"@type"\s*:\s*"([A-Za-z]+)"', data)
            return
        if self._capture:
            self._buf.append(data)
        if self._button is not None:
            self._button.append(data)
        if self._link is not None:
            self._link[1].append(data)
        if any(t in SKIP_TEXT for t in self._stack) or (self._stack and self._stack[-1] == "title"):
            return
        t = data.strip()
        if t:
            self._text.append(t)
            self._text_len += len(t) + 1


def extract(html: str) -> CroSignals:
    p = _Parser()
    p.feed(html)
    s = p.s
    s.text = " ".join(p._text)
    s.word_count = len(s.text.split())
    low = s.text.lower()
    s.trust = {k: bool(re.search(v, low, re.I)) for k, v in TRUST_PATTERNS.items()}
    if any(t in ("AggregateRating", "Review") for t in s.schema_types):
        s.trust["reviews"] = True
    s.prices = bool(PRICE_RE.search(s.text))
    s.has_ga4_or_gtm = bool(GA4_RE.search(html))
    s.has_ads_tag = bool(ADS_TAG_RE.search(html))
    s.html_bytes = len(html.encode("utf-8", "ignore"))
    s.schema_types = sorted(set(s.schema_types))
    s.ctas = list(dict.fromkeys(s.ctas))[:30]
    return s
