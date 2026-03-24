import json
import re
import uuid
from time import perf_counter
from app.core.config import settings
from app.db.connection import get_conn
from app.services.ai import AIService
from app.utils.query import is_metric_query, is_temporal_query, is_technical_query, is_social_query, is_multi_part_query
from app.utils.text import overlap_score
from app.utils.vector import to_pgvector


_STOPWORDS = {
    'the',
    'a',
    'an',
    'is',
    'are',
    'was',
    'were',
    'to',
    'for',
    'of',
    'and',
    'or',
    'in',
    'on',
    'at',
    'by',
    'with',
    'from',
    'what',
    'which',
    'how',
    'can',
    'you',
    'about',
    'this',
    'that',
    'it',
    'be',
    'as',
    'my',
    'our',
}


def _query_terms(query: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) >= 3 and t not in _STOPWORDS}


def _extract_query_facets(query: str) -> list[str]:
    cleaned = re.sub(r'\s+', ' ', query).strip()
    if not cleaned:
        return []

    parts = re.split(r'\?+|;|,\s+|\s+\band\b\s+|\s+\bbut\b\s+|\s+\bplus\b\s+', cleaned, flags=re.IGNORECASE)
    facets: list[str] = [cleaned]
    for part in parts:
        p = part.strip()
        if len(p) >= 10:
            facets.append(p)

    deduped: list[str] = []
    seen: set[str] = set()
    for facet in facets:
        key = facet.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(facet)

    return deduped[:4]


def _has_numeric_evidence(text: str) -> bool:
    t = text.lower()
    has_number = bool(re.search(r'\b\d[\d,\.]*\b', t))
    has_unit = bool(re.search(r'\b(mld|mgd|km|crore|lakh|percent|percentage|rs|₹|pond|ponds|waterbody|waterbodies)\b', t))
    return has_number or has_unit


def _has_temporal_evidence(text: str) -> bool:
    t = text.lower()
    return bool(
        re.search(
            r'\b(20\d{2}|19\d{2}|year|years|month|months|phase|phases|stage|stages|timeline|latency|minute|minutes|second|seconds|year\s*\d|years\s*\d)\b',
            t,
        )
    )


def _has_technical_evidence(text: str) -> bool:
    t = text.lower()
    return bool(
        re.search(
            r'\b(technical architecture|architecture|model|algorithm|framework|pipeline|u-?net|cnn|lstm|resnet|contrastive|xgboost)\b',
            t,
        )
    )


def _has_social_evidence(text: str) -> bool:
    t = text.lower()
    return bool(
        re.search(
            r'\b(family model|community|citizen|stakeholder|inclusion|accessibility|digital literacy|elder|youth|children|training|cooperative|governance)\b',
            t,
        )
    )


def _metric_boost(query: str, chunk: dict) -> float:
    if not is_metric_query(query):
        return 0.0

    content = (chunk.get('content') or '').lower()
    query_terms = _query_terms(query)
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))

    number_hits = len(re.findall(r'\b\d[\d,\.]*\b', content))
    unit_hits = len(re.findall(r'\b(mld|mgd|km|crore|lakh|percent|percentage|rs|₹|pond|ponds|waterbody|waterbodies)\b', content))

    return min(0.35, overlap * 0.22 + number_hits * 0.02 + unit_hits * 0.04)


def _temporal_boost(query: str, chunk: dict) -> float:
    if not is_temporal_query(query):
        return 0.0

    content = (chunk.get('content') or '').lower()
    query_terms = _query_terms(query)
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))
    temporal_hits = len(
        re.findall(r'\b(20\d{2}|19\d{2}|year|years|month|months|phase|phases|stage|stages|timeline|latency|minute|minutes|second|seconds)\b', content)
    )
    return min(0.3, overlap * 0.18 + temporal_hits * 0.02)


def _technical_boost(query: str, chunk: dict) -> float:
    if not is_technical_query(query):
        return 0.0

    content = (chunk.get('content') or '').lower()
    query_terms = _query_terms(query)
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))
    model_hits = len(re.findall(r'\b(u-?net|cnn|lstm|resnet|contrastive|xgboost)\b', content))
    arch_hits = len(re.findall(r'\b(technical architecture|architecture|framework|algorithm|pipeline)\b', content))
    return min(0.35, overlap * 0.24 + model_hits * 0.05 + arch_hits * 0.03)


def _social_boost(query: str, chunk: dict) -> float:
    if not is_social_query(query):
        return 0.0

    content = (chunk.get('content') or '').lower()
    query_terms = _query_terms(query)
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))
    social_hits = len(
        re.findall(
            r'\b(family model|community|citizen|stakeholder|inclusion|accessibility|digital literacy|elder|youth|children|training|cooperative|governance)\b',
            content,
        )
    )
    return min(0.28, overlap * 0.2 + social_hits * 0.03)


