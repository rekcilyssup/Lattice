import { env } from '../../config/env.js';
import type { RetrievedChunk } from '../../shared/types.js';
import { RetrievalRepository } from './retrieval.repository.js';
import type { RouteStrategy } from './retrieval.types.js';

interface SearchInput {
  workspaceId: string;
  query: string;
  routeStrategy: RouteStrategy;
  queryEmbedding?: number[];
}

export class HybridSearchService {
  constructor(private readonly retrievalRepository: RetrievalRepository) {}

  async search(input: SearchInput): Promise<RetrievedChunk[]> {
    let dense: RetrievedChunk[] = [];
    let sparse: RetrievedChunk[] = [];
    let metadata: RetrievedChunk[] = [];

    if ((input.routeStrategy === 'vector' || input.routeStrategy === 'hybrid') && input.queryEmbedding) {
      dense = await this.retrievalRepository.denseSearch(input.workspaceId, input.queryEmbedding, env.TOP_K_DENSE);
    }

    if (input.routeStrategy === 'keyword' || input.routeStrategy === 'hybrid') {
      sparse = await this.retrievalRepository.sparseSearch(input.workspaceId, input.query, env.TOP_K_SPARSE);
    }

    if (input.routeStrategy === 'metadata') {
      metadata = await this.retrievalRepository.metadataSearch(input.workspaceId, input.query, env.TOP_K_SPARSE);
      sparse = await this.retrievalRepository.sparseSearch(input.workspaceId, input.query, env.TOP_K_SPARSE);
    }

    if (input.routeStrategy === 'vector') {
      return dense;
    }

    return this.fuseResults(dense, sparse, metadata).slice(0, Math.max(env.TOP_K_DENSE, env.TOP_K_SPARSE));
  }

  private fuseResults(dense: RetrievedChunk[], sparse: RetrievedChunk[], metadata: RetrievedChunk[]): RetrievedChunk[] {
    const map = new Map<string, RetrievedChunk>();
    const rrfK = 60;

    dense.forEach((item, index) => {
      const existing = map.get(item.id) ?? { ...item };
      existing.denseScore = item.denseScore;
      existing.fusedScore += 0.55 * (1 / (rrfK + index + 1));
      map.set(item.id, existing);
    });

    sparse.forEach((item, index) => {
      const existing = map.get(item.id) ?? { ...item };
      existing.sparseScore = item.sparseScore;
      existing.fusedScore += 0.35 * (1 / (rrfK + index + 1));
      map.set(item.id, existing);
    });

    metadata.forEach((item, index) => {
      const existing = map.get(item.id) ?? { ...item };
      existing.sparseScore = Math.max(existing.sparseScore, item.sparseScore);
      existing.fusedScore += 0.1 * (1 / (rrfK + index + 1));
      map.set(item.id, existing);
    });

    return Array.from(map.values()).sort((a, b) => b.fusedScore - a.fusedScore);
  }
}
