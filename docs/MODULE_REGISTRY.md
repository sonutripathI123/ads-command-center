# Module Registry

**Start here for every change.** Find the module that owns the feature, then open
`backend/app/modules/<package>/MODULE.md` (and, from P01 onward, `frontend/src/modules/<slug>/MODULE.md`).

Source of truth: [`modules.json`](modules.json). The table below is generated — do not edit by hand.
Regenerate with `python scripts/gen_registry.py`; the test suite fails if it is stale.

Status lifecycle: `planned` → `in_progress` → `review` → `approved_frozen`
(a module only reaches `approved_frozen` after the user signs the acceptance gate in MID §22).

<!-- GENERATED:START -->
| ID | Module | Status | Backend package | API prefix | Tables | Flags |
|---|---|---|---|---|---|---|
| P00 | Foundation & Governance | `approved_frozen` | `backend/app/modules/p00_foundation/` | `/api/v1/foundation` | feature_flag_overrides | — |
| P01 | Dashboard Shell | `approved_frozen` | `backend/app/modules/p01_shell/` | — | — | — |
| P02 | Authentication & User Access | `approved_frozen` | `backend/app/modules/p02_auth/` | `/api/v1/auth` | users, sessions | — |
| P03 | Website Intelligence | `approved_frozen` | `backend/app/modules/p03_website_intel/` | `/api/v1/websites` | websites, pages, crawl_runs, page_signals, landing_page_mappings | crawler.enabled |
| P04 | Google Ads Connection | `approved_frozen` | `backend/app/modules/p04_ads_connection/` | `/api/v1/ads-connection` | ads_accounts, connections | — |
| P05 | Google Ads Data Sync & Warehouse | `approved_frozen` | `backend/app/modules/p05_ads_sync/` | `/api/v1/ads-sync` | campaigns, ad_groups, keywords, search_terms, ads, ad_assets, metrics_snapshots, sync_runs | ads_sync.scheduled.enabled |
| P06 | Analytics & Conversion Data | `approved_frozen` | `backend/app/modules/p06_analytics/` | `/api/v1/conversions` | conversion_events, leads, quotes, bookings, revenue_records, analytics_daily, search_console_daily, conversion_mappings, analytics_sync_runs | — |
| P07 | PPC Audit Engine | `approved_frozen` | `backend/app/modules/p07_ppc_audit/` | `/api/v1/audit` | audit_runs, audit_issues | — |
| P08 | Keyword & Search-Term Intelligence | `approved_frozen` | `backend/app/modules/p08_keyword_intel/` | `/api/v1/keywords` | keyword_candidates, negative_keyword_candidates, search_term_classifications | — |
| P09 | Ad & Creative Intelligence | `review` | `backend/app/modules/p09_ad_creative/` | `/api/v1/creatives` | ad_drafts, claim_checks | — |
| P10 | Landing Page & CRO Intelligence | `review` | `backend/app/modules/p10_landing_cro/` | `/api/v1/landing-pages` | landing_page_checks, cro_findings, implementation_briefs | — |
| P11 | Competitor Intelligence | `review` | `backend/app/modules/p11_competitor_intel/` | `/api/v1/competitors` | competitors, competitor_observations, competitor_analyses | competitor.research.enabled |
| P12 | Budget / Bid / Geo / Device / Time Intelligence | `planned` | `backend/app/modules/p12_budget_bid/` | `/api/v1/budget-bid` | segment_findings | — |
| P13 | Booking Funnel & Revenue Attribution | `review` | `backend/app/modules/p13_booking_funnel/` | `/api/v1/funnel` | — | — |
| P14 | AI Recommendation Engine | `approved_frozen` | `backend/app/modules/p14_recommendations/` | `/api/v1/recommendations` | recommendations, ai_runs, ai_evidence | ai.live_calls.enabled |
| P15 | AI Campaign Builder | `review` | `backend/app/modules/p15_campaign_builder/` | `/api/v1/campaign-builder` | campaign_drafts | — |
| P16 | Approval Center | `review` | `backend/app/modules/p16_approvals/` | `/api/v1/approvals` | approvals, approval_events | — |
| P17 | Google Ads Execution | `review` | `backend/app/modules/p17_ads_execution/` | `/api/v1/execution` | executions | ads.execution.enabled, ads.execution.automation.enabled |
| P18 | Monitoring & Alerts | `review` | `backend/app/modules/p18_monitoring/` | `/api/v1/monitoring` | alerts, monitor_checks | monitoring.scheduled.enabled |
| P19 | Reports & Exports | `review` | `backend/app/modules/p19_reports/` | `/api/v1/reports` | report_runs | — |
| P20 | Experiments | `review` | `backend/app/modules/p20_experiments/` | `/api/v1/experiments` | experiments | — |
| P21 | Business Memory & Rules | `approved_frozen` | `backend/app/modules/p21_business_rules/` | `/api/v1/business-rules` | business_rules, business_rule_versions | — |
| P22 | Security / Audit / Rollback | `review` | `backend/app/modules/p22_security_audit/` | `/api/v1/security` | audit_logs | — |
| P23 | Testing & QA | `planned` | `backend/app/modules/p23_testing_qa/` | — | — | — |
| P24 | Production Hardening | `review` | `backend/app/modules/p24_hardening/` | — | — | — |
<!-- GENERATED:END -->

