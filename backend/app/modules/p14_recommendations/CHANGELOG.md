# P14 Changelog

## 2026-09-28 — initial build
- Recommendation store (MID §18) fed by P07; priority; decision workflow; superseding.
- AI action plan: Claude Opus 5 via official SDK (structured output, refusal fallback) behind flag + key; template fallback.
- AI Recommendations page. Migration `0010_p14`. Dependency `anthropic>=1.8` added to requirements.txt.
- Registry: depends_on P02, P05, P07, P21, P22 (and P07 no longer lists P14, to avoid a cycle).
- Status: `review`.
