# Local Development Setup

This is the **exact** sequence to run this project from a fresh clone.

## Prerequisites

- Node.js 20+ (22 recommended)
- Docker Desktop / OrbStack running
- Optional for local LLM: Ollama

## 1) Start PostgreSQL (Docker)

From repo root:

```bash
cd Backend
docker compose up -d
```

Verify container is running:

```bash
docker compose ps
```

## 2) Configure backend env (important)

Create backend env file:

```bash
cd Backend
cp .env.example .env
```

Open `Backend/.env` and set DB values to match Docker mapping:

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=lattice
POSTGRES_USER=lattice
POSTGRES_PASSWORD=lattice
```

Why this matters:

- `docker-compose.yml` maps host port **5433** to container 5432
- Using 5432 can accidentally connect to a locally installed Postgres and fail with role/db errors

## 3) Optional: configure local Ollama (default provider)

The backend defaults to Ollama for testing.

Pull models:

```bash
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

Start Ollama server if needed:

```bash
ollama serve
```

If you want OpenAI/Gemini later, add keys in `Backend/.env` and switch provider fields.

## 4) Install backend dependencies + run migrations

```bash
cd Backend
npm install
npm run migrate
```

You should see migration success logs.

## 5) Start backend

```bash
cd Backend
npm run dev
```

Health check:

```bash
curl http://localhost:8080/api/v1/health
```

Expected response contains `"status":"ok"`.

## 6) Configure frontend env

```bash
cd Frontend
cp .env.example .env.local
```

Set:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api/v1
```

## 7) Start frontend

```bash
cd Frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

## 8) Quick smoke test

- Create/select a workspace
- Upload a PDF
- Wait until status shows `Indexed`
- Ask a question
- Verify citations appear

## Troubleshooting (common)

## Error: `role "lattice" does not exist`

You are connecting to the wrong Postgres instance (often local Postgres, not Docker).

Fix:

1. Ensure `POSTGRES_PORT=5433`
2. Test connection explicitly:

```bash
PGPASSWORD=lattice psql -h 127.0.0.1 -p 5433 -U lattice -d lattice -c "select current_user, current_database();"
```

## Full DB reset

```bash
cd Backend
docker compose down -v
docker compose up -d
npm run migrate
```

## Stop everything

- Press `Ctrl + C` in frontend/backend terminals
- Stop DB:

```bash
cd Backend
docker compose down
```

