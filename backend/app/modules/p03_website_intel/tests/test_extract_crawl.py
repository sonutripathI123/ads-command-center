"""Pure extraction + crawler tests (fake site via httpx.MockTransport, no network)."""
import httpx
import pytest

from app.modules.p03_website_intel import crawler
from app.modules.p03_website_intel.extract import extract, normalise_url, page_issues

pytestmark = pytest.mark.module("P03")

HOME = """<!doctype html><html lang="en-AU"><head><title>Airport Transfers Melbourne | CCM</title>
<meta name="description" content="Luxury airport chauffeur."><meta name="viewport" content="width=device-width">
<link rel="canonical" href="https://example.com.au/">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"LocalBusiness"},{"@type":"WebSite"}]}</script>
<script>var x = "book now";</script></head><body>
<h1>Melbourne Airport <a href="/airport">Chauffeur</a></h1><h2>Why us</h2>
<p>Call us on (03) 9123 4567 or 0412 345 678. """ + ("word " * 250) + """</p>
<a href="/contact">Get a Quote</a> <a href="tel:+61391234567">Call now</a> <a href="https://other.com/x">x</a>
<a href="/airport#top">Airport</a> <button>Book Now</button>
<form action="/enquire"><input name="name"><input type="email" name="email"><input type="hidden" name="t">
<input type="submit" value="Request booking"></form><img src="a.png"><img src="b.png" alt="car">
</body></html>"""


def test_extract_signals():
    s, text = extract(HOME, "https://example.com.au/")
    assert s.title == "Airport Transfers Melbourne | CCM" and s.meta_description == "Luxury airport chauffeur."
    assert s.h1 == ["Melbourne Airport Chauffeur"] and s.h2 == ["Why us"] and s.viewport and s.lang == "en-AU"
    assert {"Get a Quote", "Call now", "Book Now", "Request booking"} <= set(s.ctas)
    assert s.forms[0]["fields"] == ["name", "email"] and s.tel_links == 1
    assert {"0391234567", "0412345678"} <= set(s.phones)
    assert s.schema_types == ["LocalBusiness", "WebSite"]
    assert "https://example.com.au/airport" in s.internal_links and s.external_links == 1
    assert s.images == 2 and s.images_without_alt == 1 and s.word_count > 250
    assert "book now" not in text.split("word")[0] or "var x" not in text  # script content excluded


def test_issues_for_good_and_bad_pages():
    s, _ = extract(HOME, "https://example.com.au/")
    assert page_issues(s, 200, 500, ["airport chauffeur"]) == []
    bad, _ = extract("<html><body><h1>a</h1><h1>b</h1>hi</body></html>", "https://example.com.au/x")
    issues = page_issues(bad, 200, 4000, [])
    assert {"missing_title", "missing_meta_description", "multiple_h1", "thin_content", "no_cta",
            "no_form_or_phone", "no_viewport", "slow", "no_service_mention"} <= set(issues)
    assert page_issues(bad, 404, 100, []) == ["http_error"]


def test_normalise_url():
    assert normalise_url("HTTPS://Example.com.au/Airport/?utm=1#x") == "https://example.com.au/Airport"
    assert normalise_url("https://example.com.au") == "https://example.com.au/"
    assert normalise_url("http://WWW.example.com.au/a/") == "https://example.com.au/a"


class Site:
    def __init__(self, robots="User-agent: *\nDisallow: /private\n", sitemap=True):
        self.robots, self.sitemap, self.hits = robots, sitemap, []

    def handler(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path
        self.hits.append(path)
        html = lambda body: httpx.Response(200, headers={"content-type": "text/html"}, text=body)  # noqa: E731
        if path == "/robots.txt":
            return httpx.Response(200, text=self.robots + ("Sitemap: https://example.com.au/sitemap_index.xml\n" if self.sitemap else ""))
        if path == "/sitemap_index.xml" and self.sitemap:
            return httpx.Response(200, text='<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                            '<sitemap><loc>https://example.com.au/page-sitemap.xml</loc></sitemap></sitemapindex>')
        if path == "/page-sitemap.xml" and self.sitemap:
            return httpx.Response(200, text='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                            '<url><loc>https://example.com.au/airport</loc></url>'
                                            '<url><loc>https://www.example.com.au/wedding/</loc></url>'
                                            '<url><loc>https://example.com.au/private/x</loc></url>'
                                            '<url><loc>https://example.com.au/brochure.pdf</loc></url>'
                                            '<url><loc>https://elsewhere.com/y</loc></url></urlset>')
        if path == "/":
            return html(HOME)
        if path in ("/airport", "/wedding", "/contact"):
            return html(f"<title>{path}</title><a href='/deep'>d</a>")
        if path == "/deep":
            return html("<title>deep</title>")
        return httpx.Response(404, headers={"content-type": "text/html"}, text="nope")


def _crawl(site, **kw):
    return crawler.crawl("https://example.com.au", http_factory=lambda: httpx.Client(transport=httpx.MockTransport(site.handler)),
                         sleep=lambda s: None, **kw)


def test_crawl_uses_sitemap_and_respects_robots_and_scope():
    site = Site()
    res = _crawl(site)
    urls = [p.url for p in res.pages]
    assert res.source == "sitemap"
    assert urls == ["https://example.com.au/", "https://example.com.au/airport", "https://example.com.au/wedding"]
    assert "/private/x" not in site.hits and "/brochure.pdf" not in site.hits and "/deep" not in site.hits


def test_crawl_falls_back_to_links_and_caps_pages():
    site = Site(sitemap=False)
    res = _crawl(site, max_pages=3)
    assert res.source == "links" and len(res.pages) == 3
    assert "/private/x" not in site.hits


def test_link_crawl_follows_internal_links_only():
    site = Site(sitemap=False, robots="")
    res = _crawl(site, max_pages=20)
    assert {p.url for p in res.pages} == {"https://example.com.au/", "https://example.com.au/airport",
                                          "https://example.com.au/contact", "https://example.com.au/deep"}
    assert res.pages[0].signals.title.startswith("Airport Transfers") and "other.com" not in " ".join(site.hits)


def test_disallow_all_crawls_nothing():
    res = _crawl(Site(robots="User-agent: *\nDisallow: /\n", sitemap=False))
    assert res.pages == []
