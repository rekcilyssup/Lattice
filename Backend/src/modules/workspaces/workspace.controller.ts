import type { Request, Response } from 'express';
import { createWorkspaceSchema, workspaceIdSchema } from './workspace.schemas.js';
import { WorkspaceService } from './workspace.service.js';

export class WorkspaceController {
  constructor(private readonly workspaceService: WorkspaceService) {}

  async createWorkspace(req: Request, res: Response): Promise<void> {
    const payload = createWorkspaceSchema.parse(req.body);
    const workspace = await this.workspaceService.createWorkspace(payload.name);
    res.status(201).json({ workspace });
  }

  async listWorkspaces(_req: Request, res: Response): Promise<void> {
    const workspaces = await this.workspaceService.listWorkspaces();
    res.status(200).json({ workspaces });
  }

  async getWorkspace(req: Request, res: Response): Promise<void> {
    const { workspaceId } = workspaceIdSchema.parse(req.params);
    const workspace = await this.workspaceService.getWorkspace(workspaceId);
    res.status(200).json({ workspace });
  }
}
