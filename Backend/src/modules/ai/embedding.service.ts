import { env } from '../../config/env.js';
import { AppError } from '../../shared/errors.js';
import { logger } from '../../shared/logger.js';
import { normalizeL2 } from '../../shared/vector.js';

interface OpenAIEmbeddingResponse {
  data: Array<{ embedding: number[] }>;
}

interface GeminiEmbeddingResponse {
  embedding?: {
    values?: number[];
  };
}

export class EmbeddingService {
  async embed(texts: string[]): Promise<number[][]> {
    if (texts.length === 0) {
      return [];
    }

    const provider = this.resolveProvider();

    if (provider === 'openai') {
      return this.embedWithOpenAI(texts);
    }

    if (provider === 'gemini') {
      return this.embedWithGemini(texts);
    }

    if (provider === 'ollama') {
      return this.embedWithOllama(texts);
    }

    return this.embedWithMock(texts);
  }

  private resolveProvider(): 'openai' | 'gemini' | 'ollama' | 'mock' {
    if (env.EMBEDDING_PROVIDER === 'openai' && env.OPENAI_API_KEY) {
      return 'openai';
    }

    if (env.EMBEDDING_PROVIDER === 'gemini' && env.GEMINI_API_KEY) {
      return 'gemini';
    }

    if (env.EMBEDDING_PROVIDER === 'ollama') {
      return 'ollama';
    }

    if (env.EMBEDDING_PROVIDER !== 'mock') {
      logger.warn({ provider: env.EMBEDDING_PROVIDER }, 'Embedding key missing, falling back to mock embeddings');
    }

    return 'mock';
  }

  private async embedWithOpenAI(texts: string[]): Promise<number[][]> {
    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: env.EMBEDDING_MODEL,
        input: texts,
      }),
    });

    if (!response.ok) {
      const details = await response.text();
      throw new AppError('Failed to fetch embeddings from OpenAI', 502, 'EMBEDDING_PROVIDER_ERROR', details);
    }

    const payload = (await response.json()) as OpenAIEmbeddingResponse;
    return payload.data.map((item) => normalizeL2(this.alignDimensions(item.embedding)));
  }

  private async embedWithGemini(texts: string[]): Promise<number[][]> {
    const results: number[][] = [];

    for (const text of texts) {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${env.EMBEDDING_MODEL}:embedContent?key=${env.GEMINI_API_KEY}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: `models/${env.EMBEDDING_MODEL}`,
            content: {
              parts: [{ text }],
            },
          }),
        },
      );

      if (!response.ok) {
        const details = await response.text();
        throw new AppError('Failed to fetch embeddings from Gemini', 502, 'EMBEDDING_PROVIDER_ERROR', details);
      }

      const payload = (await response.json()) as GeminiEmbeddingResponse;
      const embedding = payload.embedding?.values;

      if (!embedding || embedding.length === 0) {
        throw new AppError('Gemini embedding response is empty', 502, 'EMBEDDING_PROVIDER_ERROR');
      }

      results.push(normalizeL2(this.alignDimensions(embedding)));
    }

    return results;
  }

  private async embedWithOllama(texts: string[]): Promise<number[][]> {
    const results: number[][] = [];

    for (const text of texts) {
      const response = await fetch(`${env.OLLAMA_BASE_URL}/api/embeddings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: env.OLLAMA_EMBEDDING_MODEL,
          prompt: text,
        }),
      });

      if (!response.ok) {
        const details = await response.text();
        throw new AppError('Failed to fetch embeddings from Ollama', 502, 'EMBEDDING_PROVIDER_ERROR', details);
      }

      const payload = (await response.json()) as { embedding?: number[] };
      if (!payload.embedding || payload.embedding.length === 0) {
        throw new AppError('Ollama embedding response is empty', 502, 'EMBEDDING_PROVIDER_ERROR');
      }

      results.push(normalizeL2(this.alignDimensions(payload.embedding)));
    }

    return results;
  }

  private embedWithMock(texts: string[]): Promise<number[][]> {
    const vectors = texts.map((text) => {
      const vector = new Array<number>(env.EMBEDDING_DIMENSION).fill(0);

      for (let index = 0; index < text.length; index += 1) {
        const slot = index % env.EMBEDDING_DIMENSION;
        vector[slot] += text.charCodeAt(index) / 255;
      }

      return normalizeL2(vector);
    });

    return Promise.resolve(vectors);
  }

  private alignDimensions(vector: number[]): number[] {
    if (vector.length === env.EMBEDDING_DIMENSION) {
      return vector;
    }

    if (vector.length > env.EMBEDDING_DIMENSION) {
      return vector.slice(0, env.EMBEDDING_DIMENSION);
    }

    return [...vector, ...new Array<number>(env.EMBEDDING_DIMENSION - vector.length).fill(0)];
  }
}
