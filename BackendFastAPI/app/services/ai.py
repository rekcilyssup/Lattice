from __future__ import annotations

import asyncio
import json
import re
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.utils.query import is_metric_query, is_temporal_query, is_technical_query, is_social_query, is_multi_part_query
from app.utils.vector import normalize

#for groq
from langchain_groq import ChatGroq

class AIService:
    def __init__(self) -> None:
        self._splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=180)

    def split_text(self, text: str) -> list[str]:
        normalized = ' '.join(text.split())
        if not normalized:
            return []
        return self._splitter.split_text(normalized)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        provider = settings.EMBEDDING_PROVIDER.lower()
        if provider == 'ollama':
            return await self._embed_ollama(texts)

        raise ValueError(f"Unsupported EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}'. Configure a supported AI embedding provider.")

    # In ai.py
    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        embedder = OllamaEmbeddings(
            model="nomic-embed-text", # This MUST be nomic-embed-text for 768 dims
            base_url=settings.OLLAMA_BASE_URL,
        )

        vectors = await asyncio.to_thread(embedder.embed_documents, texts)
        return [normalize([float(x) for x in v]) for v in vectors]

    async def generate_answer(self, query: str, contexts: list[dict], chat_history: list[dict] | None = None) -> dict:
        if not contexts:
            return {'answer': 'Information not found.', 'citationIds': []}

        provider = settings.LLM_PROVIDER.lower()
        if provider == 'ollama':
            return await self._answer_ollama_chain(query, contexts, chat_history or [])

        raise ValueError(f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. Configure a supported AI model provider.")

    async def _answer_ollama_chain(self, query: str, contexts: list[dict], chat_history: list[dict]) -> dict:
        metric_instructions = (
            'The user is asking for quantitative details. '
            'Extract exact values, units, and counts exactly as written in context '
            '(for example: 726 MLD, 179 waterbodies, 16 ponds). '
            'If multiple metrics are requested, include each explicitly in the answer. '
            'Do not approximate, normalize, or invent values. '
        ) if is_metric_query(query) else ''
        temporal_instructions = (
            'The user is asking for timeline/phase details. '
            'Include exact phase/stage/year labels and associated values exactly as written '
            '(for example: Years 1-3, Years 4-5, Year 6+, 5-minute latency). '
            'Preserve chronological order in the answer. '
        ) if is_temporal_query(query) else ''
        technical_instructions = (
            'The user is asking for technical architecture details. '
            'Explicitly name models, algorithms, and framework terms exactly as written '
            '(for example: U-Net CNN, LSTM, ResNet-50, contrastive learning, XGBoost). '
            'If the question asks "which" or "what architecture", answer with direct model names first. '
        ) if is_technical_query(query) else ''
        social_instructions = (
            'The user is asking about social or operational adoption. '
            'Explicitly state actors/groups and their roles (for example: youth, elders, community members, departments). '
            'Do not replace role details with generic summaries. '
        ) if is_social_query(query) else ''
        is_multi_part = is_multi_part_query(query)

        length_instruction = (
            'The question has multiple sub-parts or requires detailed explanation. '
            'Write a COMPLETE answer addressing EVERY sub-part — do NOT limit to 2 sentences. '
            'Use numbered points or separate sentences per sub-part. '
            'If one sub-part is unsupported by context, include "Information not found." only for that sub-part. '
        ) if is_multi_part else (
            'For direct entity/title questions, return a short exact phrase. '
            'For all other questions, keep the answer concise (2-4 sentences max). '
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    'system',
                    (
                        'You are a strict retrieval QA assistant for document-grounded answers. '
                        'Only use supplied context chunks and never use outside knowledge. '
                        'Each chunk is labeled like [C1], [C2], etc. '
                        f'{length_instruction}'
                        f'{metric_instructions}'
                        f'{temporal_instructions}'
                        f'{technical_instructions}'
                        f'{social_instructions}'
                        'You MUST return ONLY valid JSON with EXACTLY these two keys: "answer" and "citationIds". '
                        'Do NOT add any other keys to the JSON object. '
                        'Example Output: {{"answer": "The project uses U-Net CNN.", "citationIds": ["C1"]}}'
                    ),
                ),
                ('human', 'Chat History:\n{history}\n\nQuestion: {query}\n\nContext:\n{context}'),
            ]
        )

        docs = [
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
        history_text = '\n'.join([f"{m['role']}: {m['content']}" for m in chat_history[-6:]]) or 'None'

        """
        llm = ChatOllama(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            format='json',
        )
        """
        # The Free Groq Drop-In:
        llm = ChatGroq(
            api_key="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", 
            model_name="llama-3.3-70b-versatile", 
            temperature=settings.LLM_TEMPERATURE,
            model_kwargs={"response_format": {"type": "json_object"}} # Forces strict JSON output
        )

        qa_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)

        try:
            raw = await qa_chain.ainvoke({'input': query, 'query': query, 'context': docs, 'history': history_text})
        except Exception as exc:
            raise RuntimeError(
                f"AI generation failed via Ollama ({type(exc).__name__}): {exc}. "
                "Verify Ollama is running and the configured model is available."
            ) from exc

        return self._coerce_qa_payload(raw, contexts)

    def _coerce_qa_payload(self, raw: object, contexts: list[dict]) -> dict:
        text = str(raw or '').strip()
        if not text:
            return {'answer': 'Information not found.', 'citationIds': []}

        payload = self._extract_json_payload(text)
        if payload is not None:
            answer = str(payload.get('answer') or '').strip() or 'Information not found.'
            citation_ids = payload.get('citationIds') or []
            citation_ids = self._normalize_citation_ids(citation_ids)
            if answer.lower() == 'information not found.':
                citation_ids = []
            return {'answer': answer, 'citationIds': citation_ids}

        # If JSON is malformed, still return the model text (AI-generated),
        # and let the chat service attach top retrieved citations.
        return {'answer': text, 'citationIds': []}

    def _extract_json_payload(self, text: str) -> dict | None:
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        match = re.search(r'\{.*\}', text, flags=re.DOTALL)
        if not match:
            return None

        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None

        return None

    def _normalize_citation_ids(self, citation_ids: list) -> list[str]:
        normalized: list[str] = []
        for item in citation_ids:
            if not isinstance(item, (str, int)):
                continue
            cid = str(item).strip().upper()
            if not cid:
                continue
            if cid.isdigit():
                cid = f"C{cid}"
            if cid.startswith('C') and cid[1:].isdigit() and cid not in normalized:
                normalized.append(cid)
        return normalized

