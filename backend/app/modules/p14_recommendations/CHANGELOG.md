# P14 Changelog

## 2026-09-28 — initial build
- Recommendation store (MID §18) fed by P07; priority; decision workflow; superseding.
- AI action plan: Claude Opus 5 via official SDK (structured output, refusal fallback) behind flag + key; template fallback.
- AI Recommendations page. Migration `0010_p14`. Dependency `anthropic>=1.8` added to requirements.txt.
- Registry: depends_on P02, P05, P07, P21, P22 (and P07 no longer lists P14, to avoid a cycle).
- Status: `review`.
- Status: `approved_frozen` (user approved 2026-09-28).

## 2026-09-28 — fix found in the first live run (after approval)
- Live Claude plan returned an extra empty week; empty weeks are now dropped. Files: `service.py` (+1 line), test.
- `ai.live_calls.enabled` switched on (user: "AI on karo"). First live plan: claude-opus-5, ~5k in / ~5k out tokens.
