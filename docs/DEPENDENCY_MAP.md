# Dependency Map

Allowed **backend** dependencies between modules. Every module may use `app/shared` (P00).
A module may import another module **only** through `app/modules/<package>/interface.py`,
and only if the target is listed in its `depends_on` in [`modules.json`](modules.json).
This is enforced by `backend/tests/isolation/test_module_boundaries.py`.

Dependencies not listed here are **forbidden**. Adding one is a cross-module change and needs
the approval notice in [CHANGE_PROTOCOL.md](CHANGE_PROTOCOL.md#cross-module-gate).

Generated from `modules.json` — do not edit the table by hand.

<!-- GENERATED:START -->
| Module | May depend on (via `interface.py`) | Depended on by | May mutate Google Ads |
|---|---|---|---|
| P00 Foundation & Governance | — (shared only) | — | no |
| P01 Dashboard Shell | P02 Authentication & User Access | — | no |
| P02 Authentication & User Access | — (shared only) | P01, P03, P04, P05, P06, P07, P08, P09, P10, P11, P13, P14, P15, P16, P17, P18, P19, P20, P21, P22 | no |
| P03 Website Intelligence | P02 Authentication & User Access, P05 Google Ads Data Sync & Warehouse, P21 Business Memory & Rules | P06, P07, P10, P11, P13, P15, P18, P19, P20 | no |
| P04 Google Ads Connection | P02 Authentication & User Access | P05, P17 | no |
| P05 Google Ads Data Sync & Warehouse | P02 Authentication & User Access, P04 Google Ads Connection | P03, P06, P07, P08, P09, P10, P11, P12, P13, P14, P15, P16, P17, P18, P19, P20 | no |
| P06 Analytics & Conversion Data | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse | P07, P10, P12, P13, P15, P18, P19, P20 | no |
| P07 PPC Audit Engine | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data, P08 Keyword & Search-Term Intelligence, P21 Business Memory & Rules | P14 | no |
| P08 Keyword & Search-Term Intelligence | P02 Authentication & User Access, P05 Google Ads Data Sync & Warehouse, P21 Business Memory & Rules | P07, P15, P16 | no |
| P09 Ad & Creative Intelligence | P02 Authentication & User Access, P05 Google Ads Data Sync & Warehouse, P21 Business Memory & Rules, P22 Security / Audit / Rollback, P24 Production Hardening | P15, P16, P17 | no |
| P10 Landing Page & CRO Intelligence | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data, P21 Business Memory & Rules, P24 Production Hardening | — | no |
| P11 Competitor Intelligence | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P21 Business Memory & Rules, P24 Production Hardening | — | no |
| P12 Budget / Bid / Geo / Device / Time Intelligence | P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data, P14 AI Recommendation Engine | — | no |
| P13 Booking Funnel & Revenue Attribution | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data | P19 | no |
| P14 AI Recommendation Engine | P02 Authentication & User Access, P05 Google Ads Data Sync & Warehouse, P07 PPC Audit Engine, P21 Business Memory & Rules, P22 Security / Audit / Rollback, P24 Production Hardening | P12, P16, P19 | no |
| P15 AI Campaign Builder | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data, P08 Keyword & Search-Term Intelligence, P09 Ad & Creative Intelligence, P21 Business Memory & Rules | P16 | no |
| P16 Approval Center | P02 Authentication & User Access, P05 Google Ads Data Sync & Warehouse, P08 Keyword & Search-Term Intelligence, P09 Ad & Creative Intelligence, P14 AI Recommendation Engine, P15 AI Campaign Builder, P22 Security / Audit / Rollback | P17, P19, P20 | no |
| P17 Google Ads Execution | P02 Authentication & User Access, P04 Google Ads Connection, P05 Google Ads Data Sync & Warehouse, P09 Ad & Creative Intelligence, P16 Approval Center, P22 Security / Audit / Rollback | — | **YES — gated** |
| P18 Monitoring & Alerts | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data | P19 | no |
| P19 Reports & Exports | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data, P13 Booking Funnel & Revenue Attribution, P14 AI Recommendation Engine, P16 Approval Center, P18 Monitoring & Alerts | — | no |
| P20 Experiments | P02 Authentication & User Access, P03 Website Intelligence, P05 Google Ads Data Sync & Warehouse, P06 Analytics & Conversion Data, P16 Approval Center | — | no |
| P21 Business Memory & Rules | P02 Authentication & User Access | P03, P07, P08, P09, P10, P11, P14, P15 | no |
| P22 Security / Audit / Rollback | P02 Authentication & User Access | P09, P14, P16, P17 | no |
| P23 Testing & QA | — (shared only) | — | no |
| P24 Production Hardening | — (shared only) | P09, P10, P11, P14 | no |
<!-- GENERATED:END -->

## Hard rules

- `app/shared` must never import `app/modules/*`.
- Only **P17** may call Google Ads mutate APIs (checked by test). P04/P05 use read-only adapters.
- Frontend modules (P01+) follow the same rule: `frontend/src/modules/<slug>` may import another
  module's `index.ts` public exports only. (Enforced once P01 exists.)
- External APIs (Google Ads, GA4, Search Console, Claude, crawler/SERP, Driver App) are reached only through
  an adapter owned by one module, behind an internal interface.
