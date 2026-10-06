"""P04: the read calls to Google survive a brief 5xx / timeout (via P24's request_with_retry); no real network or sleeping."""
import time

import httpx
import pytest

from app.modules.p04_ads_connection.adapters.google_ads import GoogleAdsReadClient, GoogleApiError

pytestmark = pytest.mark.module("P04")


def _client(handler) -> GoogleAdsReadClient:
    return GoogleAdsReadClient(httpx.Client(transport=httpx.MockTransport(handler)), client_id="id", client_secret="s",
                               developer_token="dev", api_version="v25")


def test_search_recovers_from_a_503(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, json={"results": [{"campaign": {"id": "1"}}]})

    assert _client(handler).search("tok", "123", "SELECT campaign.id FROM campaign") == [{"campaign": {"id": "1"}}] and len(calls) == 2


def test_persistent_5xx_still_gives_the_same_error_as_before(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    c = _client(lambda req: httpx.Response(500, json={"error": {"message": "boom", "status": "INTERNAL"}}))
    with pytest.raises(GoogleApiError, match="boom"):
        c.search("tok", "123", "SELECT campaign.id FROM campaign")


def test_token_refresh_retries_but_auth_errors_do_not(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = []

    def flaky(req):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectTimeout("t")
        return httpx.Response(200, json={"access_token": "A"})

    assert _client(flaky).access_token("refresh") == "A" and len(calls) == 2
    bad = []

    def revoked(req):
        bad.append(1)
        return httpx.Response(400, json={"error": "invalid_grant", "error_description": "revoked"})

    with pytest.raises(GoogleApiError):
        _client(revoked).access_token("refresh")
    assert len(bad) == 1                                    # a revoked grant is not retried


def test_authorization_code_exchange_is_never_retried(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(GoogleApiError):
        _client(handler).exchange_code("code", redirect_uri="http://x/cb")
    assert len(calls) == 1                                  # single-use code: one attempt only
