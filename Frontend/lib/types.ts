export type Citation = {
  citation_id: string;
  document_name: string;
  page_number: number;
  exact_quote: string;
  context_snippet: string;
};

export type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  isSearching?: boolean;
  citations?: Citation[];
};

export type DocumentStatus = 'indexed' | 'ingesting' | 'failed';

export type Document = {
  id: string;
  name: string;
  status: DocumentStatus;
  progress?: number;
};

export type Container = {
  id: string;
  name: string;
  documents: Document[];
  messages: Message[];
};
