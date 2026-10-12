# P15 Changelog

## 2026-09-29 — initial build
- Theme clustering, negatives (rental brands, P08/P21), landing-page choice from P03, default settings, launch checklist.
- Edit ops, per-ad-group ad writing via P09 `write_rsa`, approval gating, Google Ads Editor export (paused).
- Tuned on Corporate Cars "Ad group 1": plural-aware themes, "rental + driver" kept, generic theme → homepage.
- Campaign Builder page. Migration `0012_p15`. Registry: depends_on P02, P03, P05, P06, P08, P09, P21.
- Status: `review`.

## 2026-10-06 — approved and frozen by the owner
- Status `review` -> `approved_frozen`. Further changes need an explicit request that targets this module (docs/CHANGE_PROTOCOL.md).

## 2026-10-12 — match type can be changed per keyword (owner request)
- New edit op `set_match_type` (`from`, `text`, `match_type` = EXACT | PHRASE | BROAD) and a match-type dropdown on every
  keyword chip on the Campaign Builder page. The Editor export already writes whatever match type the keyword carries.
  The automatic rule is unchanged (converted keyword = EXACT, otherwise PHRASE). 1 new test.
