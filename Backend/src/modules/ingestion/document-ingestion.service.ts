import type { Document } from '../../shared/types.js';
import { logger } from '../../shared/logger.js';
import { EmbeddingService } from '../ai/embedding.service.js';
import { DocumentRepository } from '../documents/document.repository.js';
import { PdfLayoutParser } from './pdf-layout-parser.js';
import { RecursiveChunker } from './recursive-chunker.js';

export class DocumentIngestionService {
  constructor(
    private readonly documentRepository: DocumentRepository,
    private readonly embeddingService: EmbeddingService,
    private readonly parser: PdfLayoutParser,
    private readonly chunker: RecursiveChunker,
  ) {}

  scheduleIngestion(document: Document): void {
    setImmediate(() => {
      this.process(document).catch((error) => {
        logger.error({ error, documentId: document.id }, 'Document ingestion failed');
      });
    });
  }

  private async process(document: Document): Promise<void> {
    try {
      const blocks = await this.parser.parse(document.storagePath);

      const chunks = this.chunker.chunk(blocks, {
        documentId: document.id,
        documentName: document.name,
        ...document.metadata,
      });

      const embeddings = await this.embedInBatches(chunks.map((chunk) => chunk.content));

      await this.documentRepository.replaceChunks({
        workspaceId: document.workspaceId,
        documentId: document.id,
        chunks,
        embeddings,
      });

      await this.documentRepository.updateStatus({
        documentId: document.id,
        status: 'indexed',
        errorMessage: null,
      });

      logger.info(
        {
          documentId: document.id,
          chunkCount: chunks.length,
        },
        'Document indexed successfully',
      );
    } catch (error) {
      await this.documentRepository.updateStatus({
        documentId: document.id,
        status: 'failed',
        errorMessage: error instanceof Error ? error.message : 'Unknown ingestion error',
      });

      throw error;
    }
  }

  private async embedInBatches(texts: string[]): Promise<number[][]> {
    const batchSize = 32;
    const vectors: number[][] = [];

    for (let start = 0; start < texts.length; start += batchSize) {
      const batch = texts.slice(start, start + batchSize);
      const batchVectors = await this.embeddingService.embed(batch);
      vectors.push(...batchVectors);
    }

    return vectors;
  }
}
