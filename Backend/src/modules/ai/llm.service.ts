import { env } from '../../config/env.js';
import { AppError } from '../../shared/errors.js';
import { createSnippet } from '../../shared/text.js';

interface ContextInput {
  citationId: string;
  documentName: string;
  pageNumber: number;
  content: string;
}

interface LlmResponse {
  answer: string;
  citationIds: string[];
}

interface OpenAIChatResponse {
  choices: Array<{
    message: {
      content?: string;
    };
  }>;
}

interface GeminiGenerateContentResponse {
  candidates?: Array<{
    content?: {
      parts?: Array<{
        text?: string;
      }>;
    };
  }>;
}

export class LlmService {
  async generateGroundedAnswer(query: string, contexts: ContextInput[]): Promise<LlmResponse> {
    if (contexts.length === 0) {
      return {
        answer: 'Information not found.',
        citationIds: [],
      };
    }

    const provider = this.resolveProvider();

    if (provider === 'openai') {
      return this.generateWithOpenAI(query, contexts);
    }

    if (provider === 'gemini') {
      return this.generateWithGemini(query, contexts);
    }

    if (provider === 'ollama') {
      return this.generateWithOllama(query, contexts);
    }

    return this.generateWithMock(contexts);
  }

  private resolveProvider(): 'openai' | 'gemini' | 'ollama' | 'mock' {
    if (env.LLM_PROVIDER === 'openai' && env.OPENAI_API_KEY) {
      return 'openai';
    }

    if (env.LLM_PROVIDER === 'gemini' && env.GEMINI_API_KEY) {
      return 'gemini';
    }

    if (env.LLM_PROVIDER === 'ollama') {
      return 'ollama';
    }

    return 'mock';
  }

  private buildSystemPrompt(): string {
    return [
      'You are a strict retrieval QA assistant.',
      'Only answer from supplied context chunks.',
      'If answer is absent, respond with "Information not found." and empty citationIds.',
      'Return ONLY valid JSON with schema: {"answer": string, "citationIds": string[]}.',
    ].join(' ');
  }

  private buildUserPrompt(query: string, contexts: ContextInput[]): string {
    const contextBlock = contexts
      .map(
        (item) =>
          `[${item.citationId}] ${item.documentName} page ${item.pageNumber}\n` +
          `Content: ${item.content.replace(/\s+/g, ' ').trim()}`,
      )
      .join('\n\n');

    return `Question: ${query}\n\nContext:\n${contextBlock}`;
  }

  private parseJson(text: string): LlmResponse {
    try {
      const normalized = text
        .trim()
        .replace(/^```json/i, '')
        .replace(/^```/i, '')
        .replace(/```$/i, '')
        .trim();
      const start = normalized.indexOf('{');
      const end = normalized.lastIndexOf('}');
      const candidate = start >= 0 && end >= 0 ? normalized.slice(start, end + 1) : normalized;

      const parsed = JSON.parse(candidate) as { answer?: string; citationIds?: unknown };
      return {
        answer: parsed.answer?.trim() || 'Information not found.',
        citationIds: Array.isArray(parsed.citationIds)
          ? parsed.citationIds.filter((item): item is string => typeof item === 'string')
          : [],
      };
    } catch (_error) {
      throw new AppError('LLM response was not valid JSON', 502, 'LLM_PARSE_ERROR', text);
    }
  }

  private async generateWithOpenAI(query: string, contexts: ContextInput[]): Promise<LlmResponse> {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: env.LLM_MODEL,
        temperature: env.LLM_TEMPERATURE,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: this.buildSystemPrompt() },
          { role: 'user', content: this.buildUserPrompt(query, contexts) },
        ],
      }),
    });

    if (!response.ok) {
      const details = await response.text();
      throw new AppError('Failed to generate answer with OpenAI', 502, 'LLM_PROVIDER_ERROR', details);
    }

    const payload = (await response.json()) as OpenAIChatResponse;
    const content = payload.choices?.[0]?.message?.content;

    if (!content) {
      throw new AppError('OpenAI returned empty content', 502, 'LLM_PROVIDER_ERROR');
    }

    return this.parseJson(content);
  }

  private async generateWithGemini(query: string, contexts: ContextInput[]): Promise<LlmResponse> {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${env.LLM_MODEL}:generateContent?key=${env.GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                {
                  text: `${this.buildSystemPrompt()}\n\n${this.buildUserPrompt(query, contexts)}`,
                },
              ],
            },
          ],
          generationConfig: {
            temperature: env.LLM_TEMPERATURE,
            responseMimeType: 'application/json',
          },
        }),
      },
    );

    if (!response.ok) {
      const details = await response.text();
      throw new AppError('Failed to generate answer with Gemini', 502, 'LLM_PROVIDER_ERROR', details);
    }

    const payload = (await response.json()) as GeminiGenerateContentResponse;
    const content = payload.candidates?.[0]?.content?.parts?.[0]?.text;

    if (!content) {
      throw new AppError('Gemini returned empty content', 502, 'LLM_PROVIDER_ERROR');
    }

    return this.parseJson(content);
  }

  private async generateWithOllama(query: string, contexts: ContextInput[]): Promise<LlmResponse> {
    const response = await fetch(`${env.OLLAMA_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: env.LLM_MODEL,
        format: 'json',
        stream: false,
        options: {
          temperature: env.LLM_TEMPERATURE,
        },
        messages: [
          { role: 'system', content: this.buildSystemPrompt() },
          { role: 'user', content: this.buildUserPrompt(query, contexts) },
        ],
      }),
    });

    if (!response.ok) {
      const details = await response.text();
      throw new AppError('Failed to generate answer with Ollama', 502, 'LLM_PROVIDER_ERROR', details);
    }

    const payload = (await response.json()) as { message?: { content?: string } };
    const content = payload.message?.content;

    if (!content) {
      throw new AppError('Ollama returned empty content', 502, 'LLM_PROVIDER_ERROR');
    }

    return this.parseJson(content);
  }

  private generateWithMock(contexts: ContextInput[]): Promise<LlmResponse> {
    const first = contexts[0];
    return Promise.resolve({
      answer: createSnippet(first.content, 260),
      citationIds: [first.citationId],
    });
  }
}
