# 5-7 Min Screen Recording Walkthrough (Code + Demo)

Use this as your speaking guide while sharing screen. Keep it conversational, not word-for-word.

## Quick Setup (Before Recording)

1. Start Dockerized DB (`Postgres + pgvector`):
```bash
cd BackendFastAPI
docker compose up -d
```
2. Start backend:
```bash
cd BackendFastAPI
source ../.venv/bin/activate
uvicorn app.main:app --reload --port 8080
```
3. Start frontend:
```bash
cd Frontend
npm run dev
```
4. Optional clean reset (flush local DB data before a fresh demo):
```bash
cd BackendFastAPI
docker compose down -v
docker compose up -d
```
Say:
- "I run Postgres in Docker so setup is reproducible on any machine."
- "For a clean demo run, I can flush old state with `down -v`, which removes containers and local DB volume data."
- "On backend startup, migrations recreate schema automatically."
5. Keep these files ready in tabs:
- `BackendFastAPI/app/services/ingestion.py`
- `BackendFastAPI/app/services/chat.py`
- `BackendFastAPI/app/services/ai.py`
- `BackendFastAPI/app/utils/query.py`
- `BackendFastAPI/app/db/migrate.py`
- `Frontend/components/ChatArea.tsx`

## 0:00-0:40 Intro (What to Say)

"This project is Lattice, a full-stack RAG assistant. Users upload PDFs, ask questions, and get grounded answers with citations. The core goal is accuracy and traceability, not just fluent text."

Show:
- `Frontend` running app
- one workspace with uploaded document

## 0:40-1:20 Architecture Snapshot

Open:
- `BackendFastAPI/app/main.py`
- `BackendFastAPI/app/db/migrate.py`

Say:
- "Backend is FastAPI, frontend is Next.js."
- "Data is in PostgreSQL with `pgvector` for dense retrieval."
- "Schema includes chunks, messages, and query audit logs, so every answer is traceable."

## 1:20-2:20 Ingestion Pipeline (Accuracy Foundation)

Open:
- `BackendFastAPI/app/services/ingestion.py`

Say:
- "PDFs are loaded page-wise, then split with overlap (`chunk_size=1200`, `chunk_overlap=180`) so context is not lost across page boundaries."
- "Each chunk stores page number, snippet, exact quote, and metadata."
- "Embeddings are generated and written to `pgvector`, so retrieval can combine semantic and lexical matching."
- "We sanitize text before DB insert to avoid corrupted PDF characters causing failures."

## 2:20-4:30 Retrieval + Reranking (Main Accuracy Story)

Open:
- `BackendFastAPI/app/services/chat.py`
- `BackendFastAPI/app/utils/query.py`

Say:
- "We classify query intent: metric, temporal, technical, social, and multi-part."
- "For each query facet, we run hybrid retrieval: dense vector search plus sparse full-text search."
- "Then we fuse scores with reciprocal-rank style weighting and rerank with overlap + intent-specific boosts."
- "We remove low-information words using `_STOPWORDS` before overlap scoring, so common words like 'the', 'is', 'what' do not skew relevance."
- "This is where accuracy improves: numerical questions prefer chunks with numeric evidence, timeline questions prefer temporal evidence, and so on."
- "Context selection is dynamic. Multi-part questions get more context; focused questions get tighter context to reduce drift."
- "Citation selection has a second filter pass, so weak or irrelevant chunks are dropped before response."

Show in code:
- `_STOPWORDS` and `_query_terms()` in `BackendFastAPI/app/services/chat.py`

Say:
- "This list is a precision guardrail. It filters filler words from query-term matching."
- "Without stopword filtering, lexical overlap can over-reward irrelevant chunks that repeat common language."
- "With filtering, boost logic focuses on high-signal tokens like domain terms, metrics, years, and model names."

## 4:30-5:30 Grounded Generation + Citation Contract

Open:
- `BackendFastAPI/app/services/ai.py`

Say:
- "The model is forced to answer only from retrieved chunks labeled `C1`, `C2`, etc."
- "Prompt contract enforces strict JSON output: `answer` and `citationIds` only."
- "If information is not in context, the system returns `Information not found.` instead of hallucinating."
- "Citation IDs from model output are normalized and validated before final response."

## 5:30-6:40 Live Demo Flow

In UI, do this:
1. Upload a PDF to workspace.
2. Ask a metric query:  
   "What is the current and projected water demand in MLD?"
3. Ask a technical query:  
   "Which architecture/models are used in section 7.3?"
4. Click a citation card and show source snippet/page in right panel.
5. Ask one unsupported question to show safe fallback:
   "What was the mayor's speech in 2011?"  
   Mention: "If evidence is missing, system says information not found."

## 6:40-7:00 Close

Say:
- "The strongest part of this project is retrieval quality plus evidence discipline."
- "Every answer is backed by citations and can be audited with retrieval traces."
- "This makes it more reliable for document-grounded enterprise use cases."

## Short Impressive Points (Cheat Sheet)

- Hybrid retrieval (`pgvector` dense + Postgres FTS sparse).
- Query-aware reranking boosts by intent type.
- Dynamic context sizing for multi-part vs focused questions.
- Strict grounded JSON answer contract with citation IDs.
- Provenance-first UI (`CitationCard`) and audit logging.

## Recording Tips

- Keep pace: about 45-60 seconds per major section.
- Zoom into the specific function blocks you are describing; avoid scrolling too much.
- If asked about tradeoffs, say: "We traded raw generation freedom for strict grounding and traceability."
- Avoid showing any secret keys/tokens on screen.

## Extra Interview Talking Points (If Asked)

- "Why Docker?"
  "Consistent local infra: everyone gets the same Postgres + pgvector behavior without manual DB installs."
- "What does flush/reset mean?"
  "For local demos, `docker compose down -v` wipes DB volumes so I can re-run ingestion and show deterministic behavior from a clean state."
- "Why `_STOPWORDS`?"
  "It removes noisy tokens from term-overlap features, improving ranking precision and reducing false positives."
