# P07 Changelog

## 2026-09-28 — initial build
- 20 deterministic checks across tracking, account, bidding, keywords, search terms, ads, landing pages, organic.
- Runs, issues (MID §18 shape), dismissals by fingerprint, history; `/audit` page.
- Registry: depends_on P02, P03, P05, P06, P08, P14, P21.
- First real audit (Corporate Cars Melbourne): 4 critical — all campaigns paused, no GA4 key events,
  form submits not tracked, Maximize Conversions on weak data; "Ad group 1" holds 1,057 keywords.
- Status: `review`.
