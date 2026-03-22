import json
import uuid
from time import perf_counter
from app.core.config import settings
from app.db.connection import get_conn
from app.services.ai import AIService
from app.utils.text import overlap_score
from app.utils.vector import to_pgvector


def _route(query: str) -> str:
    q = query.lower()
    metadata_hints = ['author', 'uploaded', 'upload date', 'document type', 'access level', 'which document']
    if any(h in q for h in metadata_hints):
        return 'metadata'
    if '"' in query:
        return 'keyword'
    return 'hybrid'


def _dense_search(workspace_id: str, vector: str, top_k: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id,c.document_id,d.name as document_name,c.page_number,c.content,c.context_snippet,c.exact_quote,
                       (1 - (c.embedding <=> %s::vector))::float8 as dense_score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.workspace_id=%s
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (vector, workspace_id, vector, top_k),
            )
            return [dict(r) for r in cur.fetchall()]


def _sparse_search(workspace_id: str, query: str, top_k: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id,c.document_id,d.name as document_name,c.page_number,c.content,c.context_snippet,c.exact_quote,
                       ts_rank(c.search_vector, plainto_tsquery('english', %s))::float8 as sparse_score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.workspace_id=%s AND c.search_vector @@ plainto_tsquery('english', %s)
                ORDER BY sparse_score DESC
                LIMIT %s
                """,
                (query, workspace_id, query, top_k),
            )
            return [dict(r) for r in cur.fetchall()]


async def ask_question(workspace_id: str, query: str) -> dict:
    started = perf_counter()
    ai = AIService()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages(id, workspace_id, role, content, citations) VALUES (%s,%s,'user',%s,%s::jsonb)",
                (str(uuid.uuid4()), workspace_id, query, '[]'),
            )
        conn.commit()

    route = _route(query)
    query_vec = None
    if route in {'hybrid', 'vector'}:
        emb = await ai.embed([query])
        query_vec = to_pgvector(emb[0], settings.EMBEDDING_DIMENSION)

    dense = _dense_search(workspace_id, query_vec, settings.TOP_K_DENSE) if query_vec else []
    sparse = _sparse_search(workspace_id, query, settings.TOP_K_SPARSE) if route in {'hybrid', 'keyword', 'metadata'} else []

    pool = {}
    for i, r in enumerate(dense):
        item = pool.get(r['id'], {**r, 'dense_score': 0.0, 'sparse_score': 0.0})
        item['dense_score'] = max(item['dense_score'], r.get('dense_score', 0.0) or 0.0)
        item['fused_score'] = item.get('fused_score', 0.0) + 0.55 * (1 / (60 + i + 1))
        pool[r['id']] = item

    for i, r in enumerate(sparse):
        item = pool.get(r['id'], {**r, 'dense_score': 0.0, 'sparse_score': 0.0})
        item['sparse_score'] = max(item['sparse_score'], r.get('sparse_score', 0.0) or 0.0)
        item['fused_score'] = item.get('fused_score', 0.0) + 0.45 * (1 / (60 + i + 1))
        pool[r['id']] = item

    reranked = sorted(
        [
            {
                **x,
                'rerank_score': overlap_score(query, x['content']) * 0.6 + x.get('dense_score', 0.0) * 0.25 + x.get('sparse_score', 0.0) * 0.15,
            }
            for x in pool.values()
        ],
        key=lambda z: z['rerank_score'],
        reverse=True,
    )[: settings.TOP_K_RERANK]

    contexts = [
        {
            'citationId': f"C{i+1}",
            'documentName': c['document_name'],
            'pageNumber': c['page_number'],
            'content': c['content'],
        }
        for i, c in enumerate(reranked)
    ]

    llm = await ai.generate_answer(query, contexts)
    answer = llm.get('answer') or 'Information not found.'

    citations = []
    if 'information not found' not in answer.lower():
        for i, c in enumerate(reranked[:3]):
            citations.append(
                {
                    'citation_id': str(i + 1),
                    'document_name': c['document_name'],
                    'page_number': c['page_number'],
                    'exact_quote': c['exact_quote'],
                    'context_snippet': c['context_snippet'],
                }
            )

    msg_id = str(uuid.uuid4())
    trace = {
        'routeStrategy': route,
        'retrievedCount': len(pool),
        'rerankedCount': len(reranked),
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages(id, workspace_id, role, content, citations, retrieval_trace) VALUES (%s,%s,'assistant',%s,%s::jsonb,%s::jsonb)",
                (msg_id, workspace_id, answer, json.dumps(citations), json.dumps(trace)),
            )
            cur.execute(
                "INSERT INTO query_audit_logs(id,workspace_id,user_query,route_strategy,retrieved_chunk_ids,response_message_id,latency_ms) VALUES (%s,%s,%s,%s,%s::uuid[],%s,%s)",
                (
                    str(uuid.uuid4()),
                    workspace_id,
                    query,
                    route,
                    [c['id'] for c in reranked],
                    msg_id,
                    int((perf_counter() - started) * 1000),
                ),
            )
        conn.commit()

    return {'answer': answer, 'citations': citations, 'routeStrategy': route, 'message': {'id': msg_id, 'role': 'assistant', 'content': answer, 'citations': citations}}
