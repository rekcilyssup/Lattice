# Import statements for future compatibility, async operations, JSON handling, regex, and LangChain components
from __future__ import annotations  # Enables forward reference annotations in Python
import asyncio  # Provides asynchronous programming capabilities
import json  # Handles JSON encoding/decoding operations
import re  # Regular expression module for pattern matching
from langchain.chains.combine_documents import create_stuff_documents_chain  # Creates document combining chain
from langchain_core.documents import Document  # Represents a document with content and metadata
from langchain_core.prompts import ChatPromptTemplate  # Template for creating chat prompts
from langchain_ollama import ChatOllama, OllamaEmbeddings  # Ollama-specific LLM and embedding classes
from langchain_text_splitters import RecursiveCharacterTextSplitter  # Splits text recursively into chunks

from app.core.config import settings  # Imports application configuration settings
from app.utils.query import is_metric_query, is_temporal_query, is_technical_query, is_social_query, is_multi_part_query  # Query type detection functions
from app.utils.vector import normalize  # Vector normalization utility function

# Import for Groq integration
from langchain_groq import ChatGroq  # Groq-specific chat LLM class

class AIService:  # Main AI service class for handling embeddings and responses
    def __init__(self) -> None:  # Constructor method initializing the AI service
        self._splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=180)  # Initializes text splitter with specific chunk size and overlap

    def split_text(self, text: str) -> list[str]:  # Method to split input text into manageable chunks
        normalized = ' '.join(text.split())  # Normalizes whitespace by splitting and rejoining text
        if not normalized:  # Checks if normalized text is empty
            return []  # Returns empty list if no text exists
        return self._splitter.split_text(normalized)  # Splits and returns the normalized text

    async def embed(self, texts: list[str]) -> list[list[float]]:  # Asynchronous method to create embeddings for text list
        if not texts:  # Checks if input text list is empty
            return []  # Returns empty list if no texts provided

        provider = settings.EMBEDDING_PROVIDER.lower()  # Gets embedding provider from settings and converts to lowercase
        if provider == 'ollama':  # Checks if provider is set to Ollama
            return await self._embed_ollama(texts)  # Calls Ollama-specific embedding method

        raise ValueError(f"Unsupported EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}'. Configure a supported AI embedding provider.")  # Raises error for unsupported providers

    # In ai.py - Method to handle Ollama embedding operations
    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:  # Private method for Ollama embedding
        embedder = OllamaEmbeddings(  # Creates Ollama embedding instance
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,  # Uses configured Ollama base URL
        )

        vectors = await asyncio.to_thread(embedder.embed_documents, texts)  # Executes embedding in separate thread asynchronously
        return [normalize([float(x) for x in v]) for v in vectors]  # Normalizes each vector and returns list of normalized float vectors

    async def generate_answer(self, query: str, contexts: list[dict], chat_history: list[dict] | None = None) -> dict:  # Generates response based on query and context
        if not contexts:  # Checks if no context documents provided
            return {'answer': 'Information not found.', 'citationIds': []}  # Returns default response when no context available

        provider = settings.LLM_PROVIDER.lower()  # Gets LLM provider from settings and converts to lowercase
        if provider == 'groq':  # Checks if provider is set to Groq
            return await self._answer_groq_chain(query, contexts, chat_history or [])  # Calls Groq-specific answer method

        if provider == 'ollama':  # Checks if provider is set to Ollama
            return await self._answer_ollama_chain(query, contexts, chat_history or [])  # Calls Ollama-specific answer method

        raise ValueError(f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. Configure a supported AI model provider.")  # Raises error for unsupported LLM providers

    def _build_qa_prompt(self, query: str):  # Builds the system/human prompt, adapting instructions to the query type
        metric_instructions = (  # Defines instructions for metric-related queries
            'The user is asking for quantitative details. '
            'Extract exact values, units, and counts exactly as written in context '
            '(for example: 726 MLD, 179 waterbodies, 16 ponds). '
            'If multiple metrics are requested, include each explicitly in the answer. '
            'Do not approximate, normalize, or invent values. '
        ) if is_metric_query(query) else ''  # Applies metric instructions only if query is metric-focused
        temporal_instructions = (  # Defines instructions for timeline-related queries
            'The user is asking for timeline/phase details. '
            'Include exact phase/stage/year labels and associated values exactly as written '
            '(for example: Years 1-3, Years 4-5, Year 6+, 5-minute latency). '
            'Preserve chronological order in the answer. '
        ) if is_temporal_query(query) else ''  # Applies temporal instructions only if query is timeline-focused
        technical_instructions = (  # Defines instructions for technical queries
            'The user is asking for technical architecture details. '
            'Explicitly name models, algorithms, and framework terms exactly as written '
            '(for example: U-Net CNN, LSTM, ResNet-50, contrastive learning, XGBoost). '
            'If the question asks "which" or "what architecture", answer with direct model names first. '
        ) if is_technical_query(query) else ''  # Applies technical instructions only if query is technical-focused
        social_instructions = (  # Defines instructions for social/operational queries
            'The user is asking about social or operational adoption. '
            'Explicitly state actors/groups and their roles (for example: youth, elders, community members, departments). '
            'Do not replace role details with generic summaries. '
        ) if is_social_query(query) else ''  # Applies social instructions only if query is social-focused
        is_multi_part = is_multi_part_query(query)  # Checks if query has multiple parts

        length_instruction = (  # Defines instructions for multi-part queries
            'The question has multiple sub-parts or requires detailed explanation. '
            'Write a COMPLETE answer addressing EVERY sub-part — do NOT limit to 2 sentences. '
            'Use numbered points or separate sentences per sub-part. '
            'If one sub-part is unsupported by context, include "Information not found." only for that sub-part. '
        ) if is_multi_part else (  # Applies detailed instructions for multi-part queries
            'For direct entity/title questions, return a short exact phrase. '
            'For all other questions, keep the answer concise (2-4 sentences max). '
        )  # Otherwise applies concise answer instructions

        return ChatPromptTemplate.from_messages(  # Creates chat prompt template with system and human messages
            [
                (
                    'system',  # System message containing instructions for the AI
                    (
                        'You are a strict retrieval QA assistant for document-grounded answers. '
                        'Only use supplied context chunks and never use outside knowledge. '
                        'Each chunk is labeled like [C1], [C2], etc. '
                        f'{length_instruction}'  # Inserts length-specific instructions
                        f'{metric_instructions}'  # Inserts metric-specific instructions
                        f'{temporal_instructions}'  # Inserts temporal-specific instructions
                        f'{technical_instructions}'  # Inserts technical-specific instructions
                        f'{social_instructions}'  # Inserts social-specific instructions
                        'You MUST return ONLY valid JSON with EXACTLY these two keys: "answer" and "citationIds". '  # Enforces JSON format requirement
                        'Do NOT add any other keys to the JSON object. '
                        'Example Output: {{"answer": "The project uses U-Net CNN.", "citationIds": ["C1"]}}'  # Shows expected JSON format
                    ),
                ),
                ('human', 'Chat History:\n{history}\n\nQuestion: {query}\n\nContext:\n{context}'),  # Human message template with placeholders for history, query, and context
            ]
        )

    @staticmethod
    def _format_context_docs(contexts: list[dict]) -> list[Document]:  # Converts context dicts into LangChain Documents with citation labels
        return [
            Document(
                page_content=f"[{c['citationId']}] {c['documentName']} page {c['pageNumber']}\n{c['content']}",
                metadata={
                    'citationId': c['citationId'],
                    'documentName': c['documentName'],
                    'pageNumber': c['pageNumber'],
                },
            )
            for c in contexts
        ]

    async def _run_qa_chain(self, llm, query: str, contexts: list[dict], chat_history: list[dict], provider_label: str) -> dict:  # Runs the QA chain with any provider and normalizes the payload
        prompt = self._build_qa_prompt(query)
        docs = self._format_context_docs(contexts)
        history_text = '\n'.join([f"{m['role']}: {m['content']}" for m in chat_history[-6:]]) or 'None'

        qa_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)

        try:
            raw = await qa_chain.ainvoke({'input': query, 'query': query, 'context': docs, 'history': history_text})
        except Exception as exc:
            raise RuntimeError(
                f"AI generation failed via {provider_label} ({type(exc).__name__}): {exc}. "
                f"Verify the {provider_label} configuration and that the configured model is available."
            ) from exc

        return self._coerce_qa_payload(raw, contexts)

    async def _answer_groq_chain(self, query: str, contexts: list[dict], chat_history: list[dict]) -> dict:  # Private method to create and execute Groq answer chain
        if not settings.GROQ_API_KEY:
            raise RuntimeError('GROQ_API_KEY is not configured. Set it in BackendFastAPI/.env (see .env.example).')

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            model_kwargs={"response_format": {"type": "json_object"}},  # Forces strict JSON output
        )

        return await self._run_qa_chain(llm, query, contexts, chat_history, 'Groq')

    async def _answer_ollama_chain(self, query: str, contexts: list[dict], chat_history: list[dict]) -> dict:  # Private method to create and execute Ollama answer chain
        llm = ChatOllama(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            format='json',
        )

        return await self._run_qa_chain(llm, query, contexts, chat_history, 'Ollama')

    def _coerce_qa_payload(self, raw: object, contexts: list[dict]) -> dict:  # Converts raw response to standardized QA dictionary
        text = str(raw or '').strip()  # Converts raw response to string and strips whitespace
        if not text:  # Checks if text is empty
            return {'answer': 'Information not found.', 'citationIds': []}  # Returns text

        payload = self._extract_json_payload(text)  # Extracts JSON payload from text
        if payload is not None:  # Checks if JSON payload was successfully extracted
            answer = str(payload.get('answer') or '').strip() or 'Information not found.'  # Gets answer from payload or default
            citation_ids = payload.get('citationIds') or []  # Gets citation IDs from payload or empty list
            citation_ids = self._normalize_citation_ids(citation_ids)  # Normalizes citation IDs
            if answer.lower() == 'information not found.':  # Checks if answer indicates no information found
                citation_ids = []  # Clears citation IDs if no information found
            return {'answer': answer, 'citationIds': citation_ids}  # Returns processed answer and citation IDs

        # If JSON is malformed, still return the model text (AI-generated),
        # and let the chat service attach top retrieved citations.
        return {'answer': text, 'citationIds': []}  # Returns raw text with empty citation IDs for malformed JSON

    def _extract_json_payload(self, text: str) -> dict | None:  # Extracts JSON object from text response
        try:
            obj = json.loads(text)  # Attempts to parse entire text as JSON
            if isinstance(obj, dict):  # Checks if parsed object is a dictionary
                return obj  # Returns dictionary if valid
        except Exception:  # Catches JSON parsing errors
            pass  # Continues to regex extraction if full text isn't valid JSON

        match = re.search(r'\{.*\}', text, flags=re.DOTALL)  # Searches for first JSON-like structure in text
        if not match:  # Checks if no JSON pattern was found
            return None  # Returns None if no pattern found

        try:
            obj = json.loads(match.group(0))  # Parses the matched JSON substring
            if isinstance(obj, dict):  # Checks if parsed object is a dictionary
                return obj  # Returns dictionary if valid
        except Exception:  # Catches JSON parsing errors for matched substring
            return None  # Returns None if parsing fails

        return None  # Returns None if no valid JSON found

    def _normalize_citation_ids(self, citation_ids: list) -> list[str]:  # Normalizes citation ID format
        normalized: list[str] = []  # Initializes list for normalized citation IDs
        for item in citation_ids:  # Iterates through each citation ID
            if not isinstance(item, (str, int)):  # Skips items that aren't strings or integers
                continue  # Continues to next item
            cid = str(item).strip().upper()  # Converts to string, strips whitespace, and converts to uppercase
            if not cid:  # Skips if converted ID is empty
                continue  # Continues to next item
            if cid.isdigit():  # Checks if ID contains only digits
                cid = f"C{cid}"  # Prepends 'C' to digit-only IDs
            if cid.startswith('C') and cid[1:].isdigit() and cid not in normalized:  # Validates format and uniqueness
                normalized.append(cid)  # Adds valid, unique citation ID to list
        return normalized  # Returns list of normalized citation IDs