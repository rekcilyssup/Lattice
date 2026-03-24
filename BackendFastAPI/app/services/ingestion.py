from __future__ import annotations

import json
import uuid
from pypdf import PdfReader
from app.db.connection import get_conn
from app.services.ai import AIService
from app.utils.text import create_snippet
from app.utils.vector import to_pgvector
from app.core.config import settings


def _sanitize_text(raw: str) -> str:
    # Some PDFs contain NUL bytes/control chars that Postgres TEXT cannot store.
    cleaned = raw.replace('\x00', ' ')
    cleaned = ''.join(ch if (ch >= ' ' or ch in '\n\r\t') else ' ' for ch in cleaned)
    return cleaned


async def ingest_document(document_id: str) -> None:
    ai = AIService()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, workspace_id, name, storage_path, metadata FROM documents WHERE id = %s", (document_id,))
            doc = cur.fetchone()
            if not doc:
                return

    try:
        reader = PdfReader(doc['storage_path'])
        items: list[dict] = []
        chunk_index = 0

        for p_idx, page in enumerate(reader.pages, start=1):
            page_text = _sanitize_text(page.extract_text() or '')
            for chunk in ai.split_text(page_text):
                safe_chunk = _sanitize_text(chunk)
                items.append(
                    {
                        'id': str(uuid.uuid4()),
                        'workspace_id': doc['workspace_id'],
                        'document_id': doc['id'],
                        'chunk_index': chunk_index,
                        'page_number': p_idx,
                        'content': safe_chunk,
                        'context_snippet': create_snippet(safe_chunk, 360),
                        'exact_quote': create_snippet(safe_chunk, 180),
                        'metadata': {'documentName': doc['name'], **(doc.get('metadata') or {})},
                    }
                )
                chunk_index += 1

        vectors = await ai.embed([x['content'] for x in items])

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE document_id = %s", (doc['id'],))

                for i, it in enumerate(items):
                    cur.execute(
                        """
                        INSERT INTO chunks(
                          id, workspace_id, document_id, chunk_index, page_number,
                          content, context_snippet, exact_quote, metadata, embedding
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::vector)
                        """,
                        (
                            it['id'],
                            it['workspace_id'],
                            it['document_id'],
                            it['chunk_index'],
                            it['page_number'],
                            it['content'],
                            it['context_snippet'],
                            it['exact_quote'],
                            json.dumps(it['metadata']),
                            to_pgvector(vectors[i], settings.EMBEDDING_DIMENSION),
                        ),
                    )

                cur.execute("UPDATE documents SET status='indexed', error_message=NULL, updated_at=NOW() WHERE id=%s", (doc['id'],))
            conn.commit()
    except Exception as e:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET status='failed', error_message=%s, updated_at=NOW() WHERE id=%s",
                    (str(e), doc['id']),
                )
            conn.commit()