def _expand_sparse_query(query: str) -> str:
    expanded = query

    # Named section references — include the section number as a bare term so FTS can match it.
    section_match = re.findall(r'section\s*(\d+(?:\.\d+)*)', query.lower())
    for sec in section_match:
        expanded += f' OR "{sec}"'

    if is_technical_query(query):
        expanded += ' OR "technical architecture" OR architecture OR model OR framework OR algorithm OR pipeline OR unet OR cnn OR lstm OR resnet OR contrastive OR xgboost'

    if is_social_query(query):
        expanded += ' OR "family model" OR community OR stakeholder OR inclusion OR accessibility OR "digital literacy" OR elder OR youth OR children OR training OR governance'

    if is_metric_query(query):
        expanded += ' OR demand OR projected OR current OR status OR value OR metric OR mld OR mgd OR crore OR lakh OR count'

    if is_temporal_query(query):
        expanded += ' OR year OR years OR month OR months OR phase OR stages OR timeline OR latency OR transition OR roadmap'

    return expanded


def _select_context_chunks(query: str, reranked: list[dict]) -> list[dict]:
    if not reranked:
        return []

    top_score = float(reranked[0].get('rerank_score', 0.0) or 0.0)
    if is_multi_part_query(query):
        # Multi-part questions need more context to answer every sub-part.
        min_score = max(0.12, top_score * 0.28)
        limit = 15
    elif is_metric_query(query):
        min_score = max(0.16, top_score * 0.35)
        limit = 6
    elif is_temporal_query(query):
        min_score = max(0.15, top_score * 0.33)
        limit = 6
    elif is_technical_query(query):
        min_score = max(0.15, top_score * 0.32)
        limit = 6
    elif is_social_query(query):
        min_score = max(0.16, top_score * 0.34)
        limit = 6
    else:
        min_score = max(0.20, top_score * 0.45)
        limit = 10

    selected = [c for c in reranked if float(c.get('rerank_score', 0.0) or 0.0) >= min_score]

    if not selected:
        selected = [reranked[0]]

    # Keep context tight to reduce drift and irrelevant citations.
    return selected[:limit]


def _select_citation_chunks(query: str, answer: str, context_chunks: list[dict], llm_citation_ids: list[str]) -> list[dict]:
    by_id = {f"C{i+1}": c for i, c in enumerate(context_chunks)}
    picked: list[dict] = []

    for cid in llm_citation_ids:
        chunk = by_id.get(cid.upper())
        if chunk:
            picked.append(chunk)

    if not picked:
        picked = context_chunks[:2]

    top_score = float(context_chunks[0].get('rerank_score', 0.0) or 0.0) if context_chunks else 0.0
    min_score = max(0.18, top_score * 0.35)
    picked = [c for c in picked if float(c.get('rerank_score', 0.0) or 0.0) >= min_score]

    if is_metric_query(query):
        metric_picked = [c for c in picked if _has_numeric_evidence(c.get('content', ''))]
        if metric_picked:
            picked = metric_picked
        elif context_chunks:
            metric_candidates = [c for c in context_chunks if _has_numeric_evidence(c.get('content', ''))]
            if metric_candidates:
                picked = metric_candidates[:2]

    if is_temporal_query(query):
        temporal_picked = [c for c in picked if _has_temporal_evidence(c.get('content', ''))]
        if temporal_picked:
            picked = temporal_picked
        elif context_chunks:
            temporal_candidates = [c for c in context_chunks if _has_temporal_evidence(c.get('content', ''))]
            if temporal_candidates:
                picked = temporal_candidates[:2]

    if is_technical_query(query):
        tech_picked = [c for c in picked if _has_technical_evidence(c.get('content', ''))]
        if tech_picked:
            picked = tech_picked
        elif context_chunks:
            tech_candidates = [c for c in context_chunks if _has_technical_evidence(c.get('content', ''))]
            if tech_candidates:
                picked = tech_candidates[:2]

    if is_social_query(query):
        social_picked = [c for c in picked if _has_social_evidence(c.get('content', ''))]
        if social_picked:
            picked = social_picked
        elif context_chunks:
            social_candidates = [c for c in context_chunks if _has_social_evidence(c.get('content', ''))]
            if social_candidates:
                picked = social_candidates[:2]

    if not picked and context_chunks and 'information not found' not in answer.lower():
        picked = context_chunks[:1]

    return picked[:3]


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


