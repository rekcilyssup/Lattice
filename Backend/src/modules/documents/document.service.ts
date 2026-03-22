import { v4 as uuid } from 'uuid';
import { AppError } from '../../shared/errors.js';
import type { Document, DocumentMetadata } from '../../shared/types.js';
import { DocumentIngestionService } from '../ingestion/document-ingestion.service.js';
import { WorkspaceService } from '../workspaces/workspace.service.js';
import { DocumentRepository } from './document.repository.js';

interface UploadPayload {
  workspaceId: string;
  filePath: string;
  fileName: string;
  metadata: DocumentMetadata;
}

export class DocumentService {
  constructor(
    private readonly documentRepository: DocumentRepository,
    private readonly workspaceService: WorkspaceService,
    private readonly ingestionService: DocumentIngestionService,
  ) {}

  async uploadDocument(payload: UploadPayload): Promise<Document> {
    await this.workspaceService.ensureWorkspaceExists(payload.workspaceId);

    const metadata: DocumentMetadata = {
      ...payload.metadata,
      uploadedAt: new Date().toISOString(),
    };

    const document = await this.documentRepository.create({
      id: uuid(),
      workspaceId: payload.workspaceId,
      name: payload.fileName,
      storagePath: payload.filePath,
      status: 'ingesting',
      metadata,
    });

    this.ingestionService.scheduleIngestion(document);

    return document;
  }

  async listDocuments(workspaceId: string): Promise<Document[]> {
    await this.workspaceService.ensureWorkspaceExists(workspaceId);
    return this.documentRepository.listByWorkspace(workspaceId);
  }

  async getDocument(workspaceId: string, documentId: string): Promise<Document> {
    await this.workspaceService.ensureWorkspaceExists(workspaceId);

    const document = await this.documentRepository.findById(documentId);
    if (!document || document.workspaceId !== workspaceId) {
      throw new AppError('Document not found', 404, 'DOCUMENT_NOT_FOUND');
    }

    return document;
  }
}
