from __future__ import annotations

import json
import uuid
from langchain_community.document_loaders import PyPDFLoader
from app.db.connection import get_conn
from app.services.ai import AIService
from app.utils.text import create_snippet
from app.utils.vector import to_pgvector
from app.core.config import settings


def _sanitize_text(raw: str) -> str:
    # Some PDFs contain NUL bytes/control chars that Postgres TEXT cannot store.
    cleaned = raw.replace('\x00', ' ')  # NUL bytes break the Postgres TEXT column
    cleaned = ''.join(ch if (ch >= ' ' or ch in '\n\r\t') else ' ' for ch in cleaned)  # strip other control chars
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
        # Load the document using LangChain's loader to preserve cross-page context
        loader = PyPDFLoader(doc['storage_path'])  # keeps per-page metadata for citations
        langchain_docs = loader.load()
        
        # Split the document as a whole. This ensures chunk_overlap bridges page breaks!
        split_docs = ai._splitter.split_documents(langchain_docs)  # whole doc, so overlap bridges pages
        
        items: list[dict] = []
        for chunk_index, chunk in enumerate(split_docs):  # deterministic ordering
            safe_chunk = _sanitize_text(chunk.page_content)  # before it reaches Postgres
            # PyPDFLoader stores the page number (0-indexed) in metadata
            p_idx = chunk.metadata.get('page', 0) + 1  # 0-indexed in PyPDF, 1-indexed for humans 
            
            items.append(
                {
                    'id': str(uuid.uuid4()),
                    'workspace_id': doc['workspace_id'],
                    'document_id': doc['id'],
                    'chunk_index': chunk_index,
                    'page_number': p_idx,
                    'content': safe_chunk,
                    'context_snippet': create_snippet(safe_chunk, 360),  # shown in the UI
                    'exact_quote': create_snippet(safe_chunk, 180),  # the cited passage
                    'metadata': {'documentName': doc['name'], **(doc.get('metadata') or {})},
                }
            )

        vectors = await ai.embed([x['content'] for x in items])  # one batch call, not per chunk

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE document_id = %s", (doc['id'],))  # re-ingest must not duplicate

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

                cur.execute("UPDATE documents SET status='indexed', error_message=NULL, updated_at=NOW() WHERE id=%s", (doc['id'],))  # mark done
            conn.commit()
    except Exception as e:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(  # embedding goes in as a pgvector literal
                    "UPDATE documents SET status='failed', error_message=%s, updated_at=NOW() WHERE id=%s",  # never leave it stuck in processing
                    (str(e), doc['id']),
                )
            conn.commit()