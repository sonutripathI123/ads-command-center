from datetime import date

import pytest
from sqlalchemy import func, select

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p05_ads_sync.models import MetricsSnapshot, SyncRun
from app.shared.db import session_scope

pytestmark = pytest.mark.module("P05")
B = "/api/v1/ads-sync/accounts/7"
W = "date_from=2026-09-26&date_to=2026-09-27"


def _sync(client, **body):
    r = client.post(f"{B}/sync", json=body)
    assert r.status_code == 202, r.text
    return client.get(f"{B}/runs").json()[0]


def test_accounts_lists_p04_accounts(client):
    accs = client.get("/api/v1/ads-sync/accounts").json()
    assert accs[0]["customer_id"] == "1949408641" and accs[0]["last_run"] is None


def test_first_sync_is_90_days_and_succeeds(client):
    run = _sync(client)
    assert run["status"] == "success", run
    assert run["date_from"] == "2026-06-30" and run["date_to"] == "2026-09-27"
    assert set(run["counts"]) == {"campaigns", "ad_groups", "keywords", "search_terms", "ads"}


def test_incremental_sync_uses_lookback(client):
    _sync(client)
    run = _sync(client)
    assert run["date_from"] == "2026-09-24" and run["date_to"] == "2026-09-27"


def test_all_queries_are_select_only(client, fake_ads):
    _sync(client)
    assert fake_ads.queries and all(q.upper().startswith("SELECT") for q in fake_ads.queries)


def test_summary_totals_and_daily(client):
    _sync(client)
    s = client.get(f"{B}/summary?{W}").json()
    t = s["totals"]
    assert t["clicks"] == 20 and t["cost"] == 51.0 and t["conversions"] == 2.0
    assert t["avg_cpc"] == 2.55 and t["cost_per_conversion"] == 25.5 and t["ctr"] == 0.1
    assert [d["date"] for d in s["daily"]] == ["2026-09-26", "2026-09-27"]


def test_campaigns_sorted_by_cost_with_zero_rows(client):
    _sync(client)
    rows = client.get(f"{B}/campaigns?{W}").json()
    assert [r["google_id"] for r in rows] == ["100", "200"]
    assert rows[0]["budget"] == 50.0 and rows[0]["cost"] == 51.0
    assert rows[1]["cost"] == 0 and rows[1]["ctr"] is None


def test_ad_groups_and_keywords(client):
    _sync(client)
    ag = client.get(f"{B}/ad-groups?campaign_id=100&{W}").json()
    assert ag[0]["name"] == "Melbourne Airport" and ag[0]["campaign_name"] == "Airport Transfers - Search"
    kws = client.get(f"{B}/keywords?{W}").json()
    assert [k["text"] for k in kws] == ["melbourne airport transfer", "chauffeur melbourne"]
    assert kws[0]["quality_score"] == 7 and kws[0]["cost"] == 30.0 and kws[1]["quality_score"] is None


def test_search_terms_summed_across_matched_keywords(client):
    _sync(client)
    terms = {t["search_term"]: t for t in client.get(f"{B}/search-terms?{W}").json()}
    assert terms["melbourne airport chauffeur"]["clicks"] == 12  # (5+1) x 2 days
    assert terms["melbourne airport chauffeur"]["cost"] == 30.0
    assert terms["uber jobs melbourne"]["conversions"] == 0
    assert terms["melbourne airport chauffeur"]["first_seen"] == "2026-09-26"
    assert [t["search_term"] for t in client.get(f"{B}/search-terms?q=UBER&{W}").json()] == ["uber jobs melbourne"]


def test_ads_have_rsa_text(client):
    _sync(client)
    ad = client.get(f"{B}/ads?{W}").json()[0]
    assert ad["headlines"] == ["Melbourne Airport Chauffeur"] and ad["final_urls"][0].endswith("/airport")


def test_resync_does_not_duplicate_metrics(client):
    _sync(client)
    with session_scope() as db:
        n1 = db.scalar(select(func.count()).select_from(MetricsSnapshot))
    _sync(client)
    with session_scope() as db:
        assert db.scalar(select(func.count()).select_from(MetricsSnapshot)) == n1
    assert client.get(f"{B}/summary?{W}").json()["totals"]["clicks"] == 20


def test_failing_step_gives_partial_run(client, fake_ads):
    fake_ads.fail_on = "search_term_view"
    run = _sync(client)
    assert run["status"] == "partial" and "search_terms" in run["errors"] and "campaigns" in run["counts"]


