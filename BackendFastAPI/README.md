# BackendFastAPI

Python FastAPI backend for the same frontend API contract.

## Stack

- FastAPI
- PostgreSQL + pgvector
- psycopg
- LangChain orchestration layer
- Ollama/OpenAI/Gemini-ready AI providers

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

Note:

- Server startup now auto-runs migrations with retry.
- Manual migration command is still useful for explicit checks.

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

## LangChain Usage

This backend now uses LangChain primitives for core RAG orchestration:

- `RecursiveCharacterTextSplitter` for chunking
- `OllamaEmbeddings` for embeddings
- `ChatPromptTemplate` + `ChatOllama` + `JsonOutputParser` for grounded answer generation

Retrieval/rerank and API contract stay the same.
