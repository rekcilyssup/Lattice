import { query } from '../../db/pool.js';
import type { Workspace } from '../../shared/types.js';

interface WorkspaceRow {
  id: string;
  name: string;
  created_at: Date | string;
  updated_at: Date | string;
}

const mapWorkspace = (row: WorkspaceRow): Workspace => ({
  id: row.id,
  name: row.name,
  createdAt: new Date(row.created_at).toISOString(),
  updatedAt: new Date(row.updated_at).toISOString(),
});

export class WorkspaceRepository {
  async create(id: string, name: string): Promise<Workspace> {
    const result = await query<WorkspaceRow>(
      `
        INSERT INTO workspaces(id, name)
        VALUES ($1, $2)
        RETURNING id, name, created_at, updated_at
      `,
      [id, name],
    );

    return mapWorkspace(result.rows[0]);
  }

  async findById(id: string): Promise<Workspace | null> {
    const result = await query<WorkspaceRow>(
      `
        SELECT id, name, created_at, updated_at
        FROM workspaces
        WHERE id = $1
      `,
      [id],
    );

    if (result.rowCount === 0) {
      return null;
    }

    return mapWorkspace(result.rows[0]);
  }

  async list(): Promise<Workspace[]> {
    const result = await query<WorkspaceRow>(
      `
        SELECT id, name, created_at, updated_at
        FROM workspaces
        ORDER BY created_at ASC
      `,
    );

    return result.rows.map(mapWorkspace);
  }
}
