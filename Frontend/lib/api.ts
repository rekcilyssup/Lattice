import { Citation, Container, Document } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8080/api/v1';

type WorkspaceResponse = {
  workspace: Container;
};

type WorkspacesResponse = {
  workspaces: Container[];
};

type ChatResponse = {
  answer: string;
  citations: Citation[];
};

const parseError = async (response: Response): Promise<string> => {
  try {
    const payload = await response.json();
    // FastAPI returns { detail: string | object }; legacy shape was { error: { message } }.
    if (typeof payload?.detail === 'string') return payload.detail;
    if (Array.isArray(payload?.detail)) {
      return payload.detail.map((d: { msg?: string }) => d?.msg ?? JSON.stringify(d)).join('; ');
    }
    if (typeof payload?.detail === 'object' && payload?.detail !== null) return JSON.stringify(payload.detail);
    return payload?.error?.message ?? payload?.message ?? 'Request failed';
  } catch (_error) {
    return `Request failed with status ${response.status}`;
  }
};

export const api = {
  async listWorkspaces(): Promise<Container[]> {
    const response = await fetch(`${API_BASE}/workspaces`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = (await response.json()) as WorkspacesResponse;
    return payload.workspaces;
  },

  async getWorkspace(workspaceId: string): Promise<Container> {
    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = (await response.json()) as WorkspaceResponse;
    return payload.workspace;
  },

  async createWorkspace(name: string): Promise<Container> {
    const response = await fetch(`${API_BASE}/workspaces`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name }),
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = (await response.json()) as WorkspaceResponse;
    return payload.workspace;
  },

  async uploadDocument(workspaceId: string, file: File, metadata?: { author?: string; documentType?: string; accessLevel?: string }): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = (await response.json()) as { document: Document };
    return payload.document;
  },

  async askQuestion(workspaceId: string, query: string): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const payload = (await response.json()) as ChatResponse;
    return {
      answer: payload.answer,
      citations: payload.citations,
    };
  },
};
