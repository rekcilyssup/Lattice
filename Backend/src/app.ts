import cors from 'cors';
import express from 'express';
import helmet from 'helmet';
import { env } from './config/env.js';
import { errorMiddleware } from './http/error-middleware.js';
import { EmbeddingService } from './modules/ai/embedding.service.js';
import { LlmService } from './modules/ai/llm.service.js';
import { AuditService } from './modules/audit/audit.service.js';
import { ChatController } from './modules/chat/chat.controller.js';
import { ChatRepository } from './modules/chat/chat.repository.js';
import { buildChatRoutes } from './modules/chat/chat.routes.js';
import { ChatService } from './modules/chat/chat.service.js';
import { DocumentController } from './modules/documents/document.controller.js';
import { DocumentRepository } from './modules/documents/document.repository.js';
import { buildDocumentRoutes } from './modules/documents/document.routes.js';
import { DocumentService } from './modules/documents/document.service.js';
import { buildHealthRoutes } from './modules/health/health.routes.js';
import { DocumentIngestionService } from './modules/ingestion/document-ingestion.service.js';
import { PdfLayoutParser } from './modules/ingestion/pdf-layout-parser.js';
import { RecursiveChunker } from './modules/ingestion/recursive-chunker.js';
import { HybridSearchService } from './modules/retrieval/hybrid-search.service.js';
import { RetrievalRepository } from './modules/retrieval/retrieval.repository.js';
import { RerankerService } from './modules/retrieval/reranker.service.js';
import { SemanticRouterService } from './modules/retrieval/semantic-router.service.js';
import { WorkspaceController } from './modules/workspaces/workspace.controller.js';
import { WorkspaceRepository } from './modules/workspaces/workspace.repository.js';
import { buildWorkspaceRoutes } from './modules/workspaces/workspace.routes.js';
import { WorkspaceService } from './modules/workspaces/workspace.service.js';
import { AppError } from './shared/errors.js';
import { logger } from './shared/logger.js';

export const createApp = () => {
  const app = express();

  app.use(
    cors({
      origin: env.CORS_ORIGIN,
      credentials: true,
    }),
  );

  app.use(helmet());
  app.use(express.json({ limit: '4mb' }));
  app.use(express.urlencoded({ extended: true }));
  app.use((req, res, next) => {
    const startedAt = Date.now();

    res.on('finish', () => {
      logger.info(
        {
          method: req.method,
          path: req.originalUrl,
          statusCode: res.statusCode,
          durationMs: Date.now() - startedAt,
        },
        'HTTP request',
      );
    });

    next();
  });

  const embeddingService = new EmbeddingService();
  const llmService = new LlmService();
  const auditService = new AuditService();

  const workspaceRepository = new WorkspaceRepository();
  const documentRepository = new DocumentRepository();
  const chatRepository = new ChatRepository();
  const retrievalRepository = new RetrievalRepository();

  const parser = new PdfLayoutParser();
  const chunker = new RecursiveChunker();
  const ingestionService = new DocumentIngestionService(documentRepository, embeddingService, parser, chunker);

  const workspaceService = new WorkspaceService(workspaceRepository, documentRepository, chatRepository);
  const documentService = new DocumentService(documentRepository, workspaceService, ingestionService);

  const semanticRouterService = new SemanticRouterService();
  const hybridSearchService = new HybridSearchService(retrievalRepository);
  const rerankerService = new RerankerService();
  const chatService = new ChatService(
    workspaceService,
    chatRepository,
    semanticRouterService,
    hybridSearchService,
    rerankerService,
    embeddingService,
    llmService,
    auditService,
  );

  const workspaceController = new WorkspaceController(workspaceService);
  const documentController = new DocumentController(documentService);
  const chatController = new ChatController(chatService);

  const apiRouter = express.Router();
  const workspaceRouter = buildWorkspaceRoutes(workspaceController);

  workspaceRouter.use('/:workspaceId/documents', buildDocumentRoutes(documentController));
  workspaceRouter.use('/:workspaceId/chat', buildChatRoutes(chatController));

  apiRouter.use('/health', buildHealthRoutes());
  apiRouter.use('/workspaces', workspaceRouter);

  app.use(env.API_BASE_PATH, apiRouter);

  app.use((_req, _res, next) => {
    next(new AppError('Route not found', 404, 'ROUTE_NOT_FOUND'));
  });

  app.use(errorMiddleware);

  return app;
};
