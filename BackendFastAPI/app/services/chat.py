import json  # JSON encoding/decoding
import re  # Regular expressions
import uuid  # UUID generation
from time import perf_counter  # Performance timing
from app.core.config import settings  # App configuration
from app.db.connection import get_conn  # Database connection
from app.services.ai import AIService  # AI service class
from app.utils.query import is_metric_query, is_temporal_query, is_technical_query, is_social_query, is_multi_part_query  # Query type detection
from app.utils.text import overlap_score  # Text overlap scoring
from app.utils.vector import to_pgvector  # Vector conversion for PostgreSQL


_STOPWORDS = {  # Common words to exclude from search
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


def _query_terms(query: str) -> set[str]:  # Extracts meaningful terms from query
    return {t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) >= 3 and t not in _STOPWORDS}  # Finds alphanumeric terms >3 chars, excludes stopwords


def _extract_query_facets(query: str) -> list[str]:  # Breaks complex query into sub-facets
    cleaned = re.sub(r'\s+', ' ', query).strip()  # Normalizes whitespace
    if not cleaned:  # Returns empty if no content
        return []

    parts = re.split(r'\?+|;|,\s+|\s+\band\b\s+|\s+\bbut\b\s+|\s+\bplus\b\s+', cleaned, flags=re.IGNORECASE)  # Splits query on separators
    facets: list[str] = [cleaned]  # Starts with full query
    for part in parts:  # Adds longer parts as additional facets
        p = part.strip()
        if len(p) >= 10:
            facets.append(p)

    deduped: list[str] = []  # Removes duplicates while preserving order
    seen: set[str] = set()
    for facet in facets:
        key = facet.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(facet)

    return deduped[:4]  # Limits to 4 facets


def _has_numeric_evidence(text: str) -> bool:  # Checks if text contains numeric information
    t = text.lower()
    has_number = bool(re.search(r'\b\d[\d,\.]*\b', t))  # Looks for numbers with commas/dots
    has_unit = bool(re.search(r'\b(mld|mgd|km|crore|lakh|percent|percentage|rs|₹|pond|ponds|waterbody|waterbodies)\b', t))  # Looks for units
    return has_number or has_unit  # Returns true if either found


def _has_temporal_evidence(text: str) -> bool:  # Checks if text contains time-related info
    t = text.lower()
    return bool(  # Looks for years, time words, phases
        re.search(
            r'\b(20\d{2}|19\d{2}|year|years|month|months|phase|phases|stage|stages|timeline|latency|minute|minutes|second|seconds|year\s*\d|years\s*\d)\b',
            t,
        )
    )


def _has_technical_evidence(text: str) -> bool:  # Checks if text contains technical terms
    t = text.lower()
    return bool(  # Looks for technical architecture terms
        re.search(
            r'\b(technical architecture|architecture|model|algorithm|framework|pipeline|u-?net|cnn|lstm|resnet|contrastive|xgboost)\b',
            t,
        )
    )


def _has_social_evidence(text: str) -> bool:  # Checks if text contains social terms
    t = text.lower()
    return bool(  # Looks for social/community terms
        re.search(
            r'\b(family model|community|citizen|stakeholder|in|digital literacy|elder|youth|children|training|cooperative|governance)\b',
            t,
        )
    )


def _metric_boost(query: str, chunk: dict) -> float:  # Boosts score for metric queries
    if not is_metric_query(query):  # Only applies boost if query is metric-focused
        return 0.0

    content = (chunk.get('content') or '').lower()  # Gets chunk content
    query_terms = _query_terms(query)  # Gets query terms
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))  # Gets content terms
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))  # Calculates term overlap

    number_hits = len(re.findall(r'\b\d[\d,\.]*\b', content))  # Counts numbers
    unit_hits = len(re.findall(r'\b(mld|mgd|km|crore|lakh|percent|percentage|rs|₹|pond|ponds|waterbody|waterbodies)\b', content))  # Counts units

    return min(0.35, overlap * 0.22 + number_hits * 0.02 + unit_hits * 0.04)  # Returns calculated boost score


def _temporal_boost(query: str, chunk: dict) -> float:  # Boosts score for temporal queries
    if not is_temporal_query(query):  # Only applies boost if query is temporal-focused
        return 0.0

    content = (chunk.get('content') or '').lower()  # Gets chunk content
    query_terms = _query_terms(query)  # Gets query terms
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))  # Gets content terms
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))  # Calculates term overlap
    temporal_hits = len(  # Counts temporal terms
        re.findall(r'\b(20\d{2}|19\d{2}|year|years|month|months|phase|phases|stage|stages|timeline|latency|minute|minutes|second|seconds)\b', content)
    )
    return min(0.3, overlap * 0.18 + temporal_hits * 0.02)  # Returns calculated boost score


