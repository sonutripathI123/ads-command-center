# P03 — Website Intelligence

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Onboard each business website (domain, main service, area, linked Google Ads account, GA4 property,
Search Console property), scan it politely, and record page-level landing-page signals and issues.
Maps every ad final URL of the linked account to a scanned page (broken / not scanned / other domain).

## Scanning (`crawler.py`, flag `crawler.enabled`, default OFF)
- robots.txt honoured (incl. Crawl-delay, capped 5 s); user agent `PPCCommandCenterBot/0.1`.
- URLs from sitemaps (robots.txt `Sitemap:` / `/sitemap.xml` / indexes), else same-site link crawl.
- Same site only (www = non-www), HTML only, page cap (default 50, max 300), 0.5 s between requests, 15 s timeout.
- No JavaScript execution — JS-only pages will look thin (itself a signal).

## Signals per page (`extract.py`)
title, meta description, canonical, robots meta, viewport, lang, H1/H2, word count, CTAs (book/quote/call/enquire),
forms + fields, phone numbers + tel links, schema.org types, internal/external links, images without alt,
response time, services/areas found (from P21 rules). Issues: http_error, noindex, missing title/meta/H1,
multiple H1, thin content, no CTA, no form or phone, no viewport, slow (> 3 s), no service mention.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p03_website_intel/interface.py` | **public interface**: `WebsiteRef`, `list_websites`, `website_pages`, `landing_pages` |
| `…/crawler.py`, `extract.py` | crawler + HTML extraction (stdlib only) |
| `…/service.py`, `router.py`, `models.py` | websites CRUD, crawl runs, pages, landing-page mapping; `/api/v1/websites` |
| `backend/alembic/versions/0007_p03_websites.py` | migration |
| `frontend/src/modules/websites/*`, `frontend/src/app/websites/**` | Websites list/add, website detail (Issues, All pages, Ad landing pages) |

## Routes (`/api/v1/websites`)
`GET /meta` · `GET ""` · `POST ""` (approve) · `GET /{id}` · `PATCH /{id}` (approve) · `POST /{id}/crawl` (recommend, flag) ·
`GET /{id}/crawls` · `GET /{id}/pages` · `GET /{id}/pages/{page_id}` · `GET /{id}/landing-pages` · `POST /{id}/landing-pages/refresh` (recommend)

## Acceptance criteria
- [x] Website onboarding with Ads/GA4/GSC links, validation, archive.
- [x] Sitemap/robots-aware crawl; page extraction; service/location detection; issues; crawl history.
- [x] Landing-page relevance records (ad final URL → page status).
- [x] Real test scan of corporatecarsmelbourne.com.au (8 pages, 2026-09-28).
- [ ] `crawler.enabled` switched on (needs an approved way to set flags — see CHANGELOG).
- [ ] User review and approval.
