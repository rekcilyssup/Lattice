# Lattice Backend (RAG + PostgreSQL + pgvector)

This backend implements a modular RAG architecture for your frontend:

- Workspace management
- PDF upload and asynchronous ingestion
- Layout-aware PDF parsing
- Semantic chunking with metadata retention
- Hybrid retrieval (dense vector + sparse keyword + metadata search)
- Re-ranking layer (heuristic or Cohere)
- Grounded answer generation with strict citations
- Query audit logging

## Stack

- Node.js + TypeScript + Express
- PostgreSQL + `pgvector`
- `pdfjs-dist` for layout-aware extraction
- Ollama/OpenAI/Gemini pluggable embedding + LLM providers (with mock fallback)

## Architecture

`src/modules/*` is split by bounded context:

- `workspaces`: workspace CRUD and aggregation
- `documents`: upload/status/document repository
- `ingestion`: PDF parsing, chunking, embedding, indexing
- `retrieval`: router, dense+sparse retrieval, fusion, reranking
- `chat`: grounded QA orchestration + citation shaping
- `audit`: continuous query/retrieval/response logs
- `ai`: provider wrappers for embeddings and LLM output

Shared infrastructure:

- `src/config`: env parsing
- `src/db`: pool + migrations
- `src/http`: async/error middleware
- `src/shared`: logger, errors, utilities, types

## Prerequisites

- Node.js 20+
- PostgreSQL 16+ with `pgvector`

Quick local DB via Docker:

```bash
cd Backend
docker compose up -d
```

## Setup

```bash
cd Backend
cp .env.example .env
npm install
npm run migrate
npm run dev
```

Server runs at `http://localhost:8080`.

## API Endpoints

Base path: `/api/v1`

- `GET /health`
- `GET /workspaces`
- `POST /workspaces` `{ name }`
- `GET /workspaces/:workspaceId`
- `GET /workspaces/:workspaceId/documents`
- `POST /workspaces/:workspaceId/documents/upload` (multipart `file`)
- `POST /workspaces/:workspaceId/chat` `{ query }`

## Provider Configuration

Set providers in `.env`:

- Embeddings: `EMBEDDING_PROVIDER=ollama|openai|gemini|mock`
- LLM: `LLM_PROVIDER=ollama|openai|gemini|mock`

### Local Llama Testing (Default)

Default config is already set for Ollama + `llama3.2:1b` (lighter for local testing).

Install and pull models locally:

```bash
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

Run Ollama (if not already running):

```bash
ollama serve
```

Required keys:

- `OPENAI_API_KEY` for OpenAI providers
- `GEMINI_API_KEY` for Gemini providers
- `COHERE_API_KEY` if `RERANK_PROVIDER=cohere`
- No API key required for Ollama local testing

If keys are missing, backend falls back to deterministic mock providers.

## Notes on pgvector

Yes, you can absolutely do this in PostgreSQL with `pgvector`.
This implementation uses `pgvector` for dense retrieval plus PostgreSQL full-text search for sparse retrieval.

## Stop Services

- Stop backend dev server: press `Ctrl + C` in the backend terminal.
- Stop Postgres container:

```bash
cd Backend
docker compose down
```

- Full reset (remove DB volume):

```bash
cd Backend
docker compose down -v
```
