# P13 Tests

```bash
cd backend && python -m pytest app/modules/p13_booking_funnel tests/isolation -q
```
`tests/test_p13.py`: stage values, rates, cost per stage, change vs previous, lead estimate; unmeasured stages are None
(not 0) with the right bottlenecks; weak-funnel bottlenecks (CTR, lost clicks, no Ads bookings, ROAS < 1, booking rate);
partial GA4 skips click → visit; API: previous-period dates, campaign filter + reported ROAS, booking quality, invalid
period, unknown website, website without account/bookings; interface.
