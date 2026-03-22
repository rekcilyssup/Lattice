# Architecture Overview

This repository is a **2-app system**:

- **Frontend**: Next.js app in `Frontend/`
- **Backend**: Node.js + Express + TypeScript API in `Backend/`
- **Database**: PostgreSQL with `pgvector` in Docker (`pgvector/pgvector:pg16`)

Think of it like this:

- **Frontend is the receptionist** (collects user request + shows results)
- **Backend is the operations team** (ingests docs, searches, generates answers)
- **Postgres is the records vault** (documents, chunks, vectors, messages, audits)

## Request/Data Flow

## 1) User action in the browser

User opens the Next.js app and can:

- create/select a workspace
- upload a PDF
- ask a question

Frontend calls backend using `NEXT_PUBLIC_API_BASE_URL` (typically `http://localhost:8080/api/v1`).

## 2) Frontend -> Backend HTTP API

The frontend sends requests to Express routes:

- `/workspaces`
- `/workspaces/:workspaceId/documents/upload`
- `/workspaces/:workspaceId/chat`

All traffic is plain JSON/multipart HTTP from browser to backend.

## 3) Backend processing pipeline

When a PDF is uploaded:

- backend stores file in `Backend/storage/uploads`
- document is marked `ingesting`
- ingestion job parses PDF text (`pdfjs-dist`), chunks text, creates embeddings
- chunks + vectors are written to Postgres
- document status becomes `indexed`

When a question is asked:

- backend stores user message
- semantic router chooses retrieval mode (`vector`, `keyword`, `metadata`, or `hybrid`)
- runs retrieval against `chunks` table:
  - dense vector similarity (`pgvector`)
  - sparse text search (`tsvector` / full-text search)
- re-ranks retrieved chunks
- sends selected context to configured LLM (default local Ollama)
- saves assistant answer + citations + retrieval trace + audit log
- returns answer + citations to frontend

## 4) Backend -> Postgres connection

Backend uses `pg` driver and env-based connection settings (`POSTGRES_*`).

Docker Postgres is exposed as:

- host: `127.0.0.1`
- port: `5433` (host) -> `5432` (container)

Critical detail:

- `docker-compose.yml` uses **5433** on host
- if backend `.env` uses 5432, it may hit your local machine Postgres instead of Docker

## Runtime Stack in this repo

- Frontend scripts: `next dev`, `next build`
- Backend scripts: `tsx watch src/index.ts`, `tsx src/db/migrate.ts`
- Backend middleware: `cors`, `helmet`, JSON body parser, request logging
- File upload: `multer`
- DB migration: SQL in `Backend/src/migrations/001_init.sql`