def _technical_boost(query: str, chunk: dict) -> float:  # Boosts score for technical queries
    if not is_technical_query(query):  # Only applies boost if query is technical-focused
        return 0.0

    content = (chunk.get('content') or '').lower()  # Gets chunk content
    query_terms = _query_terms(query)  # Gets query terms
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))  # Gets content terms
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))  # Calculates term overlap
    model_hits = len(re.findall(r'\b(u-?net|cnn|lstm|resnet|contrastive|xgboost)\b', content))  # Counts model terms
    arch_hits = len(re.findall(r'\b(technical architecture|architecture|framework|algorithm|pipeline)\b', content))  # Counts architecture terms
    return min(0.35, overlap * 0.24 + model_hits * 0.05 + arch_hits * 0.03)  # Returns calculated boost score


def _social_boost(query: str, chunk: dict) -> float:  # Boosts score for social queries
    if not is_social_query(query):  # Only applies boost if query is social-focused
        return 0.0

    content = (chunk.get('content') or '').lower()  # Gets chunk content
    query_terms = _query_terms(query)  # Gets query terms
    content_terms = set(re.findall(r"[a-zA-Z0-9]+", content))  # Gets content terms
    overlap = len(query_terms.intersection(content_terms)) / max(1, len(query_terms))  # Calculates term overlap
    social_hits = len(  # Counts social terms
        re.findall(
            r'\b(family model|community|citizen|stakeholder|inclusion|accessibility|digital literacy|elder|youth|children|training|cooperative|governance)\b',
            content,
        )
    )
    return min(0.28, overlap * 0.2 + social_hits * 0.03)  # Returns calculated boost score


def _expand_sparse_query(query: str) -> str:  # Expands query with additional terms for sparse search
    expanded = query  # Start with original query

    # Add section numbers as bare terms for FTS matching
    section_match = re.findall(r'section\s*(\d+(?:\.\d+)*)', query.lower())  # Finds section numbers
    for sec in section_match:  # Adds each section number as OR condition
        expanded += f' OR "{sec}"'

    if is_technical_query(query):  # Adds technical terms if needed
        expanded += ' OR "technical architecture" OR architecture OR model OR framework OR algorithm OR pipeline OR unet OR cnn OR lstm OR resnet OR contrastive OR xgboost'

    if is_social_query(query):  # Adds social terms if needed
        expanded += ' OR "family model" OR community OR stakeholder OR inclusion OR accessibility OR "digital literacy" OR elder OR youth OR children OR training OR governance'

    if is_metric_query(query):  # Adds metric terms if needed
        expanded += ' OR demand OR projected OR current OR status OR value OR metric OR mld OR mgd OR crore OR lakh OR count'

    if is_temporal_query(query):  # Adds temporal terms if needed
        expanded += ' OR year OR years OR month OR months OR phase OR stages OR timeline OR latency OR transition OR roadmap'

    return expanded  # Returns expanded query


def _select_context_chunks(query: str, reranked: list[dict]) -> list[dict]:  # Selects best chunks for context
    if not reranked:  # Returns empty if no results
        return []

    top_score = float(reranked[0].get('rerank_score', 0.0) or 0.0)  # Gets highest score
    if is_multi_part_query(query):  # Multi-part needs more context
        min_score = max(0.12, top_score * 0.28)
        limit = 15
    elif is_metric_query(query):  # Metric queries need focused context
        min_score = max(0.16, top_score * 0.35)
        limit = 6
    elif is_temporal_query(query):  # Temporal queries need focused context
        min_score = max(0.15, top_score * 0.33)
        limit = 6
    elif is_technical_query(query):  # Technical queries need focused context
        min_score = max(0.15, top_score * 0.32)
        limit = 6
    elif is_social_query(query):  # Social queries need focused context
        min_score = max(0.16, top_score * 0.34)
        limit = 6
    else:  # General queries
        min_score = max(0.20, top_score * 0.45)
        limit = 10

    selected = [c for c in reranked if float(c.get('rerank_score', 0.0) or 0.0) >= min_score]  # Filters by minimum score

    if not selected:  # Always includes top result if nothing meets threshold
        selected = [reranked[0]]

    # Keep context tight to reduce drift and irrelevant citations.
    return selected[:limit]  # Limits number of returned chunks


