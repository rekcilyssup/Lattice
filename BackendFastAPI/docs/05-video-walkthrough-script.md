# 5-7 Minute Video Walkthrough Script

Use this script structure for your internship recording.

## 0:00-0:45 — Problem + Goal

- "This is a LangChain-powered RAG backend with FastAPI."
- "It answers document-specific questions with citations, instead of hallucinating generic web answers."
- "The frontend calls REST APIs; the backend handles ingestion, retrieval, and grounded generation."

## 0:45-1:45 — Stack Snapshot

- Backend: FastAPI (`app/main.py`)
- Orchestration: LangChain (`app/services/ai.py`)
- DB: Postgres + pgvector (`app/db/migrate.py`)
- Parsing: `pypdf`
- LLM/Embeddings: Ollama (`llama3.2:1b`, `nomic-embed-text`)

Call out key LangChain pieces:

- `RecursiveCharacterTextSplitter`
- `OllamaEmbeddings`
- `create_stuff_documents_chain`
- `ChatPromptTemplate`
- `JsonOutputParser`

## 1:45-3:15 — Ingestion Pipeline (Code)

Walk through `app/services/ingestion.py`:

1. load PDF pages
2. split text via LangChain splitter
3. embed chunks via LangChain embeddings
4. store chunks + vectors + metadata in Postgres
5. mark document `indexed`

Explain why:

- split preserves context windows
- vector + metadata enables better retrieval and citations

## 3:15-4:45 — Query Pipeline (Code)

Walk through `app/services/chat.py`:

1. store user message
2. route query (`hybrid/keyword/metadata`)
3. retrieve dense + sparse candidates from Postgres
4. fuse + rerank
5. call LangChain generation chain with retrieved context
6. store assistant message + audit log
7. return `answer`, `citations`, `sources`, `retrieval`

Show `app/services/ai.py` for prompt and JSON output contract.

## 4:45-6:15 — Live Demo

Show terminal + browser:

1. upload PDF
2. ask a question
3. show answer + citations in UI
4. show API response includes `sources` and `retrieval.latencyMs`
5. open DB table quickly (`chunks`, `messages`, `query_audit_logs`) if possible

## 6:15-7:00 — Engineering Tradeoffs + Next Steps

- Current: SQL hybrid retrieval + LangChain generation chain
- Next:
  - move to managed vector DB if needed
  - add conversation memory per workspace
  - add eval metrics + retrieval quality dashboards
  - add streaming responses

