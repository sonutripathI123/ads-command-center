# P10 Changelog

## 2026-09-29 — initial build
- Landing URLs from P05 ads (any owned domain), polite fetch, CRO signal extraction, findings + score, briefs (Claude or
  template) with Markdown download. Landing Pages page. Migration `0015_p10`.
- Registry: depends_on P02, P03, P05, P06, P21 (P14 removed — not used); tables landing_page_checks, cro_findings,
  implementation_briefs. Status: `review`.

## 2026-10-06 — approved and frozen by the owner
- Status `review` -> `approved_frozen`. Further changes need an explicit request that targets this module (docs/CHANGE_PROTOCOL.md).
