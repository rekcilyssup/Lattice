from __future__ import annotations

import json
import httpx
from app.core.config import settings
from app.utils.text import create_snippet
from app.utils.vector import normalize


class AIService:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        provider = settings.EMBEDDING_PROVIDER.lower()
        if provider == 'ollama':
            return [await self._embed_ollama(t) for t in texts]
        return [self._embed_mock(t) for t in texts]

    async def _embed_ollama(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text},
            )
            resp.raise_for_status()
            emb = resp.json().get('embedding', [])
            return normalize([float(x) for x in emb])

    def _embed_mock(self, text: str) -> list[float]:
        vec = [0.0] * settings.EMBEDDING_DIMENSION
        for i, ch in enumerate(text):
            vec[i % settings.EMBEDDING_DIMENSION] += ord(ch) / 255.0
        return normalize(vec)

    async def generate_answer(self, query: str, contexts: list[dict]) -> dict:
        if not contexts:
            return {"answer": "Information not found.", "citationIds": []}

        provider = settings.LLM_PROVIDER.lower()
        if provider == 'ollama':
            return await self._answer_ollama(query, contexts)

        first = contexts[0]
        return {"answer": create_snippet(first['content'], 260), "citationIds": [first['citationId']]}

    async def _answer_ollama(self, query: str, contexts: list[dict]) -> dict:
        system = (
            'You are a strict retrieval QA assistant. '
            'Only answer from supplied context chunks. '
            'If answer is absent, respond with "Information not found." and empty citationIds. '
            'Return ONLY valid JSON with schema: {"answer": string, "citationIds": string[]}. '
        )

        context_text = "\n\n".join(
            [f"[{c['citationId']}] {c['documentName']} page {c['pageNumber']}\nContent: {c['content']}" for c in contexts]
        )

        user = f"Question: {query}\n\nContext:\n{context_text}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": settings.LLM_MODEL,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": settings.LLM_TEMPERATURE},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            content = resp.json().get('message', {}).get('content', '{}')

        try:
            payload = json.loads(content)
            return {
                "answer": (payload.get('answer') or 'Information not found.').strip(),
                "citationIds": payload.get('citationIds') or [],
            }
        except Exception:
            return {"answer": "Information not found.", "citationIds": []}
