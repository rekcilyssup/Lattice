'use client';

import { useRef } from 'react';
import { FileText, UploadCloud, CheckCircle2, Loader2, Database, ChevronLeft, ChevronRight, Plus, FolderKanban, AlertCircle } from 'lucide-react';
import { Container } from '@/lib/types';

export function Sidebar({ 
  isCollapsed, 
  onToggle,
  containers,
  activeContainerId,
  onSelectContainer,
  onCreateContainer,
  onUploadDocument,
  isUploading = false,
}: { 
  isCollapsed: boolean; 
  onToggle: () => void;
  containers: Container[];
  activeContainerId: string;
  onSelectContainer: (id: string) => void;
  onCreateContainer: () => void;
  onUploadDocument: (file: File) => void;
  isUploading?: boolean;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeContainer = containers.find(c => c.id === activeContainerId);

  return (
    <div className={`relative flex-shrink-0 transition-all duration-300 ease-in-out ${isCollapsed ? 'w-0' : 'w-72'} bg-zinc-50 border-r border-zinc-200 h-full z-20`}>
      <aside className={`w-72 h-full overflow-hidden flex flex-col transition-opacity duration-300 ${isCollapsed ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
        <div className="p-4 border-b border-zinc-200 flex items-center gap-2">
          <Database className="w-5 h-5 text-zinc-700" />
          <h1 className="font-semibold text-sm tracking-tight text-zinc-900">RAG Index Manager</h1>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-8">
          
          {/* Workspaces Section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Workspaces</h2>
              <button onClick={onCreateContainer} className="p-1 hover:bg-zinc-200 rounded text-zinc-500 hover:text-zinc-900 transition-colors" title="New Workspace">
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-1">
              {containers.map(c => (
                <button
                  key={c.id}
                  onClick={() => onSelectContainer(c.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                    c.id === activeContainerId 
                      ? 'bg-zinc-200 text-zinc-900 font-medium' 
                      : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'
                  }`}
                >
                  <FolderKanban className="w-4 h-4" />
                  <span className="truncate">{c.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Active Documents Section */}
          <div>
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Active Documents</h2>
            
            <div className="space-y-2">
              {!activeContainer?.documents.length && (
                <div className="text-sm text-zinc-500 italic px-2">No documents uploaded.</div>
              )}
              {activeContainer?.documents.map(doc => (
                <div key={doc.id} className="flex items-start gap-3 p-3 bg-white border border-zinc-200 rounded-md shadow-sm">
                  <FileText className="w-4 h-4 text-zinc-400 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-zinc-900 truncate">{doc.name}</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      {doc.status === 'indexed' ? (
                        <>
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                          <span className="text-xs text-zinc-500 font-mono">Indexed</span>
                        </>
                      ) : doc.status === 'failed' ? (
                        <>
                          <AlertCircle className="w-3 h-3 text-red-500" />
                          <span className="text-xs text-red-500 font-mono">Indexing failed</span>
                        </>
                      ) : (
                        <>
                          <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
                          <span className="text-xs text-zinc-500 font-mono">Ingesting...</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Upload New */}
          <div>
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Upload New</h2>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  onUploadDocument(file);
                }
                event.target.value = '';
              }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="w-full flex flex-col items-center justify-center gap-2 p-6 border-2 border-dashed border-zinc-300 rounded-lg hover:border-zinc-400 hover:bg-zinc-100/50 transition-colors disabled:opacity-60"
            >
              <UploadCloud className="w-6 h-6 text-zinc-400" />
              <span className="text-sm font-medium text-zinc-600">{isUploading ? 'Uploading PDF...' : 'Drop PDF here'}</span>
              <span className="text-xs text-zinc-400">{isUploading ? 'Please wait' : 'or click to browse'}</span>
            </button>
          </div>
        </div>
        
        <div className="p-4 border-t border-zinc-200 bg-zinc-100/50">
          <div className="flex items-center justify-between text-xs font-mono text-zinc-500">
            <span>Index Status</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Online</span>
          </div>
        </div>
      </aside>
      
      <button
        onClick={onToggle}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-12 bg-white border border-zinc-200 rounded-r-md shadow-sm flex items-center justify-center hover:bg-zinc-50 text-zinc-500 hover:text-zinc-900 z-30"
        title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
      >
        {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </div>
  );
}
