# BackendFastAPI

Python FastAPI backend for the same frontend API contract.

## Stack

- FastAPI
- PostgreSQL + pgvector
- psycopg
- LangChain orchestration layer
- Ollama embeddings for ingestion + dense retrieval
- Groq chat model integration for answer generation

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

## How Indexing Works

When you upload a PDF, backend indexing does the following:

1. Reads PDF pages using `PyPDFLoader`
2. Splits text into chunks (`RecursiveCharacterTextSplitter`)
3. Generates embeddings for each chunk
4. Stores chunks + vectors in Postgres (`chunks.embedding`)

Because embeddings are generated during indexing, the embedding provider must be available at upload time.

## AI Configuration

Environment keys in `.env`:

- `EMBEDDING_PROVIDER` (current implementation expects `ollama`)
- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `EMBEDDING_MODEL` (example: `nomic-embed-text`)
- `EMBEDDING_DIMENSION` (must match DB vector size; default `768`)
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TEMPERATURE`

If indexing fails with an Ollama connection error, start Ollama and ensure the embedding model exists.

Example:

```bash
ollama serve
ollama pull nomic-embed-text
```

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
- `ChatPromptTemplate` + chat model chain for grounded answer generation

Retrieval/rerank and API contract stay the same.
