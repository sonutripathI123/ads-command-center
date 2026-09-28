# P06 Tests

```bash
cd backend && python -m pytest app/modules/p06_analytics tests/isolation -q
```
`tests/test_p06.py`: service-account JWT (generated test key) + GA4/GSC pagination, missing key file, sync counts,
overview totals/channels/first day/queries, all health checks, idempotent re-sync, partial run on GSC permission error,
event roles + suggestions, bookings CSV (column aliases, AU dates incl. 2-digit years, "$1,200.50", website by domain,
PII columns ignored, cancelled excluded, Google Ads detection, re-import updates), required columns, permissions,
site without GA4/GSC. Google is a MockTransport fake; P02/P03/P05 replaced via their interfaces.
