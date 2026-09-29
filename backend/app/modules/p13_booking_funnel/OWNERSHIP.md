# P13 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P13 |
| MODULE_NAME | Booking Funnel & Revenue Attribution |
| PURPOSE | Click → visit → lead → booking → revenue funnel and bottlenecks |
| OWNER_PATHS | `backend/app/modules/p13_booking_funnel/`, `frontend/src/modules/funnel/`, `frontend/src/app/bookings-revenue/` |
| OWNED_ROUTES | API `/api/v1/funnel/*`; UI `/bookings-revenue` |
| OWNED_COMPONENTS | FunnelPage |
| OWNED_SERVICES | funnel model, bottlenecks |
| OWNED_TABLES | none |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P06 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/funnel/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p13_booking_funnel tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
