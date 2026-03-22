import { query } from '../../db/pool.js';
import type { RetrievedChunk } from '../../shared/types.js';
import { toPgVectorLiteral } from '../../shared/vector.js';

interface RetrievedChunkRow {
  id: string;
  workspace_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  content: string;
  context_snippet: string;
  exact_quote: string;
  metadata: Record<string, unknown>;
  dense_score?: number;
  sparse_score?: number;
}

const mapChunk = (row: RetrievedChunkRow): RetrievedChunk => ({
  id: row.id,
  workspaceId: row.workspace_id,
  documentId: row.document_id,
  documentName: row.document_name,
  pageNumber: row.page_number,
  content: row.content,
  contextSnippet: row.context_snippet,
  exactQuote: row.exact_quote,
  metadata: row.metadata,
  denseScore: row.dense_score ?? 0,
  sparseScore: row.sparse_score ?? 0,
  fusedScore: 0,
  rerankScore: 0,
});

export class RetrievalRepository {
  async denseSearch(workspaceId: string, embedding: number[], topK: number): Promise<RetrievedChunk[]> {
    const vector = toPgVectorLiteral(embedding);

    const result = await query<RetrievedChunkRow>(
      `
        SELECT
          c.id,
          c.workspace_id,
          c.document_id,
          d.name AS document_name,
          c.page_number,
          c.content,
          c.context_snippet,
          c.exact_quote,
          c.metadata,
          (1 - (c.embedding <=> $2::vector))::float8 AS dense_score
        FROM chunks c
        INNER JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = $1
        ORDER BY c.embedding <=> $2::vector
        LIMIT $3
      `,
      [workspaceId, vector, topK],
    );

    return result.rows.map(mapChunk);
  }

  async sparseSearch(workspaceId: string, queryText: string, topK: number): Promise<RetrievedChunk[]> {
    const result = await query<RetrievedChunkRow>(
      `
        SELECT
          c.id,
          c.workspace_id,
          c.document_id,
          d.name AS document_name,
          c.page_number,
          c.content,
          c.context_snippet,
          c.exact_quote,
          c.metadata,
          ts_rank(c.search_vector, plainto_tsquery('english', $2))::float8 AS sparse_score
        FROM chunks c
        INNER JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = $1
          AND c.search_vector @@ plainto_tsquery('english', $2)
        ORDER BY sparse_score DESC
        LIMIT $3
      `,
      [workspaceId, queryText, topK],
    );

    return result.rows.map(mapChunk);
  }

  async metadataSearch(workspaceId: string, queryText: string, topK: number): Promise<RetrievedChunk[]> {
    const likePattern = `%${queryText}%`;

    const result = await query<RetrievedChunkRow>(
      `
        SELECT
          c.id,
          c.workspace_id,
          c.document_id,
          d.name AS document_name,
          c.page_number,
          c.content,
          c.context_snippet,
          c.exact_quote,
          c.metadata,
          CASE
            WHEN d.name ILIKE $2 THEN 1.0
            WHEN d.metadata::text ILIKE $2 THEN 0.8
            ELSE 0.2
          END::float8 AS sparse_score
        FROM chunks c
        INNER JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = $1
          AND (d.name ILIKE $2 OR d.metadata::text ILIKE $2 OR c.content ILIKE $2)
        ORDER BY sparse_score DESC
        LIMIT $3
      `,
      [workspaceId, likePattern, topK],
    );

    return result.rows.map(mapChunk);
  }
}
