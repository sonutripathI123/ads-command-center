# AI Google Ads Specialist / PPC Command Center

A modular Google Ads command centre for the chauffeur business: connect → ingest → audit → research →
diagnose → recommend → **human approval** → execute → monitor → learn.

- Build contract: [docs/MID.md](docs/MID.md)
- Where things live: [docs/MODULE_REGISTRY.md](docs/MODULE_REGISTRY.md), [docs/PROJECT_MAP.md](docs/PROJECT_MAP.md)
- How to change things: [docs/CHANGE_PROTOCOL.md](docs/CHANGE_PROTOCOL.md)

## Local backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on Linux)
pip install -r requirements.txt
copy ..\.env.example .env         # then edit; set DATABASE_URL=sqlite:///./dev.db if no Postgres
python -m alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000/docs
python -m pytest -q
```

Or with Docker: `docker compose up` (Postgres + Redis + backend).

Live Google Ads changes are impossible while `ADS_EXECUTION_KILL_SWITCH=true` (the default).
