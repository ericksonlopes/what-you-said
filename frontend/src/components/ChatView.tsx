import React, {useEffect, useRef, useState, type SyntheticEvent} from 'react';
import {Bot, PlayCircle, Send, User} from 'lucide-react';
import {useAppContext} from '../store/AppContext';
import {ChatMessage, Citation} from '../types';
import {api} from "@/src/services/api.ts";

// --- Mock Data ---
const MOCK_CITATIONS: Citation[] = [
  {
    id: 'cit_1',
    sourceId: 'src_1',
    title: 'Huberman Lab #102: Focus & Productivity',
    timestamp: '45:12',
    textSnippet: 'The anterior mid-cingulate cortex is highly active when you are doing something you don\'t want to do...',
    relevanceScore: 0.92
  },
  {
    id: 'cit_2',
    sourceId: 'src_2',
    title: 'Deep Work - Cal Newport (Summary)',
    textSnippet: 'To produce at your peak level you need to work for extended periods with full concentration on a single task...',
    relevanceScore: 0.85
  }
];

export function ChatView() {
  const { selectedSubjects } = useAppContext();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSendMessage = async (e: SyntheticEvent<HTMLFormElement> | React.KeyboardEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    if (!inputValue.trim() || selectedSubjects.length === 0) return;

    const userQuery = inputValue.trim();
    const newUserMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: userQuery,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, newUserMsg]);
    setInputValue('');
    setIsTyping(true);

    try {
      // 1. Fetch real context using the search API
      const subjectId = selectedSubjects[0].id; // Use first selected context for simplicity
      const searchData = await api.search(userQuery, 3, subjectId);
      
      // 2. Map citations from real search results
      const realCitations: Citation[] = searchData.results.map((res: any) => ({
        id: res.id,
        sourceId: res.content_source_id,
        title: res.external_source || 'Knowledge Source',
        timestamp: res.extra?.timestamp || '',
        textSnippet: res.content || '',
        relevanceScore: res.score || 0
      }));

      // 3. Construct a "RAG response" (Since backend doesn't have LLM yet, we summarize what we found)
      const hasResults = realCitations.length > 0;
      const aiContent = hasResults 
        ? `I found ${realCitations.length} relevant snippet(s) in your "${selectedSubjects[0].name}" knowledge base that might answer your question. You can review the specific details in the citations below.`
        : `I searched through "${selectedSubjects[0].name}" but couldn't find any specific information that matches your query. Try adding more data or rephrasing your question.`;

      const newAiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: aiContent,
        citations: realCitations,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, newAiMsg]);
    } catch (err) {
      console.error('Chat error:', err);
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I encountered an error while searching your knowledge base. Please check if the backend is running.",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  if (selectedSubjects.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8">
        <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center mb-6 group hover:border-zinc-600 transition-colors cursor-default">
          <Bot className="w-8 h-8 text-zinc-500 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-12" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">No Context Selected</h2>
        <p className="text-zinc-400 max-w-md">
          Please select one or more Knowledge Bases from the sidebar to start chatting with your data.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col relative">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 custom-scrollbar pb-32">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-70">
            <Bot className="w-12 h-12 text-emerald-500/50 mb-4 animate-pulse" />
            <h3 className="text-lg font-medium text-zinc-200">How can I help you today?</h3>
            <p className="text-sm text-zinc-500 mt-2 max-w-md">
              Ask me anything about the {selectedSubjects.length} selected knowledge bases. I will search through the transcripts and documents to find the exact answers.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
                msg.role === 'user' ? 'bg-zinc-800 border border-zinc-700' : 'bg-emerald-500/20 border border-emerald-500/30'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-zinc-300" /> : <Bot className="w-4 h-4 text-emerald-400" />}
              </div>

              {/* Message Content */}
              <div className={`flex flex-col gap-2 min-w-0 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-zinc-800 text-zinc-100 rounded-tr-sm' 
                    : 'bg-transparent text-zinc-200'
                }`}>
                  {msg.content}
                </div>

                {/* Citations (Only for AI) */}
                {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {msg.citations.map((cit, idx) => (
                      <button 
                        key={cit.id}
                        className="group flex flex-col gap-1.5 p-3 rounded-xl bg-zinc-900/50 border border-zinc-800 hover:border-emerald-500/30 hover:bg-zinc-800/80 transition-all text-left max-w-[280px]"
                        onClick={() => alert(`Showing source: ${cit.title}\n\nSnippet: "${cit.textSnippet}"`)}
                      >
                        <div className="flex items-center gap-2 text-xs font-medium text-zinc-300 group-hover:text-emerald-400 transition-colors">
                          <span className="flex items-center justify-center w-4 h-4 rounded-full bg-zinc-800 text-[10px] text-zinc-400 group-hover:bg-emerald-500/20 group-hover:text-emerald-500">
                            {idx + 1}
                          </span>
                          <span className="truncate">{cit.title}</span>
                        </div>
                        {cit.timestamp && (
                          <div className="flex items-center gap-1.5 text-[11px] text-emerald-500/70 font-mono bg-emerald-500/10 px-1.5 py-0.5 rounded w-fit">
                            <PlayCircle className="w-3 h-3" />
                            {cit.timestamp}
                          </div>
                        )}
                        <p className="text-[11px] text-zinc-500 line-clamp-2 mt-1 leading-relaxed">
                          "{cit.textSnippet}"
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex gap-4 max-w-4xl mx-auto">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0 mt-1">
              <Bot className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="px-5 py-4 rounded-2xl bg-transparent flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-bg-dark via-bg-dark to-transparent">
        <div className="max-w-4xl mx-auto relative">
          <form 
            onSubmit={handleSendMessage}
            className="relative flex items-end gap-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-2 shadow-2xl focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/20 transition-all"
          >
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder={`Ask anything about ${selectedSubjects.length} selected context${selectedSubjects.length > 1 ? 's' : ''}...`}
              className="w-full max-h-32 min-h-[44px] bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 resize-none focus:outline-none py-3 px-3 custom-scrollbar"
              rows={1}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isTyping}
              className="group p-3 rounded-xl bg-emerald-500 text-black hover:bg-emerald-400 disabled:opacity-50 disabled:hover:bg-emerald-500 transition-colors flex-shrink-0 mb-0.5"
            >
              <Send className="w-4 h-4 transition-transform duration-200 group-hover:scale-110 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </button>
          </form>
          <div className="text-center mt-2">
            <span className="text-[10px] text-zinc-600">
              AI can make mistakes. Verify important information using the provided citations.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
