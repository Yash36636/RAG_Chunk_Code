'use client';

import { useState, useRef, useEffect } from 'react';
import {
  ProductWisdomHeader,
  HighlightBadge,
  HeroTitle,
  SearchInput,
  SuggestionChip,
  ChatInput,
} from '@/components';
import AnswerPanel from '@/components/AnswerPanel';
import CitationSidebar from '@/components/CitationSidebar';
import ConfidenceBadge from '@/components/ConfidenceBadge';
import LowConfidenceWarning from '@/components/LowConfidenceWarning';
import SafetyMessage from '@/components/SafetyMessage';
import ConversationBubble from '@/components/ConversationBubble';
import { fetchAnswer, generateSessionId, clearSession, QueryResponse } from '@/data/mockData';
import { RotateCcw } from 'lucide-react';

const suggestions = [
  'How to prioritize features?',
  'What makes a great product manager?',
  'How should I think about pricing?',
  'How do you build a growth loop?',
];

// Chat message type for stacking
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: QueryResponse;
  timestamp: number;
}

export default function Home() {
  // Session ID persists for the entire conversation
  const sessionIdRef = useRef<string>(generateSessionId());
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);
    
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const result = await fetchAnswer(query, sessionIdRef.current);
      
      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: result.answer.direct_answer,
        response: result,
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, assistantMessage]);
      
    } catch (err) {
      console.error('Query failed:', err);
      setError('Failed to connect. Please ensure the backend is running.');
      // Remove the user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleNewConversation = async () => {
    await clearSession(sessionIdRef.current);
    sessionIdRef.current = generateSessionId();
    setMessages([]);
    setError(null);
    setActiveSourceId(null);
  };

  const handleSourceHighlight = (sourceId: string) => {
    setActiveSourceId(sourceId);
    // Auto-clear highlight after animation
    setTimeout(() => setActiveSourceId(null), 1500);
  };

  const hasMessages = messages.length > 0;
  const lastResponse = messages.filter(m => m.response).pop()?.response;

  return (
    <div className="chat-container">
      <ProductWisdomHeader />

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-4">
          {!hasMessages && !isLoading && !error ? (
            /* HERO STATE */
            <div className="flex flex-col items-center justify-center min-h-[60vh] gap-8 animate-slide-up">
              <HighlightBadge text="Powered by Lenny's Podcast transcripts" />
              <HeroTitle />
              <p className="text-muted-foreground text-center max-w-lg font-sans">
                Get answers from 100+ hours of conversations with top product leaders
              </p>
              <SearchInput 
                onSubmit={handleSearch} 
                isLoading={isLoading}
              />
              <div className="flex flex-wrap justify-center gap-3 mt-2">
                {suggestions.map((suggestion, index) => (
                  <div
                    key={suggestion}
                    className="animate-fade-in"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <SuggestionChip
                      text={suggestion}
                      onClick={handleSearch}
                      disabled={isLoading}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* CHAT STATE - Message stacking like ChatGPT */
            <div className="flex gap-8 pt-8 pb-24">
              {/* LEFT: Chat messages */}
              <div className="flex-1 min-w-0 space-y-6">
                {/* Session controls */}
                {messages.length > 2 && (
                  <div className="flex items-center justify-between mb-4 animate-fade-in">
                    <span className="text-xs text-muted-foreground">
                      {messages.length} messages in conversation
                    </span>
                    <button
                      onClick={handleNewConversation}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground bg-card/50 hover:bg-card rounded-full transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      New conversation
                    </button>
                  </div>
                )}

                {/* Message stack */}
                {messages.map((message, index) => (
                  <div key={message.id} className="animate-fade-in">
                    {message.role === 'user' ? (
                      /* User message */
                      <div className="flex justify-end mb-4">
                        <div className="message-user">
                          <p className="text-foreground text-[15px] leading-relaxed font-sans">
                            {message.content}
                          </p>
                        </div>
                      </div>
                    ) : (
                      /* Assistant message */
                      <div className="space-y-4">
                        {message.response?.safety_refusal || message.response?.mode === 'safety' ? (
                          <SafetyMessage message={message.content} />
                        ) : message.response?.mode === 'conversation' ? (
                          <>
                            <LowConfidenceWarning visible={message.response.confidence === 'low'} />
                            <ConversationBubble message={message.content} />
                          </>
                        ) : (
                          /* RAG mode */
                          <>
                            {/* Confidence badge */}
                            <div className="flex items-center justify-between">
                              <ConfidenceBadge confidence={message.response?.confidence || 'medium'} />
                              <span className="text-xs text-muted-foreground">
                                {message.response?.latency_ms}ms · {message.response?.sources.length} sources
                              </span>
                            </div>
                            
                            <LowConfidenceWarning visible={message.response?.confidence === 'low'} />
                            
                            <AnswerPanel
                              answer={message.response!.answer}
                              confidence={message.response!.confidence}
                              latencyMs={message.response!.latency_ms}
                              onCopy={() => handleCopy(message.content)}
                              onRegenerate={() => {}}
                              onSourceClick={handleSourceHighlight}
                            />
                          </>
                        )}
                        
                        {/* Smart follow-ups from backend */}
                        {message.response?.followups && message.response.followups.length > 0 && (
                          <div className="flex flex-wrap gap-2 pt-2">
                            {message.response.followups.map((followup, i) => (
                              <button
                                key={i}
                                onClick={() => handleSearch(followup)}
                                disabled={isLoading}
                                className="px-3 py-1.5 text-xs text-left text-muted-foreground hover:text-foreground bg-card/50 hover:bg-card border border-border/50 hover:border-primary/30 rounded-full transition-all disabled:opacity-50"
                              >
                                {followup}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex items-center gap-3 text-muted-foreground animate-fade-in">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm font-sans">Thinking...</span>
                  </div>
                )}

                {/* Error */}
                {error && (
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 animate-fade-in">
                    {error}
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* RIGHT: Citation Sidebar (sticky) - shows sources from last RAG response */}
              {lastResponse?.mode === 'rag' && lastResponse.sources.length > 0 && (
                <div className="w-[260px] flex-shrink-0 hidden lg:block">
                  <CitationSidebar 
                    sources={lastResponse.sources} 
                    activeSourceId={activeSourceId}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Chat input - always visible after first message */}
      {hasMessages && (
        <div className="flex-shrink-0 p-4 pb-8 animate-slide-up">
          <ChatInput
            onSend={handleSearch}
            isLoading={isLoading}
            placeholder="Ask a follow-up question..."
          />
        </div>
      )}
    </div>
  );
}
