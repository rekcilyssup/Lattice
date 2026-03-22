import { z } from 'zod';

export const createWorkspaceSchema = z.object({
  name: z.string().trim().min(2).max(120),
});

export const workspaceIdSchema = z.object({
  workspaceId: z.string().uuid(),
});