def _select_citation_chunks(query: str, answer: str, context_chunks: list[dict], llm_citation_ids: list[str]) -> list[dict]:  # Selects final citation chunks
    by_id = {f"C{i+1}": c for i, c in enumerate(context_chunks)}  # Maps citation IDs to chunks
    picked: list[dict] = []  # Initialize picked list

    for cid in llm_citation_ids:  # Picks chunks requested by LLM
        chunk = by_id.get(cid.upper())
        if chunk:
            picked.append(chunk)

    if not picked:  # Uses first 2 if LLM didn't specify citations
        picked = context_chunks[:2]

    top_score = float(context_chunks[0].get('rerank_score', 0.0) or 0.0) if context_chunks else 0.0  # Gets top score
    min_score = max(0.18, top_score * 0.35)  # Sets minimum score
    picked = [c for c in picked if float(c.get('rerank_score', 0.0) or 0.0) >= min_score]  # Filters by score

    if is_metric_query(query):  # For metric queries, prefer chunks with numbers
        metric_picked = [c for c in picked if _has_numeric_evidence(c.get('content', ''))]
        if metric_picked:
            picked = metric_picked
        elif context_chunks:
            metric_candidates = [c for c in context_chunks if _has_numeric_evidence(c.get('content', ''))]
            if metric_candidates:
                picked = metric_candidates[:2]

    if is_temporal_query(query):  # For temporal queries, prefer chunks with time info
        temporal_picked = [c for c in picked if _has_temporal_evidence(c.get('content', ''))]
        if temporal_picked:
            picked = temporal_picked
        elif context_chunks:
            temporal_candidates = [c for c in context_chunks if _has_temporal_evidence(c.get('content', ''))]
            if temporal_candidates:
                picked = temporal_candidates[:2]

    if is_technical_query(query):  # For technical queries, prefer chunks with technical terms
        tech_picked = [c for c in picked if _has_technical_evidence(c.get('content', ''))]
        if tech_picked:
            picked = tech_picked
        elif context_chunks:
            tech_candidates = [c for c in context_chunks if _has_technical_evidence(c.get('content', ''))]
            if tech_candidates:
                picked = tech_candidates[:2]

    if is_social_query(query):  # For social queries, prefer chunks with social terms
        social_picked = [c for c in picked if _has_social_evidence(c.get('content', ''))]
        if social_picked:
            picked = social_picked
        elif context_chunks:
            social_candidates = [c for c in context_chunks if _has_social_evidence(c.get('content', ''))]
            if social_candidates:
                picked = social_candidates[:2]

    if not picked and context_chunks and 'information not found' not in answer.lower():  # Falls back to top chunk if needed
        picked = context_chunks[:1]

    return picked[:3]  # Limits to 3 citation chunks


def _route(query: str) -> str:  # Determines search strategy based on query
    q = query.lower()  # Convert to lowercase
    metadata_hints = ['author', 'uploaded', 'upload date', 'document type', 'access level', 'which document']  # Metadata query indicators
    if any(h in q for h in metadata_hints):  # Check for metadata keywords
        return 'metadata'
    if '"' in query:  # Check for quoted terms
        return 'keyword'
    return 'hybrid'  # Default to hybrid search


