# P10 Tests

```bash
cd backend && python -m pytest app/modules/p10_landing_cro tests/isolation -q
```
`tests/test_p10.py` (no network): signal extraction (viewport, H1, CTAs incl. early CTA, FAQ/email not CTAs, tel/booking
links, form fields/required/button, trust, prices, GA4/Ads tags, schema); click-weighted plural-aware keyword coverage;
rules on a good vs bad page (every category), broken page → score 0, unlinked domain → tracking not verified; robots.txt
honoured and response timed (mock transport); template brief + markdown + Claude input; URL merging and removed ads;
check run, worst page first, P06 issues only on linked domains, history by run, account summary, interface scores;
brief template / live / AI failure (502); flag off (409), unknown ids, no ads, permissions.
