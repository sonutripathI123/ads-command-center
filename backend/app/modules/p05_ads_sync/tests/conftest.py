"""P05 fixtures. P04 and P02 are replaced through their public interfaces only."""
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p04_ads_connection.interface import AccountRef
from app.modules.p05_ads_sync import models as m
from app.shared.db import Base, get_engine, session_scope

TABLES = [m.Campaign, m.AdGroup, m.Keyword, m.SearchTerm, m.Ad, m.MetricsSnapshot, m.SyncRun]
ACC = AccountRef(id=7, customer_id="1949408641", descriptive_name="Corporate Cars Melbourne", currency_code="AUD",
                 time_zone="Australia/Brisbane", login_customer_id=None)


def _metric(clicks, cost_aud, conv=0.0, impr=None):
    out = {"clicks": str(clicks), "impressions": str(impr if impr is not None else clicks * 10),
           "costMicros": str(int(cost_aud * 1_000_000))}
    if conv:
        out["conversions"] = conv
        out["conversionsValue"] = conv * 150
    return out


class FakeAds:
    """Two days of data: campaign 100 (Search, ad group 10 with 2 keywords) and campaign 200 (no spend)."""

    def __init__(self, days=("2026-09-26", "2026-09-27")):
        self.days, self.queries, self.fail_on = days, [], None

    def search(self, query: str) -> list[dict]:
        self.queries.append(query)
        assert query.lstrip().upper().startswith("SELECT")
        src = re.search(r"FROM (\w+)", query).group(1)
        if self.fail_on and self.fail_on == src:
            raise RuntimeError(f"Google rejected {src}")
        dated = "segments.date BETWEEN" in query
        camp = {"id": "100", "name": "Airport Transfers - Search", "status": "ENABLED",
                "advertisingChannelType": "SEARCH", "biddingStrategyType": "MAXIMIZE_CONVERSIONS"}
        if src == "campaign" and not dated:
            return [{"campaign": camp, "campaignBudget": {"amountMicros": "50000000"}},
                    {"campaign": {"id": "200", "name": "Brand", "status": "PAUSED"}}]
        if src == "campaign":
            return [{"campaign": {"id": "100"}, "segments": {"date": d}, "metrics": _metric(10, 25.5, 1.0)} for d in self.days]
        if src == "ad_group" and not dated:
            return [{"adGroup": {"id": "10", "name": "Melbourne Airport", "status": "ENABLED", "type": "SEARCH_STANDARD"},
                     "campaign": {"id": "100"}}]
        if src == "ad_group":
            return [{"adGroup": {"id": "10"}, "segments": {"date": d}, "metrics": _metric(10, 25.5, 1.0)} for d in self.days]
        if src == "keyword_view" and not dated:
            return [{"adGroupCriterion": {"criterionId": "1", "keyword": {"text": "melbourne airport transfer", "matchType": "PHRASE"},
                                          "status": "ENABLED", "qualityInfo": {"qualityScore": 7}},
                     "adGroup": {"id": "10"}, "campaign": {"id": "100"}},
                    {"adGroupCriterion": {"criterionId": "2", "keyword": {"text": "chauffeur melbourne", "matchType": "BROAD"},
                                          "status": "ENABLED"}, "adGroup": {"id": "10"}, "campaign": {"id": "100"}}]
        if src == "keyword_view":
            return [{"adGroupCriterion": {"criterionId": "1"}, "adGroup": {"id": "10"}, "segments": {"date": d},
                     "metrics": _metric(6, 15.0, 1.0)} for d in self.days] + \
                   [{"adGroupCriterion": {"criterionId": "2"}, "adGroup": {"id": "10"}, "segments": {"date": d},
                     "metrics": _metric(4, 10.5)} for d in self.days]
        if src == "search_term_view":
            rows = []
            for d in self.days:
                rows.append({"searchTermView": {"searchTerm": "melbourne airport chauffeur", "status": "NONE"},
                             "adGroup": {"id": "10"}, "campaign": {"id": "100"},
                             "segments": {"date": d, "keyword": {"info": {"text": "melbourne airport transfer", "matchType": "PHRASE"}}},
                             "metrics": _metric(5, 12.0, 1.0)})
                # same term matched by a second keyword on the same day -> must be summed
                rows.append({"searchTermView": {"searchTerm": "melbourne airport chauffeur", "status": "NONE"},
                             "adGroup": {"id": "10"}, "campaign": {"id": "100"},
                             "segments": {"date": d, "keyword": {"info": {"text": "chauffeur melbourne", "matchType": "BROAD"}}},
                             "metrics": _metric(1, 3.0)})
                rows.append({"searchTermView": {"searchTerm": "uber jobs melbourne", "status": "NONE"},
                             "adGroup": {"id": "10"}, "campaign": {"id": "100"},
                             "segments": {"date": d, "keyword": {"info": {"text": "chauffeur melbourne", "matchType": "BROAD"}}},
                             "metrics": _metric(2, 4.0)})
            return rows
        if src == "ad_group_ad" and not dated:
            return [{"adGroupAd": {"status": "ENABLED", "ad": {"id": "555", "type": "RESPONSIVE_SEARCH_AD",
                     "finalUrls": ["https://corporatecarsmelbourne.com.au/airport"],
                     "responsiveSearchAd": {"headlines": [{"text": "Melbourne Airport Chauffeur"}],
                                            "descriptions": [{"text": "Book a luxury transfer."}]}}},
                     "adGroup": {"id": "10"}, "campaign": {"id": "100"}}]
        if src == "ad_group_ad":
            return [{"adGroupAd": {"ad": {"id": "555"}}, "adGroup": {"id": "10"}, "segments": {"date": d},
                     "metrics": _metric(10, 25.5, 1.0)} for d in self.days]
        raise AssertionError(f"unexpected query {query}")


@pytest.fixture(scope="session", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[t.__table__ for t in TABLES])


@pytest.fixture(autouse=True)
def _clean():
    yield
    with session_scope() as db:
        for t in TABLES:
            db.execute(delete(t))


@pytest.fixture
def fake_ads(monkeypatch):
    from app.modules.p05_ads_sync import router, sync

    fake = FakeAds()
    monkeypatch.setattr(sync, "active_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "active_accounts", lambda db: [ACC])
    monkeypatch.setattr(sync, "open_read_session", lambda db, account_id, http: fake)
    monkeypatch.setattr(sync, "account_today", lambda acc: __import__("datetime").date(2026, 9, 27))
    return fake


@pytest.fixture
def client(fake_ads):
    from app.main import create_app

    app = create_app()
    user = CurrentUser(id=1, email="a@example.com", name="a", role="analyst",
                       permissions=frozenset({Permission.READ, Permission.RECOMMEND}))
    app.dependency_overrides[get_current_user] = lambda: user
    c = TestClient(app, raise_server_exceptions=False)
    c.app_ref = app
    return c
