# P19 Tests

```bash
cd backend && python -m pytest app/modules/p19_reports tests/isolation -q
```
`tests/test_p19.py`: daily/weekly/monthly/custom periods and previous periods (incl. February), invalid periods; KPI
changes and headline; account report (previous-period call, campaigns filter, funnel, recommendations, approvals,
alerts), CSV sections, print-ready HTML, list without content; website report (issues filter, HTML escaping, GA4 note);
validation, unknown ids, options, interface; number alignment helper.
