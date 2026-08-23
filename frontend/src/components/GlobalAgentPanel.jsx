import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Loader2, Bot, User, Maximize2, Minimize2, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAgent } from '../contexts/AgentContext';

export default function GlobalAgentPanel() {
  const { isAgentOpen, toggleAgent, messages, setMessages, addMessage, clearMessages } = useAgent();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
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
    <div className={`fixed right-0 top-14 bottom-0 ${isExpanded ? 'w-[600px]' : 'w-[400px]'} border-l border-white/5 bg-[#0B0E14]/95 backdrop-blur-2xl flex flex-col shadow-[-20px_0_40px_-15px_rgba(0,0,0,0.7)] z-50 transition-all duration-300`}>
      
      {/* Sleek Top Glow */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50"></div>

      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 bg-transparent shrink-0">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-0 bg-primary/40 blur-md rounded-full"></div>
            <div className="w-9 h-9 bg-gradient-to-br from-primary to-[#00f2fe] rounded-xl flex items-center justify-center shadow-lg relative z-10 border border-white/20">
              <Bot size={20} className="text-white drop-shadow-md" />
            </div>
          </div>
          <div>
            <h3 className="text-[15px] font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60 tracking-wide">
              Alphahubiq Copilot
            </h3>
            <p className="text-[10px] text-stock-green uppercase font-bold tracking-wider mt-0.5">
              {currentTicker ? `LÀM VIỆC VỚI ${currentTicker}` : 'TRỢ LÝ TOÀN CẦU'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {messages.length > 0 && (
            <button onClick={clearMessages} className="text-text-muted hover:text-red-400 transition-colors p-2 rounded-lg hover:bg-white/5" title="Xóa lịch sử chat">
              <Trash2 size={16} />
            </button>
          )}
          <button onClick={() => setIsExpanded(!isExpanded)} className="text-text-muted hover:text-white transition-colors p-2 rounded-lg hover:bg-white/5" title={isExpanded ? "Thu nhỏ" : "Phóng to"}>
            {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button onClick={toggleAgent} className="text-text-muted hover:text-white transition-colors p-2 rounded-lg hover:bg-white/5" title="Đóng">
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 no-scrollbar relative">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center pb-10">
            <div className="relative mb-6">
              <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full scale-150"></div>
              <div className="w-20 h-20 bg-white/5 rounded-3xl flex items-center justify-center mx-auto border border-white/10 relative z-10 backdrop-blur-sm shadow-xl">
                <Bot size={40} className="text-primary drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]" />
              </div>
            </div>
            <h3 className="text-xl text-white font-bold mb-2 tracking-tight">Tôi có thể giúp gì cho bạn?</h3>
            <p className="text-text-muted text-sm px-6 max-w-xs leading-relaxed">Ra lệnh điều hướng web, hỏi thông tin tài chính, hoặc phân tích kỹ thuật ngay tại đây.</p>
            
            <div className="mt-8 space-y-3 w-full max-w-[90%]">
              {[
                `Mở trang danh mục đầu tư`, 
                `Phân tích mã NVDA`, 
                `Thị trường hôm nay thế nào?`
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(suggestion); }}
                  className="block w-full text-left px-5 py-3.5 text-sm font-medium text-text-primary bg-white/5 rounded-xl hover:bg-white/10 hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] transition-all border border-white/5 hover:border-white/15 group"
                >
                  <span className="group-hover:text-white transition-colors">{suggestion}</span>
                  <span className="float-right opacity-0 group-hover:opacity-100 transition-opacity text-primary">→</span>
                </button>
              ))}
            </div>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm ${msg.role === 'user' ? 'bg-white/10 border border-white/10' : 'bg-primary/20 text-primary border border-primary/30'}`}>
              {msg.role === 'user' ? <User size={14} className="text-white" /> : <Bot size={14} />}
            </div>
            <div className={`p-4 rounded-2xl max-w-[85%] text-[14px] leading-relaxed shadow-sm ${msg.role === 'user' ? 'bg-white/10 text-white rounded-tr-sm border border-white/5' : 'bg-transparent text-text-primary rounded-tl-sm border border-white/5 bg-gradient-to-br from-white/[0.03] to-transparent'}`}>
              {msg.role === 'assistant' ? (
                <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-black/40 prose-pre:border prose-pre:border-white/10">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content
                      .replace(/\[ACTION:.*?\]/g, '')
                      .replace(/<(?:｜｜DSML｜｜)?tool_calls>[\s\S]*?<\/(?:｜｜DSML｜｜)?tool_calls>/g, '')
                      .replace(/<(?:｜｜DSML｜｜)?tool_calls>[\s\S]*$/g, '')
                      .replace(/```(?:xml|bash|json)?\s*```/g, '')}
                  </ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 border border-primary/30">
              <Bot size={14} />
            </div>
            <div className="p-4 rounded-2xl bg-gradient-to-br from-white/[0.03] to-transparent text-text-secondary rounded-tl-sm flex items-center gap-3 border border-white/5 shadow-sm">
              <Loader2 size={16} className="animate-spin text-primary" /> 
              <span className="text-sm font-medium animate-pulse">Đang suy nghĩ...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Floating Input Area */}
      <div className="p-5 pt-2 shrink-0 bg-transparent relative z-10">
        <div className="flex items-center bg-[#1e293b]/90 backdrop-blur-md rounded-2xl border border-white/10 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 transition-all p-1.5 shadow-2xl">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Hỏi tôi bất cứ điều gì..."
            className="flex-1 bg-transparent px-4 py-2.5 text-white text-[15px] focus:outline-none placeholder-text-muted"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="w-10 h-10 bg-gradient-to-br from-primary to-blue-600 rounded-xl flex items-center justify-center text-white disabled:opacity-30 disabled:from-white/10 disabled:to-white/5 transition-all m-0.5 hover:shadow-[0_0_15px_rgba(59,130,246,0.6)] hover:scale-105 active:scale-95"
          >
            <Send size={16} className="ml-1" />
          </button>
        </div>
      </div>
    </div>
  );
}
