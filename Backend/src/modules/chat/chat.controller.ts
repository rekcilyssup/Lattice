import type { Request, Response } from 'express';
import { askQuestionSchema, workspaceIdSchema } from './chat.schemas.js';
import { ChatService } from './chat.service.js';

export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  async askQuestion(req: Request, res: Response): Promise<void> {
    const { workspaceId } = workspaceIdSchema.parse(req.params);
    const payload = askQuestionSchema.parse(req.body);

    const result = await this.chatService.askQuestion(workspaceId, payload.query);

    res.status(200).json({
      answer: result.answer,
      citations: result.citations,
      routeStrategy: result.routeStrategy,
      message: result.message,
    });
  }
}
