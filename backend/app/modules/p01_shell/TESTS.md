# P01 Tests

```bash
cd backend && python -m pytest app/modules/p01_shell tests/isolation -q   # contract + boundary tests
cd frontend && npx tsc --noEmit && npm run lint && npm run build          # type, lint, build
```

`tests/test_p01_shell.py` checks: nav == MID §19 sections, unique slugs, registered module IDs,
shell never imports feature modules, shell only calls the P00 API, feature modules import only public
interfaces (`@/shell`, `@/modules/<slug>`), no remote fonts / hard-coded secrets.
