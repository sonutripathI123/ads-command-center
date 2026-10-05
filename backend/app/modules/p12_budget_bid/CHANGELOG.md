# P12 Changelog

## 2026-10-05 — initial build
- Read-only device / weekday / time-of-day / location / budget analysis from Google Ads (GAQL SELECT via P04), stored as
  snapshots + findings. Findings carry evidence, confidence and a proposed action; statistical guard against calling luck "waste".
- Migration `0021_p12`. Registry: status `review`; `depends_on` changed from P05, P06, P14 to P02, P04, P21 (what the code
  actually imports); tables `segment_runs`, `segment_findings`.
- First real run (90 days): flagged AUD 296 of clicks from outside Australia, two places marked "not served" that still got
  spend, 44% of searches lost on ad rank, and Maximize-clicks bidding. No change was made to Google Ads.
- Not done: applying bid adjustments/schedules (P17 supports only negatives + RSAs), ad-group/keyword-level and audience segments.
