import { Router } from 'express';
import { asyncHandler } from '../../http/async-handler.js';
import { ChatController } from './chat.controller.js';

export const buildChatRoutes = (chatController: ChatController): Router => {
  const router = Router({ mergeParams: true });

  router.post('/', asyncHandler((req, res) => chatController.askQuestion(req, res)));

  return router;
};
