export type DocumentStatus = 'ingesting' | 'indexed' | 'failed';

export interface Workspace {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentMetadata {
  author?: string;
  documentType?: string;
  accessLevel?: string;
  uploadedAt?: string;
  [key: string]: unknown;
}

export interface Document {
  id: string;
  workspaceId: string;
  name: string;
  storagePath: string;
  status: DocumentStatus;
  metadata: DocumentMetadata;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Citation {
  citation_id: string;
  document_name: string;
  page_number: number;
  exact_quote: string;
  context_snippet: string;
}

export interface Message {
  id: string;
  workspaceId: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  retrievalTrace: Record<string, unknown> | null;
  createdAt: string;
}

export interface ParsedBlock {
  pageNumber: number;
  text: string;
  bbox: {
    xMin: number;
    yMin: number;
    xMax: number;
    yMax: number;
  };
}

export interface ChunkDraft {
  pageNumber: number;
  chunkIndex: number;
  content: string;
  contextSnippet: string;
  exactQuote: string;
  metadata: Record<string, unknown>;
}

export interface RetrievedChunk {
  id: string;
  workspaceId: string;
  documentId: string;
  documentName: string;
  pageNumber: number;
  content: string;
  contextSnippet: string;
  exactQuote: string;
  metadata: Record<string, unknown>;
  denseScore: number;
  sparseScore: number;
  fusedScore: number;
  rerankScore: number;
}

export interface ChatTurnResult {
  answer: string;
  citations: Citation[];
  routeStrategy: string;
  chunksUsed: RetrievedChunk[];
}
