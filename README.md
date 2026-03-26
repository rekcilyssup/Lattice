# Lattice RAG System

Full-stack RAG application with:

- `Frontend/`: Next.js UI (workspaces, PDF upload, chat, citations)
- `BackendFastAPI/`: Python FastAPI backend (ingestion, hybrid retrieval, reranking, grounded responses)
- PostgreSQL + `pgvector` for vector search

## Project Structure

- `Frontend/` - UI app
- `BackendFastAPI/` - API server + migrations
- `Docs/` - architecture and requirements docs

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for local PostgreSQL + pgvector)

## 1) Start Database

```bash
cd BackendFastAPI
docker compose up -d
```

This starts PostgreSQL (`lattice`) with `pgvector` enabled on port `5433`.

## 2) Run Backend

```bash
cd BackendFastAPI
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.db.migrate
uvicorn app.main:app --reload --port 8080
```

Backend runs at: `http://localhost:8080`

Health check:

```bash
curl http://localhost:8080/api/v1/health
```

## 3) Run Frontend

Create `Frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api/v1
```

Then run:

```bash
cd Frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:3000`

## Main API Endpoints

- `GET /api/v1/health`
- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}`
- `GET /api/v1/workspaces/{workspace_id}/documents`
- `POST /api/v1/workspaces/{workspace_id}/documents/upload`
- `POST /api/v1/workspaces/{workspace_id}/chat`

## Notes

- Document indexing runs during upload: PDF text is chunked and embedded, then stored in Postgres.
- Dense retrieval uses vector embeddings from the configured embedding provider (default: Ollama).
- For backend-specific details, see `BackendFastAPI/README.md`.
