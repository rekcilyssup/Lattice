import { ExternalLink, FileText, Quote } from 'lucide-react';
import { Citation } from '@/lib/types';

export function CitationCard({ citation, onClick }: { citation: Citation; onClick?: () => void }) {
  // Highlight the exact quote within the context snippet
  const renderContext = () => {
    const parts = citation.context_snippet.split(citation.exact_quote);
    if (parts.length === 1) return <span className="italic text-zinc-500">{citation.context_snippet}</span>;
    
    return (
      <span className="italic text-zinc-500 leading-relaxed">
        {parts[0]}
        <strong className="font-semibold text-zinc-900 not-italic bg-yellow-100/80 px-1 py-0.5 mx-0.5 rounded border border-yellow-200/50 shadow-sm">{citation.exact_quote}</strong>
        {parts[1]}
      </span>
    );
  };

  return (
    <div onClick={onClick} className="group relative bg-white border border-zinc-200 rounded-lg p-4 shadow-sm hover:shadow-md hover:border-zinc-300 transition-all cursor-pointer">
      {/* Header: Document & Page */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-1 bg-zinc-100 border border-zinc-200 rounded text-xs font-mono text-zinc-700">
            <FileText className="w-3 h-3" />
            <span className="truncate max-w-[200px]">{citation.document_name}</span>
          </div>
          <div className="px-2 py-1 bg-zinc-800 text-zinc-100 rounded text-[10px] font-mono uppercase tracking-wider">
            Page {citation.page_number}
          </div>
        </div>
        
        <button className="p-1.5 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 rounded-md transition-colors opacity-0 group-hover:opacity-100" title="View Source Document">
          <ExternalLink className="w-4 h-4" />
        </button>
      </div>

      {/* Content: Quote & Context */}
      <div className="relative pl-4 border-l-2 border-zinc-300">
        <Quote className="absolute -left-2 -top-1 w-4 h-4 text-zinc-300 bg-white" />
        <p className="text-sm">
          {renderContext()}
        </p>
      </div>
      
      {/* Footer: Citation ID */}
      <div className="mt-3 pt-3 border-t border-zinc-100 flex justify-end">
        <span className="text-[10px] text-zinc-400 font-mono">
          REF_ID: {citation.citation_id.padStart(4, '0')}
        </span>
      </div>
    </div>
  );
}
