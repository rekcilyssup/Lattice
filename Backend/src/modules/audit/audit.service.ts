import { query } from '../../db/pool.js';

interface LogQueryInput {
  id: string;
  workspaceId: string;
  userQuery: string;
  routeStrategy: string;
  retrievedChunkIds: string[];
  responseMessageId: string | null;
  latencyMs: number;
}

export class AuditService {
  async logQuery(input: LogQueryInput): Promise<void> {
    await query(
      `
        INSERT INTO query_audit_logs(
          id,
          workspace_id,
          user_query,
          route_strategy,
          retrieved_chunk_ids,
          response_message_id,
          latency_ms
        ) VALUES ($1, $2, $3, $4, $5::uuid[], $6, $7)
      `,
      [
        input.id,
        input.workspaceId,
        input.userQuery,
        input.routeStrategy,
        input.retrievedChunkIds,
        input.responseMessageId,
        input.latencyMs,
      ],
    );
  }
}
