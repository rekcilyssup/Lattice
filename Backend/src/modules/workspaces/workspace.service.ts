import { v4 as uuid } from 'uuid';
import { AppError } from '../../shared/errors.js';
import type { Document, Message, Workspace } from '../../shared/types.js';
import { DocumentRepository } from '../documents/document.repository.js';
import { ChatRepository } from '../chat/chat.repository.js';
import { WorkspaceRepository } from './workspace.repository.js';

interface WorkspaceAggregate {
  id: string;
  name: string;
  documents: Document[];
  messages: Message[];
}

export class WorkspaceService {
  constructor(
    private readonly workspaceRepository: WorkspaceRepository,
    private readonly documentRepository: DocumentRepository,
    private readonly chatRepository: ChatRepository,
  ) {}

  async createWorkspace(name: string): Promise<WorkspaceAggregate> {
    const workspaceId = uuid();
    const workspace = await this.workspaceRepository.create(workspaceId, name);

    await this.chatRepository.createMessage({
      id: uuid(),
      workspaceId: workspace.id,
      role: 'assistant',
      content: `Workspace created. Upload documents to start grounded Q&A in "${workspace.name}".`,
      citations: [],
      retrievalTrace: null,
    });

    return {
      id: workspace.id,
      name: workspace.name,
      documents: [],
      messages: await this.chatRepository.listMessagesByWorkspace(workspace.id),
    };
  }

  async getWorkspace(workspaceId: string): Promise<WorkspaceAggregate> {
    const workspace = await this.workspaceRepository.findById(workspaceId);
    if (!workspace) {
      throw new AppError('Workspace not found', 404, 'WORKSPACE_NOT_FOUND');
    }

    const [documents, messages] = await Promise.all([
      this.documentRepository.listByWorkspace(workspaceId),
      this.chatRepository.listMessagesByWorkspace(workspaceId),
    ]);

    return {
      id: workspace.id,
      name: workspace.name,
      documents,
      messages,
    };
  }

  async listWorkspaces(): Promise<WorkspaceAggregate[]> {
    const workspaces = await this.workspaceRepository.list();

    if (workspaces.length === 0) {
      return [];
    }

    const aggregates = await Promise.all(workspaces.map((workspace) => this.getWorkspace(workspace.id)));
    return aggregates;
  }

  async ensureWorkspaceExists(workspaceId: string): Promise<Workspace> {
    const workspace = await this.workspaceRepository.findById(workspaceId);
    if (!workspace) {
      throw new AppError('Workspace not found', 404, 'WORKSPACE_NOT_FOUND');
    }
    return workspace;
  }
}
