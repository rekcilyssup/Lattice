from __future__ import annotations

import uuid
from pypdf import PdfReader
from app.db.connection import get_conn
from app.services.ai import AIService
from app.utils.text import create_snippet
from app.utils.vector import to_pgvector
from app.core.config import settings


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 180) -> list[str]:
    text = ' '.join(text.split())
    if not text:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        end = min(len(text), i + max_chars)
        chunks.append(text[i:end])
        if end == len(text):
            break
        i = end - overlap
    return chunks


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
            page_text = page.extract_text() or ''
            for chunk in _chunk_text(page_text):
                items.append(
                    {
                        'id': str(uuid.uuid4()),
                        'workspace_id': doc['workspace_id'],
                        'document_id': doc['id'],
                        'chunk_index': chunk_index,
                        'page_number': p_idx,
                        'content': chunk,
                        'context_snippet': create_snippet(chunk, 360),
                        'exact_quote': create_snippet(chunk, 180),
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
                            json_dumps(it['metadata']),
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


def json_dumps(value: dict) -> str:
    import json

    return json.dumps(value)
