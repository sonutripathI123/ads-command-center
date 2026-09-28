# P08 Changelog

## 2026-09-28 — initial build
- Deterministic classifier + negative candidates + insights; persistence of classifications/candidates/decisions.
- Negative review page with status tabs and confidence filter; copy/CSV export; keyword insights page.
- Tuned on real Corporate Cars data: multi-word excluded phrases seen with service words are downgraded
  ("rent a car with a chauffeur"); idle/duplicates only for enabled campaigns, duplicates within one campaign.
- Registry: depends_on adds P02.
- Status: `review`.
- Status: `approved_frozen` (user approved 2026-09-28).

## 2026-09-28 — registry only (no code change)
- Removed unused P14 from `depends_on` to break the cycle P07 → P08 → P14 → P07 created when P14 started consuming P07. P08 code never imported P14.
