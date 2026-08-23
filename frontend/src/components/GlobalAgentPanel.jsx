import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Loader2, Bot, User, Maximize2, Minimize2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAgent } from '../contexts/AgentContext';

export default function GlobalAgentPanel() {
  const { isAgentOpen, toggleAgent, messages, setMessages, addMessage } = useAgent();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();
  const API_URL = import.meta.env.VITE_API_URL ?? '';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Determine context based on current route
  const getContextString = () => {
    if (location.pathname.startsWith('/stock/')) {
      const ticker = location.pathname.split('/')[2];
      return `User is viewing stock detail for ${ticker.toUpperCase()}`;
    } else if (location.pathname === '/portfolio') {
      return `User is viewing their Portfolio and Watchlist.`;
    } else if (location.pathname === '/today') {
      return `User is viewing the Today Dashboard (Market Overview).`;
    } else if (location.pathname === '/screeners') {
      return `User is viewing Stock Screeners.`;
    } else if (location.pathname === '/chart') {
      return `User is viewing the global TradingView Chart.`;
    }
    return `User is at route: ${location.pathname}`;
  };

  const currentTicker = location.pathname.startsWith('/stock/') ? location.pathname.split('/')[2].toUpperCase() : null;

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg = input.trim();
    setInput('');
    addMessage({ role: 'user', content: userMsg });
    setLoading(true);

    try {
      const contextString = getContextString();
      // Only attach context silently to the prompt, not to the UI history
      const apiMessages = [
        ...messages.map(m => ({ role: m.role, content: m.content })),
        { role: 'user', content: `[Context: ${contextString}]\n\n${userMsg}` }
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

      parseActions(assistantMessage);
    } catch (err) {
      addMessage({ role: 'assistant', content: `Error: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  const parseActions = (text) => {
    // Action definitions:
    // [ACTION:CHANGE_TICKER:AAPL] -> Navigate to /stock/AAPL
    // [ACTION:NAVIGATE:PORTFOLIO] -> Navigate to /portfolio
    
    const tickerMatch = text.match(/\[ACTION:CHANGE_TICKER:(\w+)\]/);
    if (tickerMatch) {
      navigate(`/stock/${tickerMatch[1].toUpperCase()}`);
    }
    
    const navMatch = text.match(/\[ACTION:NAVIGATE:(\w+)\]/);
    if (navMatch) {
      const page = navMatch[1].toLowerCase();
      navigate(`/${page}`);
    }
    
    // We can handle more global actions here in the future
  };

  if (!isAgentOpen) return null;

  return (
    <div className="w-[400px] border-l border-dark-border bg-dark-sidebar flex flex-col shadow-2xl relative z-40 transition-all duration-300 h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border bg-dark-card shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-primary to-stock-green rounded-lg flex items-center justify-center shadow-lg shadow-primary/20">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">Alphahubiq Copilot</h3>
            <p className="text-[10px] text-stock-green uppercase font-semibold">
              {currentTicker ? `Làm việc với ${currentTicker}` : 'Trợ lý toàn cầu'}
            </p>
          </div>
        </div>
        <button onClick={toggleAgent} className="text-text-muted hover:text-white transition-colors bg-dark-bg p-1.5 rounded-md border border-dark-border hover:border-text-muted">
          <Minimize2 size={16} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-dark-bg rounded-full flex items-center justify-center mx-auto mb-4 border border-dark-border">
              <Bot size={32} className="text-primary" />
            </div>
            <h3 className="text-white font-bold mb-2">Tôi có thể giúp gì cho bạn?</h3>
            <p className="text-text-secondary text-sm px-4">Ra lệnh điều hướng web, hỏi thông tin tài chính, hoặc phân tích kỹ thuật ngay tại đây.</p>
            
            <div className="mt-6 space-y-2">
              {[
                `Mở trang danh mục đầu tư`, 
                `Phân tích mã NVDA`, 
                `Thị trường hôm nay thế nào?`
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(suggestion); }}
                  className="block w-full text-left px-4 py-3 text-sm text-text-primary bg-dark-bg rounded-lg hover:bg-dark-hover transition-colors border border-dark-border hover:border-primary/50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-dark-border' : 'bg-primary/20 text-primary'}`}>
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={`p-3 rounded-2xl max-w-[85%] text-sm ${msg.role === 'user' ? 'bg-dark-border text-white rounded-tr-none' : 'bg-[#1e293b] text-text-primary rounded-tl-none border border-dark-border'}`}>
              {msg.role === 'assistant' ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content.replace(/\[ACTION:.*?\]/g, '')}</ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0">
              <Bot size={16} />
            </div>
            <div className="p-3 rounded-2xl bg-[#1e293b] text-text-secondary rounded-tl-none flex items-center gap-2 border border-dark-border">
              <Loader2 size={14} className="animate-spin text-primary" /> Đang suy nghĩ...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-dark-card border-t border-dark-border shrink-0">
        <div className="flex items-center bg-dark-bg rounded-xl border border-dark-border focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all p-1">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Gõ lệnh hoặc câu hỏi..."
            className="flex-1 bg-transparent px-3 py-2 text-white text-sm focus:outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white disabled:opacity-50 disabled:bg-dark-border transition-colors m-1 hover:bg-primary-hover"
          >
            <Send size={14} className="ml-1" />
          </button>
        </div>
      </div>
    </div>
  );
}
