# P05 — Google Ads Data Sync & Warehouse

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Copy Google Ads entities and **daily** metrics into the local database (read-only GAQL through P04), and serve
aggregated performance to the dashboard and to analysis modules (P07, P08, P12, P13, P19).

## Sync
- `POST /accounts/{id}/sync` (or CLI) creates a `sync_runs` row and runs in the background.
- First sync: last **90 days**. Later syncs: from last synced day **minus 3 days** (late conversions) to today.
  `{"days": N}` forces a full re-sync of N days (max 730).
- Steps (independent; one failing → run `partial`): campaigns, ad_groups, keywords (keyword_view), search_terms
  (search_term_view, summed across matched keywords), ads (ad_group_ad, RSA text). Metrics for the window are
  replaced, so re-running never duplicates. A run stuck `running` > 30 min is marked failed.
- Scheduled sync (flag `ads_sync.scheduled.enabled`) is **not built yet**; use Windows Task Scheduler with the CLI.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p05_ads_sync/interface.py` | **public interface**: `summary`, `campaigns`, `ad_groups`, `keywords`, `search_terms`, `ads` (db, account_id, d1, d2) |
| `…/sync.py` | sync engine + GAQL queries |
| `…/service.py` | aggregations + derived metrics (CTR, CPC, conv rate, cost/conv) |
| `…/router.py` | `/api/v1/ads-sync` routes |
| `…/models.py` | warehouse tables |
| `…/cli.py` | `python -m app.modules.p05_ads_sync.cli sync [--days N]` |
| `backend/alembic/versions/0004_p05_ads_warehouse.py` | migration |
| `frontend/src/modules/ads-sync/*` | AdsDataFrame (account, 7/30/90d, Sync now), DataTable, SpendChart, pages |
| `frontend/src/app/{campaigns,ad-groups,keywords,search-terms}/page.tsx` | routes |

## Routes (`/api/v1/ads-sync`)
| Method | Path | Access |
|---|---|---|
| GET | `/accounts` | read |
| POST | `/accounts/{id}/sync` | recommend (analyst+) |
| GET | `/accounts/{id}/runs` | read |
| GET | `/accounts/{id}/summary` · `/campaigns` · `/ad-groups` · `/keywords` · `/search-terms` · `/ads` | read; `?days=` or `?date_from=&date_to=` |

## Tables
`campaigns`, `ad_groups`, `keywords`, `search_terms`, `ads`, `metrics_snapshots`, `sync_runs`
(`ad_assets` from the registry is not built yet — PMax/asset data comes with P09).

## Known limits
- Performance Max campaigns show at campaign level only (no keywords/search terms from `search_term_view`).
- Keywords/Search Terms pages are P05 data views; P08 adds intent classification and negative candidates on top.

## Acceptance criteria
- [x] Campaigns, ad groups, keywords, search terms, ads + daily metrics synced; incremental with lookback.
- [x] Sync health: per-step errors, partial/failed runs, stuck-run expiry, one run at a time per account.
- [x] Read-only toward Google (SELECT-only, no mutate).
- [x] Real sync of Corporate Cars Melbourne succeeded (2026-09-28: 4 campaigns, ad groups, 1.5k keyword rows, 2.8k search-term rows).
- [x] Dashboard pages: Campaigns (tiles, daily spend chart, table), Ad Groups, Keywords, Search Terms.
- [ ] User review and approval.
