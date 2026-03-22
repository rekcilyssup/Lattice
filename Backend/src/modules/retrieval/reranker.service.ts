import { env } from '../../config/env.js';
import type { RetrievedChunk } from '../../shared/types.js';
import { overlapScore } from '../../shared/text.js';

interface CohereRerankResponse {
  results?: Array<{
    index: number;
    relevance_score: number;
  }>;
}

export class RerankerService {
  async rerank(query: string, chunks: RetrievedChunk[]): Promise<RetrievedChunk[]> {
    if (chunks.length === 0) {
      return [];
    }

    if (env.RERANK_PROVIDER === 'cohere' && env.COHERE_API_KEY) {
      return this.rerankWithCohere(query, chunks);
    }

    return this.rerankWithHeuristic(query, chunks);
  }

  private async rerankWithCohere(query: string, chunks: RetrievedChunk[]): Promise<RetrievedChunk[]> {
    const response = await fetch('https://api.cohere.com/v2/rerank', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${env.COHERE_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'rerank-v3.5',
        query,
        top_n: Math.min(env.TOP_K_RERANK, chunks.length),
        documents: chunks.map((chunk) => chunk.content),
      }),
    });

    if (!response.ok) {
      return this.rerankWithHeuristic(query, chunks);
    }

    const payload = (await response.json()) as CohereRerankResponse;
    const scores = payload.results ?? [];

    const reranked = scores
      .map((item) => {
        const source = chunks[item.index];
        return {
          ...source,
          rerankScore: item.relevance_score,
        };
      })
      .sort((a, b) => b.rerankScore - a.rerankScore);

    return reranked;
  }

  private rerankWithHeuristic(query: string, chunks: RetrievedChunk[]): Promise<RetrievedChunk[]> {
    const reranked = chunks
      .map((chunk) => {
        const lexical = overlapScore(query, chunk.content);
        const dense = Math.max(chunk.denseScore, 0);
        const sparse = Math.max(chunk.sparseScore, 0);

        return {
          ...chunk,
          rerankScore: lexical * 0.6 + dense * 0.25 + sparse * 0.15,
        };
      })
      .sort((a, b) => b.rerankScore - a.rerankScore)
      .slice(0, env.TOP_K_RERANK);

    return Promise.resolve(reranked);
  }
}
