# P08 Changelog

## 2026-09-28 — initial build
- Deterministic classifier + negative candidates + insights; persistence of classifications/candidates/decisions.
- Negative review page with status tabs and confidence filter; copy/CSV export; keyword insights page.
- Tuned on real Corporate Cars data: multi-word excluded phrases seen with service words are downgraded
  ("rent a car with a chauffeur"); idle/duplicates only for enabled campaigns, duplicates within one campaign.
- Registry: depends_on adds P02.
- Status: `review`.
