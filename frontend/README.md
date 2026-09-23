# Frontend — P01 Dashboard Shell (Next.js + TypeScript)

```bash
npm install
npm run dev        # http://localhost:3000  (backend expected at http://localhost:8000)
```

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if the backend runs elsewhere.

## Layout
```
src/
├── app/                    routes — thin; module pages render components from src/modules/<slug>
│   └── [section]/          placeholder for every section whose module isn't built yet
├── shell/                  P01: layout, navigation, scope selector, global status
│   └── index.ts            public interface — import as "@/shell"
└── modules/<slug>/         one folder per module (added from P03 on); index.ts is its public interface
```

Module ownership and rules: `backend/app/modules/p01_shell/MODULE.md` and `docs/CHANGE_PROTOCOL.md`.
