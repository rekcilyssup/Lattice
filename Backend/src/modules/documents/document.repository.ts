import { randomUUID } from 'node:crypto';
import { query } from '../../db/pool.js';
import type { ChunkDraft, Document, DocumentMetadata } from '../../shared/types.js';
import { toPgVectorLiteral } from '../../shared/vector.js';

interface DocumentRow {
  id: string;
  workspace_id: string;
  name: string;
  storage_path: string;
  status: 'ingesting' | 'indexed' | 'failed';
  metadata: DocumentMetadata;
  error_message: string | null;
  created_at: Date | string;
  updated_at: Date | string;
}

const mapDocument = (row: DocumentRow): Document => ({
  id: row.id,
  workspaceId: row.workspace_id,
  name: row.name,
  storagePath: row.storage_path,
  status: row.status,
  metadata: row.metadata,
  errorMessage: row.error_message,
  createdAt: new Date(row.created_at).toISOString(),
  updatedAt: new Date(row.updated_at).toISOString(),
});

export class DocumentRepository {
  async create(params: {
    id: string;
    workspaceId: string;
    name: string;
    storagePath: string;
    status: 'ingesting' | 'indexed' | 'failed';
    metadata: DocumentMetadata;
  }): Promise<Document> {
    const result = await query<DocumentRow>(
      `
        INSERT INTO documents(id, workspace_id, name, storage_path, status, metadata)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id, workspace_id, name, storage_path, status, metadata, error_message, created_at, updated_at
      `,
      [params.id, params.workspaceId, params.name, params.storagePath, params.status, JSON.stringify(params.metadata)],
    );

    return mapDocument(result.rows[0]);
  }

  async findById(documentId: string): Promise<Document | null> {
    const result = await query<DocumentRow>(
      `
        SELECT id, workspace_id, name, storage_path, status, metadata, error_message, created_at, updated_at
        FROM documents
        WHERE id = $1
      `,
      [documentId],
    );

    if (result.rowCount === 0) {
      return null;
    }

    return mapDocument(result.rows[0]);
  }

  async listByWorkspace(workspaceId: string): Promise<Document[]> {
    const result = await query<DocumentRow>(
      `
        SELECT id, workspace_id, name, storage_path, status, metadata, error_message, created_at, updated_at
        FROM documents
        WHERE workspace_id = $1
        ORDER BY created_at ASC
      `,
      [workspaceId],
    );

    return result.rows.map(mapDocument);
  }

  async updateStatus(params: { documentId: string; status: 'ingesting' | 'indexed' | 'failed'; errorMessage?: string | null }): Promise<void> {
    await query(
      `
        UPDATE documents
        SET status = $2,
            error_message = $3,
            updated_at = NOW()
        WHERE id = $1
      `,
      [params.documentId, params.status, params.errorMessage ?? null],
    );
  }

  async replaceChunks(params: {
    workspaceId: string;
    documentId: string;
    chunks: ChunkDraft[];
    embeddings: number[][];
  }): Promise<void> {
    await query('DELETE FROM chunks WHERE document_id = $1', [params.documentId]);

    if (params.chunks.length === 0) {
      return;
    }

    const valueClauses: string[] = [];
    const values: unknown[] = [];

    params.chunks.forEach((chunk, index) => {
      const offset = index * 10;
      valueClauses.push(
        `(
          $${offset + 1},
          $${offset + 2},
          $${offset + 3},
          $${offset + 4},
          $${offset + 5},
          $${offset + 6},
          $${offset + 7},
          $${offset + 8},
          $${offset + 9}::jsonb,
          $${offset + 10}::vector,
          NOW()
        )`,
      );

      values.push(
        randomUUID(),
        params.workspaceId,
        params.documentId,
        chunk.chunkIndex,
        chunk.pageNumber,
        chunk.content,
        chunk.contextSnippet,
        chunk.exactQuote,
        JSON.stringify(chunk.metadata),
        toPgVectorLiteral(params.embeddings[index]),
      );
    });

    await query(
      `
        INSERT INTO chunks(
          id,
          workspace_id,
          document_id,
          chunk_index,
          page_number,
          content,
          context_snippet,
          exact_quote,
          metadata,
          embedding,
          created_at
        ) VALUES ${valueClauses.join(',')}
      `,
      values,
    );
  }
}
