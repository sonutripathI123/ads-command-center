"""P06: GA4 and Search Console reads survive a brief 5xx / timeout (via P24's request_with_retry); no network or sleeping."""
import time

import httpx
import pytest

from app.modules.p06_analytics.adapters.google import GA4Client, GoogleDataError, SearchConsoleClient

pytestmark = pytest.mark.module("P06")


class FakeSA:
    def __init__(self, handler):
        self.http = httpx.Client(transport=httpx.MockTransport(handler))

    def headers(self):
        return {"Authorization": "Bearer t"}


def test_ga4_report_recovers_from_503(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = []

    def handler(req):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"rowCount": 1, "rows": [{"dimensionValues": [{"value": "Paid Search"}], "metricValues": [{"value": "7"}]}]})

    rows = GA4Client(FakeSA(handler)).report("123", start="2026-10-01", end="2026-10-02", dimensions=["sessionDefaultChannelGroup"], metrics=["sessions"])
    assert rows == [{"sessionDefaultChannelGroup": "Paid Search", "sessions": "7"}] and len(calls) == 2


def test_search_console_recovers_from_a_timeout(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = []

    def handler(req):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow")
        return httpx.Response(200, json={"rows": [{"keys": ["2026-10-01", "limo hire"], "clicks": 3, "impressions": 40, "position": 4.2}]})

    rows = SearchConsoleClient(FakeSA(handler)).query("https://x.com.au/", start="2026-10-01", end="2026-10-02", dimensions=["date", "query"])
    assert rows[0]["clicks"] == 3 and len(calls) == 2


def test_persistent_failure_still_raises_the_normal_error(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    sa = FakeSA(lambda req: httpx.Response(500, json={"error": {"message": "backend error"}}))
    with pytest.raises(GoogleDataError):
        GA4Client(sa).report("123", start="2026-10-01", end="2026-10-02", dimensions=["date"], metrics=["sessions"])
