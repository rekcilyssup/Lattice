import { X, FileText } from 'lucide-react';
import { Citation } from '@/lib/types';

export function RightSidebar({ citation, onClose }: { citation: Citation | null; onClose: () => void }) {
  if (!citation) return null;

  const sourceSnippet = citation.context_snippet;

  const renderHighlightedText = () => {
    const parts = sourceSnippet.split(citation.exact_quote);
    if (parts.length === 1) return <span className="text-zinc-700 whitespace-pre-wrap">{sourceSnippet}</span>;

    return (
      <span className="text-zinc-700 whitespace-pre-wrap leading-relaxed">
        {parts[0]}
        <strong className="font-semibold text-zinc-900 not-italic bg-yellow-100/80 px-1 py-0.5 mx-0.5 rounded border border-yellow-200/50 shadow-sm">{citation.exact_quote}</strong>
        {parts.slice(1).join(citation.exact_quote)}
      </span>
    );
  };

  return (
    <aside className="w-[400px] flex-shrink-0 flex flex-col bg-white border-l border-zinc-200 h-full shadow-2xl z-20 animate-in slide-in-from-right-8 duration-300">
      <div className="h-14 px-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50 flex-shrink-0">
        <div className="flex items-center gap-2 overflow-hidden">
          <FileText className="w-4 h-4 text-zinc-500 flex-shrink-0" />
          <span className="text-sm font-medium text-zinc-800 truncate">{citation.document_name}</span>
          <span className="px-2 py-0.5 bg-zinc-200 text-zinc-700 rounded text-[10px] font-mono uppercase tracking-wider flex-shrink-0">
            Page {citation.page_number}
          </span>
        </div>
        <button onClick={onClose} className="p-1.5 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-200 rounded-md transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-6 bg-zinc-100/50">
        <div className="bg-white border border-zinc-200 shadow-sm rounded-sm p-8 min-h-full">
          <div className="text-xs font-mono text-zinc-400 mb-8 pb-4 border-b border-zinc-100 flex justify-between">
            <span>SOURCE DOCUMENT VIEW</span>
            <span>PAGE {citation.page_number}</span>
          </div>
          <div className="text-sm font-serif">
            {renderHighlightedText()}
          </div>
        </div>
      </div>
    </aside>
  );
}
