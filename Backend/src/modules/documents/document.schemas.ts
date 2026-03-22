import { z } from 'zod';

export const workspaceIdSchema = z.object({
  workspaceId: z.string().uuid(),
});

export const uploadMetadataSchema = z.object({
  author: z.string().trim().min(1).max(200).optional(),
  documentType: z.string().trim().min(1).max(120).optional(),
  accessLevel: z.string().trim().min(1).max(60).optional(),
});
