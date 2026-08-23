import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Loader2, Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function AgentPanel({ ticker, onAction }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const API_URL = import.meta.env.VITE_API_URL ?? '';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset messages when ticker changes
  useEffect(() => {
    setMessages([]);
  }, [ticker]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      // Build context-aware messages
      const apiMessages = [
        ...messages.map(m => ({ role: m.role, content: m.content })),
        { role: 'user', content: `[Context: User is viewing stock ${ticker}]\n\n${userMsg}` }
      ];

      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: apiMessages,
          user_id: '00000000-0000-0000-0000-000000000000'
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        
        // Handle session ID injection
        if (chunk.startsWith('__session_id__:')) {
          const lines = chunk.split('\n\n');
          if (lines.length > 1 && lines.slice(1).join('').trim()) {
            assistantMessage += lines.slice(1).join('\n\n');
          }
          continue;
        }
        
        assistantMessage += chunk;
        setMessages(prev => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg?.role === 'assistant') {
            lastMsg.content = assistantMessage;
          } else {
            updated.push({ role: 'assistant', content: assistantMessage });
          }
          return [...updated];
        });
      }

      // Parse UI actions from response
      parseActions(assistantMessage);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const parseActions = (text) => {
    // Look for action commands in the response
    const tickerMatch = text.match(/\[ACTION:CHANGE_TICKER:(\w+)\]/);
    if (tickerMatch && onAction) {
      onAction({ type: 'change_ticker', value: tickerMatch[1] });
    }
    
    const indicatorMatch = text.match(/\[ACTION:ADD_INDICATOR:(\w+)\]/);
    if (indicatorMatch && onAction) {
      onAction({ type: 'add_indicator', value: indicatorMatch[1] });
    }

    const analysisMatch = text.match(/\[ACTION:RUN_ANALYSIS:(\w+)\]/);
    if (analysisMatch && onAction) {
      onAction({ type: 'run_analysis', value: analysisMatch[1] });
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-br from-primary to-primary-hover rounded-full shadow-lg shadow-primary/30 flex items-center justify-center text-white hover:scale-110 transition-transform z-50"
      >
        <MessageCircle size={24} />
      </button>
    );
  }

  return (
    <div className="fixed right-0 top-14 bottom-0 w-96 bg-dark-sidebar border-l border-dark-border flex flex-col z-50 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border bg-dark-card">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-primary to-stock-green rounded-lg flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">AI Agent</h3>
            <p className="text-[10px] text-text-muted">Viewing {ticker}</p>
          </div>
        </div>
        <button onClick={() => setIsOpen(false)} className="text-text-muted hover:text-white transition-colors">
          <X size={18} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Bot size={32} className="mx-auto text-text-muted mb-3" />
            <p className="text-text-muted text-sm">Ask me about <span className="text-primary font-semibold">{ticker}</span></p>
            <div className="mt-4 space-y-2">
              {[`Phân tích ${ticker}`, `Tin tức mới nhất`, `Hỗ trợ kháng cự`].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(suggestion); }}
                  className="block w-full text-left px-3 py-2 text-xs text-text-secondary bg-dark-bg rounded-lg hover:bg-dark-hover transition-colors border border-dark-border"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-1">
                <Bot size={14} className="text-primary" />
              </div>
            )}
            <div className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${
              msg.role === 'user' 
                ? 'bg-primary text-white rounded-br-sm' 
                : 'bg-dark-bg border border-dark-border text-text-primary rounded-bl-sm'
            }`}>
              {msg.role === 'assistant' ? (
                <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              ) : msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="w-6 h-6 rounded-full bg-stock-green/20 flex items-center justify-center flex-shrink-0 mt-1">
                <User size={14} className="text-stock-green" />
              </div>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Bot size={14} className="text-primary" />
            </div>
            <div className="px-3 py-2 bg-dark-bg border border-dark-border rounded-xl rounded-bl-sm">
              <Loader2 size={16} className="animate-spin text-primary" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-dark-border bg-dark-card">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={`Ask about ${ticker}...`}
            className="flex-1 bg-dark-bg border border-dark-border text-white text-sm rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary focus:border-primary placeholder-text-muted"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-3 py-2.5 bg-primary hover:bg-primary-hover text-white rounded-xl transition-colors disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