def test_connection_failure_gives_failed_run(client, monkeypatch):
    from app.modules.p05_ads_sync import sync

    def boom(db, account_id, http):
        raise RuntimeError("deleted_client")

    monkeypatch.setattr(sync, "open_read_session", boom)
    run = _sync(client)
    assert run["status"] == "failed" and "deleted_client" in run["errors"]["connect"]


def test_second_sync_while_running_returns_existing(client):
    with session_scope() as db:
        db.add(SyncRun(account_id=7, status="running", date_from=date(2026, 9, 1), date_to=date(2026, 9, 27)))
    r = client.post(f"{B}/sync", json={})
    assert r.json()["status"] == "running"
    with session_scope() as db:
        assert db.scalar(select(func.count()).select_from(SyncRun)) == 1


def test_viewer_cannot_sync_but_can_read(client):
    viewer = CurrentUser(id=2, email="v@example.com", name="v", role="viewer", permissions=frozenset({Permission.READ}))
    client.app_ref.dependency_overrides[get_current_user] = lambda: viewer
    assert client.post(f"{B}/sync", json={}).status_code == 403
    assert client.get(f"{B}/campaigns").status_code == 200


def test_unknown_account_404(client):
    assert client.post("/api/v1/ads-sync/accounts/999/sync", json={}).status_code == 404


def test_bad_date_window(client):
    assert client.get(f"{B}/summary?date_from=2026-09-27&date_to=2026-09-01").status_code == 422


def test_interface_exposes_performance(client):
    from app.modules.p05_ads_sync.interface import search_terms

    _sync(client)
    with session_scope() as db:
        rows = search_terms(db, 7, date(2026, 9, 26), date(2026, 9, 27))
    assert {r["search_term"] for r in rows} == {"melbourne airport chauffeur", "uber jobs melbourne"}


# ---- removed / paused campaigns are shown truthfully ------------------------------------------------------

def _fake_status(fake_ads, *, drop=(), status=None):
    orig = fake_ads.search

    def search(q):
        rows = orig(q)
        if "FROM campaign" in q and "segments.date" not in q:
            rows = [r for r in rows if r["campaign"]["id"] not in drop]
            for r in rows:
                if status and r["campaign"]["id"] in status:
                    r["campaign"]["status"] = status[r["campaign"]["id"]]
        return rows

    fake_ads.search = search


def test_campaign_deleted_in_google_becomes_removed_and_is_hidden_when_idle(client, fake_ads):
    _sync(client)
    assert {c["name"]: c["status"] for c in client.get(f"{B}/campaigns?{W}").json()}["Brand"] == "PAUSED"
    _fake_status(fake_ads, drop={"200"})                      # Google no longer returns campaign 200 -> it was removed there
    _sync(client)
    everything = {c["name"]: c["status"] for c in client.get(f"{B}/campaigns?{W}&include_removed=true").json()}
    assert everything["Brand"] == "REMOVED" and everything["Airport Transfers - Search"] == "ENABLED"
    assert [c["name"] for c in client.get(f"{B}/campaigns?{W}").json()] == ["Airport Transfers - Search"]   # idle removed hidden


def test_ad_group_shows_its_campaigns_status(client, fake_ads):
    _fake_status(fake_ads, status={"100": "PAUSED"})
    _sync(client)
    g = client.get(f"{B}/ad-groups?{W}").json()[0]
    assert g["status"] == "ENABLED" and g["campaign_status"] == "PAUSED" and g["effective_status"] == "CAMPAIGN_PAUSED"


def test_effective_status_rules_and_idle_removed_filter():
    from app.modules.p05_ads_sync import service

    e = service.effective_status
    assert e("ENABLED", "ENABLED") == "ENABLED" and e("PAUSED", "ENABLED") == "PAUSED"
    assert e("ENABLED", "PAUSED") == "CAMPAIGN_PAUSED" and e("ENABLED", None) == "REMOVED" and e("REMOVED", "ENABLED") == "REMOVED"
    rows = [{"s": "REMOVED", "impressions": 0, "cost": 0.0}, {"s": "REMOVED", "impressions": 5, "cost": 1.0}, {"s": "ENABLED", "impressions": 0, "cost": 0.0}]
    assert service.hide_idle_removed(rows, "s") == rows[1:]
