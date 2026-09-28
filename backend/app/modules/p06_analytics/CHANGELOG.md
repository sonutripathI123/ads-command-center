# P06 Changelog

## 2026-09-28 — initial build
- GA4 + Search Console read-only sync via service account (no new dependency: JWT signed with `cryptography`).
- Conversion mapping with suggestions; tracking health checks; bookings CSV import (no personal data).
- Conversions & Analytics page. Migration `0008_p06`. Registry: depends_on adds P05; tables list extended.
- First real sync (Corporate Cars Melbourne): GA4 only from 2026-09-14, 0 key events, form_start without submit.
- Status: `review`.
- Status: `approved_frozen` (user approved 2026-09-28). Driver App adapter not approved yet.

## 2026-09-28 — change request (user): separate GA4 and Search Console
- Conversions page split into tabs: Google Analytics (GA4) / Search Console / Bookings, each with a plain-English
  explanation, its own tiles and its own health warnings. Search Console tab adds click rate and average position.
- Only file changed: `frontend/src/modules/conversions/ConversionsPage.tsx`. Backend/API unchanged.
