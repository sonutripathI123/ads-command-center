# P03 Tests

```bash
cd backend && python -m pytest app/modules/p03_website_intel tests/isolation -q
```
- `tests/test_extract_crawl.py`: signal extraction (title/meta/H1/CTA/forms/phones/schema/links/images), issue rules,
  URL normalisation, sitemap index discovery, robots Disallow, same-site scope, non-HTML skip, link-crawl fallback, page cap.
- `tests/test_api.py`: create/validate/duplicate/update/archive, permissions, flag-off 409, full crawl → pages,
  signals, landing-page statuses, re-crawl without duplicates, 404s, interface. The site is a MockTransport fake.
