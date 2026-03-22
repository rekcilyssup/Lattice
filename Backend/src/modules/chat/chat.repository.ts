import { query } from '../../db/pool.js';
import type { Citation, Message } from '../../shared/types.js';

interface MessageRow {
  id: string;
  workspace_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  retrieval_trace: Record<string, unknown> | null;
  created_at: Date | string;
}

interface CreateMessageInput {
  id: string;
  workspaceId: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  retrievalTrace: Record<string, unknown> | null;
}

const mapMessage = (row: MessageRow): Message => ({
  id: row.id,
  workspaceId: row.workspace_id,
  role: row.role,
  content: row.content,
  citations: row.citations ?? [],
  retrievalTrace: row.retrieval_trace,
  createdAt: new Date(row.created_at).toISOString(),
});

export class ChatRepository {
  async createMessage(input: CreateMessageInput): Promise<Message> {
    const result = await query<MessageRow>(
      `
        INSERT INTO messages(id, workspace_id, role, content, citations, retrieval_trace)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
        RETURNING id, workspace_id, role, content, citations, retrieval_trace, created_at
      `,
      [input.id, input.workspaceId, input.role, input.content, JSON.stringify(input.citations), JSON.stringify(input.retrievalTrace)],
    );

    return mapMessage(result.rows[0]);
  }

  async listMessagesByWorkspace(workspaceId: string): Promise<Message[]> {
    const result = await query<MessageRow>(
      `
        SELECT id, workspace_id, role, content, citations, retrieval_trace, created_at
        FROM messages
        WHERE workspace_id = $1
        ORDER BY created_at ASC
      `,
      [workspaceId],
    );

    return result.rows.map(mapMessage);
  }
}