def _dense_search(workspace_id: str, vector: str, top_k: int) -> list[dict]:  # Performs vector similarity search
    # pgvector's <=> returns DISTANCE, not similarity: 0.0 = same direction,
    # 1.0 = orthogonal. Hence "1 - distance" in the SELECT, so higher = better.
    with get_conn() as conn:  # Database connection context
        with conn.cursor() as cur:  # Cursor context
            cur.execute(  # Execute vector similarity search
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
            return [dict(r) for r in cur.fetchall()]  # Return results as list of dicts


def _sparse_search(workspace_id: str, query: str, expanded_query: str, top_k: int) -> list[dict]:  # Performs keyword search
    def _run(ts_query: str) -> list[dict]:  # Helper function to run search
        with get_conn() as conn:  # Database connection context
            with conn.cursor() as cur:  # Cursor context
                cur.execute(  # Execute full-text search
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
                return [dict(r) for r in cur.fetchall()]  # Return results as list of dicts

    rows = _run(expanded_query)  # stage 1: intent-expanded OR-terms
    if rows:
        return rows

    if expanded_query != query:  # stage 2: drop the OR-terms and retry
        rows = _run(query)
        if rows:
            return rows

    with get_conn() as conn:  # stage 3: plainto_tsquery ignores boolean syntax
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
            return [dict(r) for r in cur.fetchall()]  # Return fallback results


def _chat_history(workspace_id: str, limit: int = 6) -> list[dict]:  # Retrieves conversation history
    with get_conn() as conn:  # Database connection context
        with conn.cursor() as cur:  # Cursor context
            cur.execute(  # Get recent messages
                """
                SELECT role, content
                FROM messages
                WHERE workspace_id=%s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (workspace_id, limit),
            )
            rows = [dict(r) for r in cur.fetchall()]  # Fetch all results
    return list(reversed(rows))  # the LLM needs oldest -> newest


def _is_title_query(query: str) -> bool:  # Checks if query is looking for document titles
    q = query.lower()  # Convert to lowercase
    title_hints = ['case study', 'title', 'assigned to the student', 'assigned to student']  # Title query indicators
    return any(h in q for h in title_hints)  # Check for title keywords


def _title_boost(query: str, chunk: dict) -> float:  # Boosts score for title queries
    if not _is_title_query(query):  # Only is title-focused
        return 0.0

    content = (chunk.get('content') or '').lower()  # Gets chunk content
    page = int(chunk.get('page_number') or 0)  # Gets page number
    boost = 0.0  # Initialize boost

    if page == 1:  # Boost first page
        boost += 0.35
    if 'case study' in content:  # Boost case study mentions
        boost += 0.25
    if 'prepared by' in content:  # Boost author mentions
        boost += 0.25
    if 'date:' in content:  # Boost date mentions
        boost += 0.1

    return boost  # Return calculated boost


async def ask_question(workspace_id: str, query: str) -> dict:  # Main question answering function
    started = perf_counter()  # Start timing
    ai = AIService()  # Initialize AI service

    with get_conn() as conn:  # Log user message
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages(id, workspace_id, role, content, citations) VALUES (%s,%s,'user',%s,%s::jsonb)",
                (str(uuid.uuid4()), workspace_id, query, '[]'),
            )
        conn.commit()

    route = _route(query)  # Determine search strategy
    facet_queries = _extract_query_facets(query)  # Split query into facets

    dense: list[dict] = []  # Initialize dense results
    if route in {'hybrid', 'vector'}:  # Perform vector search if needed
        try:
            vectors = await ai.embed(facet_queries)  # Generate embeddings
        except Exception as exc:
            raise RuntimeError(f"AI embedding failed ({type(exc).__name__}): {exc}") from exc

        per_facet_dense = max(5, settings.TOP_K_DENSE // max(1, len(vectors)))  # Calculate chunks per facet
        for vec in vectors:  # Search each facet
            dense.extend(_dense_search(workspace_id, to_pgvector(vec, settings.EMBEDDING_DIMENSION), per_facet_dense))

    sparse: list[dict] = []  # Initialize sparse results
    if route in {'hybrid', 'keyword', 'metadata'}:  # Perform keyword search if needed
        per_facet_sparse = max(5, settings.TOP_K_SPARSE // max(1, len(facet_queries)))  # Calculate chunks per facet
        for facet_query in facet_queries:  # Search each facet
            sparse.extend(
                _sparse_search(
                    workspace_id,
                    facet_query,
                    _expand_sparse_query(facet_query),
                    per_facet_sparse,
                )
            )

    pool = {}  # Combine results using Reciprocal Rank Fusion
    for i, r in enumerate(dense):  # Process dense results
        item = pool.get(r['id'], {**r, 'dense_score': 0.0, 'sparse_score': 0.0})  # Get or create item
        item['dense_score'] = max(item['dense_score'], r.get('dense_score', 0.0) or 0.0)  # Update dense score
        item['fused_score'] = item.get('fused_score', 0.0) + 0.55 * (1 / (60 + i + 1))  # Add RRF contribution
        pool[r['id']] = item  # Store updated item

    for i, r in enumerate(sparse):  # Process sparse results
        item = pool.get(r['id'], {**r, 'dense_score': 0.0, 'sparse_score': 0.0})  # Get or create item
        item['sparse_score'] = max(item['sparse_score'], r.get('sparse_score', 0.0) or 0.0)  # Update sparse score
        item['fused_score'] = item.get('fused_score', 0.0) + 0.45 * (1 / (60 + i + 1))  # Add RRF contribution
        pool[r['id']] = item  # Store updated item

    reranked = sorted(  # Final reranking with multiple scoring factors
        [
            {
                **x,
                'rerank_score': (
                    x.get('fused_score', 0.0) * 50.0  # Scale RRF to 0.1-0.8 range
                    + overlap_score(query, x['content']) * 0.2  # Add content overlap score
                    + _title_boost(query, x)  # Add title boost
                    + _metric_boost(query, x)  # Add metric boost
                    + _temporal_boost(query, x)  # Add temporal boost
                    + _technical_boost(query, x)  # Add technical boost
                    + _social_boost(query, x)  # Add social boost
                ),
            }
            for x in pool.values()  # Apply to all pooled results
        ],
        key=lambda z: z['rerank_score'],  # Sort by rerank score
        reverse=True,
    )[: settings.TOP_K_RERANK]  # Limit to top K

    context_chunks = _select_context_chunks(query, reranked)  # Select context chunks
    contexts = [  # Format contexts for AI
        {
            'citationId': f"C{i+1}",
            'documentName': c['document_name'],
            'pageNumber': c['page_number'],
            'content': c['content'],
        }
        for i, c in enumerate(context_chunks)  # Create citation IDs C1, C2, etc.
    ]

    history = _chat_history(workspace_id, limit=6)  # Get chat history
    try:
        llm = await ai.generate_answer(query, contexts, history)  # Generate AI response
    except Exception as exc:
        raise RuntimeError(f"AI answer generation failed ({type(exc).__name__}): {exc}") from exc
    answer = llm.get('answer') or 'Information not found.'  # Get answer or default
    llm_citation_ids = [str(cid).upper() for cid in llm.get('citationIds') or []]  # Normalize citation IDs

    selected_chunks = _select_citation_chunks(query, answer, context_chunks, llm_citation_ids)  # Select citation chunks

    citations = []  # Build citations list
    if 'information not found' not in answer.lower():  # Only if answer found
        for i, c in enumerate(selected_chunks):  # Create citation entries
            citations.append(
                {
                    'citation_id': str(i + 1),
                    'document_name': c['document_name'],
                    'page_number': c['page_number'],
                    'exact_quote': c['exact_quote'],
                    'context_snippet': c['context_snippet'],
                }
            )

    msg_id = str(uuid.uuid4())  # Generate message ID
    trace = {  # Create retrieval trace for logging
        'routeStrategy': route,
        'latencyMs': int((perf_counter() - started) * 1000),  # Calculate latency
        'retrievedCount': len(pool),  # Count retrieved chunks
        'rerankedCount': len(reranked),  # Count reranked chunks
        'contextCount': len(context_chunks),  # Count context chunks
        'facetCount': len(facet_queries),  # Count query facets
        'isMetricQuery': is_metric_query(query),  # Track metric queries
        'isTemporalQuery': is_temporal_query(query),  # Track temporal queries
        'isTechnicalQuery': is_technical_query(query),  # Track technical queries
        'isSocialQuery': is_social_query(query),  # Track social queries
    }

    with get_conn() as conn:  # Save results to database
        with conn.cursor() as cur:
            cur.execute(  # Insert assistant message
                "INSERT INTO messages(id, workspace_id, role, content, citations, retrieval_trace) VALUES (%s,%s,'assistant',%s,%s::jsonb,%s::jsonb)",
                (msg_id, workspace_id, answer, json.dumps(citations), json.dumps(trace)),
            )
            cur.execute(  # Insert audit log
                "INSERT INTO query_audit_logs(id,workspace_id,user_query,route_strategy,retrieved_chunk_ids,response_message_id,latency_ms) VALUES (%s,%s,%s,%s,%s::uuid[],%s,%s)",
                (
                    str(uuid.uuid4()),
                    workspace_id,
                    query,
                    route,
                    [c['id'] for c in reranked],  # Chunk IDs for audit
                    msg_id,
                    trace['latencyMs'],  # Latency for audit
                ),
            )
        conn.commit()

    sources = [  # Prepare sources for response
        {
            'chunkId': c['id'],  # Chunk ID
            'documentName': c['document_name'],  # Document name
            'pageNumber': c['page_number'],  # Page number
            'snippet': c['context_snippet'],  # Context snippet
            'denseScore': c.get('dense_score', 0.0),  # Dense score
            'sparseScore': c.get('sparse_score', 0.0),  # Sparse score
            'rerankScore': c.get('rerank_score', 0.0),  # Rerank score
        }
        for c in context_chunks  # For all context chunks
    ]

    return {  # Return complete response
        'answer': answer,
        'citations': citations,
        'routeStrategy': route,
        'retrieval': trace,
        'sources': sources,
        'message': {'id': msg_id, 'role': 'assistant', 'content': answer, 'citations': citations},
    }