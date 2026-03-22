# BackendFastAPI

Python FastAPI backend for the same frontend API contract.

## Stack

- FastAPI
- PostgreSQL + pgvector
- psycopg
- Ollama/OpenAI/Gemini-ready AI layer

## Run Locally

1. Start DB:

```bash
cd BackendFastAPI
docker compose up -d
```

2. Create env and set DB port to `5433`:

```bash
cp .env.example .env
```

3. Create venv + install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run migration:

```bash
python -m app.db.migrate
```

5. Start server:

```bash
uvicorn app.main:app --reload --port 8080
```

Health:

```bash
curl http://localhost:8080/api/v1/health
```

## API Endpoints

- `GET /api/v1/health`
- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}`
- `GET /api/v1/workspaces/{workspace_id}/documents`
- `POST /api/v1/workspaces/{workspace_id}/documents/upload`
- `POST /api/v1/workspaces/{workspace_id}/chat`

## Frontend Integration

Set frontend env:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api/v1
```

No frontend code changes required.
