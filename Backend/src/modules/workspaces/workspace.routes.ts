import { Router } from 'express';
import { asyncHandler } from '../../http/async-handler.js';
import { WorkspaceController } from './workspace.controller.js';

export const buildWorkspaceRoutes = (workspaceController: WorkspaceController): Router => {
  const router = Router();

  router.post('/', asyncHandler((req, res) => workspaceController.createWorkspace(req, res)));
  router.get('/', asyncHandler((req, res) => workspaceController.listWorkspaces(req, res)));
  router.get('/:workspaceId', asyncHandler((req, res) => workspaceController.getWorkspace(req, res)));

  return router;
};
