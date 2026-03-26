from __future__ import annotations

import time
from psycopg import OperationalError
from app.db.connection import get_conn

SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS workspaces (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ingesting', 'indexed', 'failed')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_workspace_id ON documents(workspace_id);

CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  content TEXT NOT NULL,
  context_snippet TEXT NOT NULL,
  exact_quote TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  embedding VECTOR(768) NOT NULL,
  search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_workspace_id ON chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON chunks USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  citations JSONB NOT NULL DEFAULT '[]'::jsonb,
  retrieval_trace JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_workspace_id_created_at ON messages(workspace_id, created_at ASC);

CREATE TABLE IF NOT EXISTS query_audit_logs (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_query TEXT NOT NULL,
  route_strategy TEXT NOT NULL,
  retrieved_chunk_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
  response_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
  latency_ms INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_audit_logs_workspace_id ON query_audit_logs(workspace_id);
"""


def run_migrations() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()


def run_migrations_with_retry(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            run_migrations()
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(delay_seconds)
    if last_error:
        raise last_error


if __name__ == '__main__':
    run_migrations_with_retry()
    print('Migrations complete')
