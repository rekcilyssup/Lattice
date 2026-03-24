'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Search, User, Bot, FileSearch } from 'lucide-react';
import { CitationCard } from './CitationCard';
import { Citation, Message } from '@/lib/types';

export function ChatArea({
  messages,
  onUpdateMessages,
  onCitationClick,
  onSendMessage,
}: {
  messages: Message[];
  onUpdateMessages: (updater: (prev: Message[]) => Message[]) => void;
  onCitationClick?: (citation: Citation) => void;
  onSendMessage: (query: string) => Promise<{ answer: string; citations: Citation[] }>;
}) {
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userQuery = input.trim();
    setInput('');
    setIsProcessing(true);

    const userMsgId = Date.now().toString();
    onUpdateMessages((prev) => [...prev, { id: userMsgId, role: 'user', content: userQuery }]);

    const assistantMsgId = (Date.now() + 1).toString();
    onUpdateMessages((prev) => [
      ...prev,
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        isSearching: true,
      },
    ]);

    try {
      const response = await onSendMessage(userQuery);

      onUpdateMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                isSearching: false,
                content: response.answer,
                citations: response.citations,
              }
            : msg,
        ),
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to get response from backend';

      onUpdateMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                isSearching: false,
                content: `Error: ${message}`,
                citations: [],
              }
            : msg,
        ),
      );
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="h-14 flex items-center px-6 border-b border-zinc-200 bg-white flex-shrink-0">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-zinc-400" />
          <h2 className="text-sm font-medium text-zinc-800">Hybrid Search & Retrieval</h2>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-md bg-zinc-900 flex items-center justify-center flex-shrink-0 mt-1">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}

            <div className={`flex flex-col gap-2 max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div
                className={`px-4 py-3 rounded-lg text-sm leading-relaxed ${
                  msg.role === 'user' ? 'bg-zinc-900 text-white' : 'bg-zinc-100 text-zinc-900 border border-zinc-200'
                }`}
              >
                {msg.isSearching ? (
                  <div className="flex items-center gap-2 text-zinc-500 font-mono text-xs">
                    <FileSearch className="w-4 h-4 animate-pulse" />
                    <span>Searching hybrid index...</span>
                  </div>
                ) : (
                  <p>{msg.content}</p>
                )}

              </div>

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-4 w-full">
                  <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="h-px bg-zinc-200 flex-1"></div>
                    <span>Provable Provenance</span>
                    <div className="h-px bg-zinc-200 flex-1"></div>
                  </div>
                  <div className="grid grid-cols-1 gap-3">
                    {msg.citations.map((citation) => (
                      <CitationCard key={citation.citation_id} citation={citation} onClick={() => onCitationClick?.(citation)} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-md bg-zinc-200 flex items-center justify-center flex-shrink-0 mt-1">
                <User className="w-5 h-5 text-zinc-600" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-zinc-200">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Query the document index..."
              disabled={isProcessing}
              className="w-full pl-4 pr-12 py-3 bg-zinc-50 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent disabled:opacity-50 transition-shadow"
            />
            <button
              type="submit"
              disabled={!input.trim() || isProcessing}
              className="absolute right-2 p-1.5 bg-zinc-900 text-white rounded-md hover:bg-zinc-800 disabled:opacity-50 disabled:hover:bg-zinc-900 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="mt-2 text-center">
            <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Strict Retrieval Mode Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
