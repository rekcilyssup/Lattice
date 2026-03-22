'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { ChatArea } from '@/components/ChatArea';
import { RightSidebar } from '@/components/RightSidebar';
import { api } from '@/lib/api';
import { Citation, Container, Message } from '@/lib/types';

export default function Page() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [activeContainerId, setActiveContainerId] = useState<string>('');
  const [isLeftSidebarCollapsed, setIsLeftSidebarCollapsed] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);

  const replaceWorkspace = (workspace: Container) => {
    setContainers((prev) => {
      const exists = prev.some((item) => item.id === workspace.id);
      if (!exists) {
        return [...prev, workspace];
      }

      return prev.map((item) => (item.id === workspace.id ? workspace : item));
    });
  };

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const workspaces = await api.listWorkspaces();

      if (workspaces.length === 0) {
        const defaultWorkspace = await api.createWorkspace('Default Workspace');
        setContainers([defaultWorkspace]);
        setActiveContainerId(defaultWorkspace.id);
      } else {
        setContainers(workspaces);
        setActiveContainerId((previous) => previous || workspaces[0].id);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (!activeContainerId) return;

    const timer = setInterval(async () => {
      try {
        const workspace = await api.getWorkspace(activeContainerId);
        replaceWorkspace(workspace);
      } catch (_error) {
        // Ignore transient polling errors.
      }
    }, 4000);

    return () => clearInterval(timer);
  }, [activeContainerId]);

  const handleCreateContainer = async () => {
    try {
      const workspace = await api.createWorkspace(`New Workspace ${containers.length + 1}`);
      setContainers((prev) => [...prev, workspace]);
      setActiveContainerId(workspace.id);
    } catch (error) {
      console.error(error);
    }
  };

  const handleUpdateMessages = (containerId: string, updater: (prev: Message[]) => Message[]) => {
    setContainers((prev) => prev.map((container) => (container.id === containerId ? { ...container, messages: updater(container.messages) } : container)));
  };

  const handleSendMessage = async (workspaceId: string, query: string) => {
    const response = await api.askQuestion(workspaceId, query);
    return response;
  };

  const handleUploadDocument = async (workspaceId: string, file: File) => {
    setIsUploading(true);
    try {
      await api.uploadDocument(workspaceId, file);
      const workspace = await api.getWorkspace(workspaceId);
      replaceWorkspace(workspace);
    } catch (error) {
      console.error(error);
      alert(error instanceof Error ? error.message : 'Document upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const activeContainer = containers.find((container) => container.id === activeContainerId);

  return (
    <div className="flex h-screen w-full bg-zinc-50 overflow-hidden">
      <Sidebar
        isCollapsed={isLeftSidebarCollapsed}
        onToggle={() => setIsLeftSidebarCollapsed(!isLeftSidebarCollapsed)}
        containers={containers}
        activeContainerId={activeContainerId}
        onSelectContainer={setActiveContainerId}
        onCreateContainer={handleCreateContainer}
        onUploadDocument={(file) => {
          if (!activeContainerId) return;
          void handleUploadDocument(activeContainerId, file);
        }}
        isUploading={isUploading}
      />
      <main className="flex-1 flex flex-col min-w-0 bg-white shadow-sm z-10">
        {isLoading && <div className="p-6 text-sm text-zinc-500">Loading workspace...</div>}

        {!isLoading && activeContainer && (
          <ChatArea
            key={activeContainer.id}
            messages={activeContainer.messages}
            onUpdateMessages={(updater) => handleUpdateMessages(activeContainer.id, updater)}
            onCitationClick={(citation) => setSelectedCitation(citation)}
            onSendMessage={(query) => handleSendMessage(activeContainer.id, query)}
          />
        )}
      </main>
      {selectedCitation && <RightSidebar citation={selectedCitation} onClose={() => setSelectedCitation(null)} />}
    </div>
  );
}