## Shared code (owner: P00)

| Path | Public interface |
|---|---|
| `backend/app/shared/config.py` | `get_settings()` |
| `backend/app/shared/db.py` | `Base`, `get_db`, `session_scope`, `get_engine` |
| `backend/app/shared/errors.py` | `AppError`, `NotFoundError`, `ValidationFailed`, `PermissionDenied`, `FeatureDisabled` |
| `backend/app/shared/logging.py` | `get_logger(module_id)` |
| `backend/app/shared/feature_flags.py` | `is_enabled`, `require_enabled`, `resolve_all` |
| `backend/app/shared/flags_cli.py` | operator CLI (`python -m app.shared.flags_cli`) |
| `backend/app/shared/registry.py` | `load_registry()` |
| `backend/app/main.py` | app factory; auto-mounts active module routers |

Changing any file in this table is a **cross-module change** (MID §13).

## Feature → module lookup

| If the request mentions… | Module |
|---|---|
| health check, feature flags, module registry, logging, error format, migrations framework | P00 |
| navigation, layout, website/account selector, global alert banner | P01 |
| login, users, roles, permissions | P02 |
| crawl, sitemap, pages, schema, service/location detection | P03 |
| connect Google Ads, MCC / customer selection, connection status | P04 |
| sync, campaigns/ad groups/keywords/search terms data import, snapshots | P05 |
| GA4, conversion events, calls/forms, Driver App booking adapter, offline conversions | P06 |
| audit, account health, issues list | P07 |
| keyword research, intent, negatives, search-term review, overlap | P08 |
| RSA copy, ad variants, claim/policy checks | P09 |
| landing page match, CTA, form, trust signals, page speed, briefs | P10 |
| competitors, SERP observations, content gaps | P11 |
| budget pacing, geo/device/time/bid strategy | P12 |
| click→lead→quote→booking→revenue, attribution | P13 |
| recommendation schema, evidence, confidence, AI runs | P14 |
| new campaign draft, launch checklist | P15 |
| approve / reject / modify, approver, high-impact confirmation | P16 |
| push to Google Ads, mutation allowlist, kill switch behaviour | P17 |
| scheduled checks, spend spike / conversion drop alerts | P18 |
| daily/weekly/monthly reports, CSV/PDF | P19 |
| experiments, control/variant | P20 |
| services, locations, excluded intent, business priorities | P21 |
| audit log, before/after, rollback, secret handling | P22 |
| test fixtures, API mocks, QA harness | P23 |
| deployment, backups, rate limits, quota, recovery | P24 |
