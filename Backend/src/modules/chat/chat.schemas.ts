import { z } from 'zod';

export const workspaceIdSchema = z.object({
  workspaceId: z.string().uuid(),
});

export const askQuestionSchema = z.object({
  query: z.string().trim().min(2).max(5000),
});
