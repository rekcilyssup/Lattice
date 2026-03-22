# Database and API

This document summarizes the current schema and API surface.

## Database Schema (PostgreSQL + pgvector)

Defined in `Backend/src/migrations/001_init.sql`.

## Core tables

- **`workspaces`**
  - logical container for documents + chat
  - columns: `id`, `name`, `created_at`, `updated_at`

- **`documents`**
  - uploaded files per workspace
  - columns: `id`, `workspace_id`, `name`, `storage_path`, `status`, `metadata`, `error_message`, timestamps
  - `status`: `ingesting | indexed | failed`

- **`chunks`**
  - parsed/segmented text from documents
  - columns include: `document_id`, `page_number`, `content`, `context_snippet`, `exact_quote`, `metadata`
  - vector column: `embedding VECTOR(1536)`
  - sparse search column: generated `search_vector TSVECTOR`
  - indexes include GIN (`search_vector`) and IVFFlat (`embedding`)

- **`messages`**
  - conversation history
  - columns: `workspace_id`, `role`, `content`, `citations`, `retrieval_trace`, `created_at`

- **`query_audit_logs`**
  - observability/audit trail for retrieval quality
  - stores query text, route strategy, retrieved chunks, latency, response linkage

## Extensions/indexes

- `CREATE EXTENSION IF NOT EXISTS vector;`
- full-text and vector indexes are pre-created in migration

## API Base Path

All endpoints are mounted under:

- **`/api/v1`**

## Endpoints

## Health

- `GET /api/v1/health`
  - returns service status and timestamp

## Workspaces

- `GET /api/v1/workspaces`
  - list workspaces with aggregated documents/messages

- `POST /api/v1/workspaces`
  - create workspace
  - body:
    ```json
    { "name": "My Workspace" }
    ```

- `GET /api/v1/workspaces/:workspaceId`
  - fetch one workspace aggregate

## Documents

- `GET /api/v1/workspaces/:workspaceId/documents`
  - list documents in workspace

- `POST /api/v1/workspaces/:workspaceId/documents/upload`
  - multipart upload
  - field: `file` (PDF)
  - optional metadata supported
  - response is accepted immediately (`202`) while ingestion continues async

## Chat

- `POST /api/v1/workspaces/:workspaceId/chat`
  - body:
    ```json
    { "query": "What is ...?" }
    ```
  - response includes:
    - `answer`
    - `citations[]`
    - `routeStrategy`
    - stored assistant `message`

## Retrieval behavior (current)

Backend currently performs:

- query routing (`vector` / `keyword` / `metadata` / `hybrid`)
- dense retrieval (pgvector cosine similarity)
- sparse retrieval (Postgres full-text search)
- result fusion + reranking
- grounded generation with citation objects