def _sparse_search(workspace_id: str, query: str, expanded_query: str, top_k: int) -> list[dict]:
    def _run(ts_query: str) -> list[dict]:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id,c.document_id,d.name as document_name,c.page_number,c.content,c.context_snippet,c.exact_quote,
                           ts_rank(c.search_vector, websearch_to_tsquery('english', %s))::float8 as sparse_score
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE c.workspace_id=%s AND c.search_vector @@ websearch_to_tsquery('english', %s)
                    ORDER BY sparse_score DESC
                    LIMIT %s
                    """,
                    (ts_query, workspace_id, ts_query, top_k),
                )
                return [dict(r) for r in cur.fetchall()]

    rows = _run(expanded_query)
    if rows:
        return rows

    if expanded_query != query:
        rows = _run(query)
        if rows:
            return rows

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


def _chat_history(workspace_id: str, limit: int = 6) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content
                FROM messages
                WHERE workspace_id=%s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (workspace_id, limit),
            )
            rows = [dict(r) for r in cur.fetchall()]
    return list(reversed(rows))


def _is_title_query(query: str) -> bool:
    q = query.lower()
    title_hints = ['case study', 'title', 'assigned to the student', 'assigned to student']
    return any(h in q for h in title_hints)


def _title_boost(query: str, chunk: dict) -> float:
    if not _is_title_query(query):
        return 0.0

    content = (chunk.get('content') or '').lower()
    page = int(chunk.get('page_number') or 0)
    boost = 0.0

    if page == 1:
        boost += 0.35
    if 'case study' in content:
        boost += 0.25
    if 'prepared by' in content:
        boost += 0.25
    if 'date:' in content:
        boost += 0.1

    return boost


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
    facet_queries = _extract_query_facets(query)

    dense: list[dict] = []
    if route in {'hybrid', 'vector'}:
        try:
            vectors = await ai.embed(facet_queries)
        except Exception as exc:
            raise RuntimeError(f"AI embedding failed ({type(exc).__name__}): {exc}") from exc

        per_facet_dense = max(5, settings.TOP_K_DENSE // max(1, len(vectors)))
        for vec in vectors:
            dense.extend(_dense_search(workspace_id, to_pgvector(vec, settings.EMBEDDING_DIMENSION), per_facet_dense))

    sparse: list[dict] = []
    if route in {'hybrid', 'keyword', 'metadata'}:
        per_facet_sparse = max(5, settings.TOP_K_SPARSE // max(1, len(facet_queries)))
        for facet_query in facet_queries:
            sparse.extend(
                _sparse_search(
                    workspace_id,
                    facet_query,
                    _expand_sparse_query(facet_query),
                    per_facet_sparse,
                )
            )

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
                'rerank_score': (
                    x.get('fused_score', 0.0) * 50.0  # <-- THE MAGIC FIX: Scales RRF to a 0.1 - 0.8 range
                    + overlap_score(query, x['content']) * 0.2
                    + _title_boost(query, x)
                    + _metric_boost(query, x)
                    + _temporal_boost(query, x)
                    + _technical_boost(query, x)
                    + _social_boost(query, x)
                ),
            }
            for x in pool.values()
        ],
        key=lambda z: z['rerank_score'],
        reverse=True,
    )[: settings.TOP_K_RERANK]

    context_chunks = _select_context_chunks(query, reranked)
    contexts = [
        {
            'citationId': f"C{i+1}",
            'documentName': c['document_name'],
            'pageNumber': c['page_number'],
            'content': c['content'],
        }
        for i, c in enumerate(context_chunks)
    ]

    history = _chat_history(workspace_id, limit=6)
    try:
        llm = await ai.generate_answer(query, contexts, history)
    except Exception as exc:
        raise RuntimeError(f"AI answer generation failed ({type(exc).__name__}): {exc}") from exc
    answer = llm.get('answer') or 'Information not found.'
    llm_citation_ids = [str(cid).upper() for cid in llm.get('citationIds') or []]

    selected_chunks = _select_citation_chunks(query, answer, context_chunks, llm_citation_ids)

    citations = []
    if 'information not found' not in answer.lower():
        for i, c in enumerate(selected_chunks):
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
        'latencyMs': int((perf_counter() - started) * 1000),
        'retrievedCount': len(pool),
        'rerankedCount': len(reranked),
        'contextCount': len(context_chunks),
        'facetCount': len(facet_queries),
        'isMetricQuery': is_metric_query(query),
        'isTemporalQuery': is_temporal_query(query),
        'isTechnicalQuery': is_technical_query(query),
        'isSocialQuery': is_social_query(query),
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
                    trace['latencyMs'],
                ),
            )
        conn.commit()

    sources = [
        {
            'chunkId': c['id'],
            'documentName': c['document_name'],
            'pageNumber': c['page_number'],
            'snippet': c['context_snippet'],
            'denseScore': c.get('dense_score', 0.0),
            'sparseScore': c.get('sparse_score', 0.0),
            'rerankScore': c.get('rerank_score', 0.0),
        }
        for c in context_chunks
    ]

    return {
        'answer': answer,
        'citations': citations,
        'routeStrategy': route,
        'retrieval': trace,
        'sources': sources,
        'message': {'id': msg_id, 'role': 'assistant', 'content': answer, 'citations': citations},
    }
