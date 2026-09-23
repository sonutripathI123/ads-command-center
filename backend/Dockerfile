# Build context is the repo root so docs/modules.json is available at runtime.
FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY docs/modules.json docs/modules.json
COPY backend backend
WORKDIR /srv/backend
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
