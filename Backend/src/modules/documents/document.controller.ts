import type { Request, Response } from 'express';
import { AppError } from '../../shared/errors.js';
import type { DocumentMetadata } from '../../shared/types.js';
import { uploadMetadataSchema, workspaceIdSchema } from './document.schemas.js';
import { DocumentService } from './document.service.js';

const parseMetadata = (value: unknown): DocumentMetadata => {
  if (!value) {
    return {};
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return {};
    }

    try {
      const parsed = JSON.parse(trimmed) as unknown;
      return uploadMetadataSchema.parse(parsed);
    } catch (_error) {
      throw new AppError('Invalid metadata JSON', 400, 'INVALID_METADATA');
    }
  }

  if (typeof value === 'object') {
    return uploadMetadataSchema.parse(value);
  }

  return {};
};

export class DocumentController {
  constructor(private readonly documentService: DocumentService) {}

  async uploadDocument(req: Request, res: Response): Promise<void> {
    const { workspaceId } = workspaceIdSchema.parse(req.params);

    if (!req.file) {
      throw new AppError('PDF file is required', 400, 'FILE_REQUIRED');
    }

    const metadata = parseMetadata(req.body.metadata ?? {
      author: req.body.author,
      documentType: req.body.documentType,
      accessLevel: req.body.accessLevel,
    });

    const document = await this.documentService.uploadDocument({
      workspaceId,
      filePath: req.file.path,
      fileName: req.file.originalname,
      metadata,
    });

    res.status(202).json({ document });
  }

  async listDocuments(req: Request, res: Response): Promise<void> {
    const { workspaceId } = workspaceIdSchema.parse(req.params);
    const documents = await this.documentService.listDocuments(workspaceId);
    res.status(200).json({ documents });
  }
}
