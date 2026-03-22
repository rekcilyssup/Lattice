# Lattice RAG System

Full-stack RAG application with:

- `Frontend/`: Next.js UI (workspaces, PDF upload, chat, citation cards)
- `Backend/`: Modular Node.js/TypeScript API (ingestion, hybrid retrieval, reranking, grounded generation)
- PostgreSQL + `pgvector` for vector search

## Project Structure

- `Frontend/` - UI app
- `Backend/` - API server + migrations
- `Docs/srs.md` - functional and non-functional requirements

## Prerequisites

- Node.js 20+ (22 recommended)
- Docker (for local PostgreSQL + pgvector)

## 1) Start Database

```bash
cd Backend
docker compose up -d
```

This starts PostgreSQL (`lattice`) with `pgvector` enabled.

## 2) Run Backend

```bash
cd Backend
cp .env.example .env
npm install
npm run migrate
npm run dev
```

Backend runs at: `http://localhost:8080`

Health check:

```bash
curl http://localhost:8080/api/v1/health
```

## 3) Run Frontend

```bash
cd Frontend
cp .env.example .env.local
```

Set this in `Frontend/.env.local`:

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

## Build Checks

Backend build:

```bash
cd Backend
npm run build
```

Frontend build:

```bash
cd Frontend
npm run build
```

## Stop Everything

If backend/frontend are running in terminals:

- Press `Ctrl + C` in each terminal window.

Stop Docker Postgres (`pgvector`):

```bash
cd Backend
docker compose down
```

If you also want to remove DB data volume (full reset):

```bash
cd Backend
docker compose down -v
```

If any process is still occupying ports:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8080 -sTCP:LISTEN
lsof -nP -iTCP:5433 -sTCP:LISTEN
```

Then kill by PID if needed:

```bash
kill -9 <PID>
```

## Main API Endpoints

- `GET /api/v1/health`
- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/:workspaceId`
- `GET /api/v1/workspaces/:workspaceId/documents`
- `POST /api/v1/workspaces/:workspaceId/documents/upload`
- `POST /api/v1/workspaces/:workspaceId/chat`

## Notes

- Yes, this system is designed to run embeddings in PostgreSQL using `pgvector`.
- Retrieval strategy is hybrid: dense vector + sparse keyword + reranking.
- Detailed backend module docs are in `Backend/README.md`.
# Lattice
