import { v4 as uuid } from 'uuid';
import { env } from '../../config/env.js';
import type { Citation, Message, RetrievedChunk } from '../../shared/types.js';
import { AuditService } from '../audit/audit.service.js';
import { EmbeddingService } from '../ai/embedding.service.js';
import { LlmService } from '../ai/llm.service.js';
import { HybridSearchService } from '../retrieval/hybrid-search.service.js';
import { RerankerService } from '../retrieval/reranker.service.js';
import { SemanticRouterService } from '../retrieval/semantic-router.service.js';
import { ChatRepository } from './chat.repository.js';
import { WorkspaceService } from '../workspaces/workspace.service.js';

interface AskQuestionResult {
  message: Message;
  answer: string;
  citations: Citation[];
  routeStrategy: string;
}

export class ChatService {
  constructor(
    private readonly workspaceService: WorkspaceService,
    private readonly chatRepository: ChatRepository,
    private readonly semanticRouterService: SemanticRouterService,
    private readonly hybridSearchService: HybridSearchService,
    private readonly rerankerService: RerankerService,
    private readonly embeddingService: EmbeddingService,
    private readonly llmService: LlmService,
    private readonly auditService: AuditService,
  ) {}

  async askQuestion(workspaceId: string, query: string): Promise<AskQuestionResult> {
    const startedAt = Date.now();
    await this.workspaceService.ensureWorkspaceExists(workspaceId);

    await this.chatRepository.createMessage({
      id: uuid(),
      workspaceId,
      role: 'user',
      content: query,
      citations: [],
      retrievalTrace: null,
    });

    const routeStrategy = this.semanticRouterService.route(query);

    const queryEmbedding =
      routeStrategy === 'keyword' || routeStrategy === 'metadata'
        ? undefined
        : (await this.embeddingService.embed([query]))[0];

    const retrieved = await this.hybridSearchService.search({
      workspaceId,
      query,
      routeStrategy,
      queryEmbedding,
    });

    const reranked = await this.rerankerService.rerank(query, retrieved);
    const topChunks = reranked.slice(0, env.TOP_K_RERANK);

    let answer = 'Information not found.';
    let citations: Citation[] = [];

    if (topChunks.length > 0) {
      const llmContexts = topChunks.map((chunk, index) => ({
        citationId: `C${index + 1}`,
        documentName: chunk.documentName,
        pageNumber: chunk.pageNumber,
        content: chunk.content,
      }));

      const llmOutput = await this.llmService.generateGroundedAnswer(query, llmContexts);
      answer = llmOutput.answer.trim() || 'Information not found.';

      if (!/information not found/i.test(answer)) {
        const selectedChunkMap = this.selectChunksForCitations(llmOutput.citationIds, topChunks);
        const citationChunks = selectedChunkMap.length > 0 ? selectedChunkMap : topChunks.slice(0, Math.min(3, topChunks.length));

        citations = citationChunks.map((chunk, index) => ({
          citation_id: `${index + 1}`,
          document_name: chunk.documentName,
          page_number: chunk.pageNumber,
          exact_quote: chunk.exactQuote,
          context_snippet: chunk.contextSnippet,
        }));
      }
    }

    const retrievalTrace = {
      routeStrategy,
      retrievedCount: retrieved.length,
      rerankedCount: reranked.length,
      chunkScores: topChunks.map((chunk) => ({
        chunkId: chunk.id,
        denseScore: chunk.denseScore,
        sparseScore: chunk.sparseScore,
        fusedScore: chunk.fusedScore,
        rerankScore: chunk.rerankScore,
      })),
    };

    const assistantMessage = await this.chatRepository.createMessage({
      id: uuid(),
      workspaceId,
      role: 'assistant',
      content: answer,
      citations,
      retrievalTrace,
    });

    await this.auditService.logQuery({
      id: uuid(),
      workspaceId,
      userQuery: query,
      routeStrategy,
      retrievedChunkIds: topChunks.map((chunk) => chunk.id),
      responseMessageId: assistantMessage.id,
      latencyMs: Date.now() - startedAt,
    });

    return {
      message: assistantMessage,
      answer,
      citations,
      routeStrategy,
    };
  }

  private selectChunksForCitations(citationIds: string[], chunks: RetrievedChunk[]): RetrievedChunk[] {
    const matched: RetrievedChunk[] = [];

    citationIds.forEach((citationId) => {
      const normalized = citationId.trim().toUpperCase();
      const index = Number(normalized.replace('C', '')) - 1;

      if (!Number.isNaN(index) && chunks[index]) {
        matched.push(chunks[index]);
      }
    });

    const deduplicated = new Map<string, RetrievedChunk>();
    matched.forEach((chunk) => {
      deduplicated.set(chunk.id, chunk);
    });

    return Array.from(deduplicated.values());
  }
}
