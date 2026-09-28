# P21 — Business Memory & Rules

**Status:** approved_frozen (user approved 2026-09-28)

## Purpose
One versioned document of business facts that analysis modules use: services, areas served, places not served,
searches never wanted, competitor and brand names, thresholds (min spend / clicks before suggesting a negative,
target cost per conversion). Built-in chauffeur defaults apply until the first save.

## Behaviour
- Scopes: `global`, or `account:<ads_account_id>` (a saved account scope replaces global for that account).
- Every save that changes something creates a new version (who, when, note). Unchanged saves create nothing.
- Restore = save an old version again as a new version (history is never rewritten).
- Lists are normalised: lower-case, trimmed, de-duplicated.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p21_business_rules/interface.py` | **public interface**: `Rules`, `get_rules(db, account_id=None)` |
| `…/rules.py` | `Rules` model + chauffeur defaults |
| `…/service.py`, `router.py`, `models.py` | versioning, `/api/v1/business-rules`, tables |
| `backend/alembic/versions/0005_p21_business_rules.py` | migration |
| `frontend/src/modules/business-rules/*`, `frontend/src/app/business-rules/page.tsx` | Business Rules page |

## Routes
`GET ""` (read), `GET /defaults` (read), `PUT ""` (approve), `GET /versions` (read), `POST /versions/{v}/restore` (approve);
all accept `?account_id=`.

## Acceptance criteria
- [x] Services, locations, excluded intent, priorities (thresholds, target CPA) editable.
- [x] Versioned with author/time/note; restore.
- [x] Interface used by P08.
- [x] User review and approval (2026-09-28).
