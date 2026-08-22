import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const ChatPage = () => {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);
  const skipNextFetchRef = useRef(false);
  
  // Fake user ID for now - should come from auth
  const USER_ID = "00000000-0000-0000-0000-000000000000";
  const rawApiUrl = import.meta.env.VITE_API_URL ?? '';
  const API_URL = rawApiUrl.replace(/\/$/, '');

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_URL}/api/chat/sessions/${USER_ID}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setSessions(data);
        if (data.length > 0 && !activeSession) {
          setActiveSession(data[0].id);
        }
      } else {
        console.error("Expected array but got:", data);
        setSessions([]);
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
    }
  };

  const fetchMessages = async (sessionId) => {
    try {
      const res = await fetch(`${API_URL}/api/chat/sessions/${sessionId}/messages`);
      const data = await res.json();
      if (Array.isArray(data)) {
        // Filter out tool messages for clean UI, or format them differently
        const parsedData = data.filter(m => m.role !== 'tool').map(m => {
          let displayContent = m.content || "";
          let isError = false;
          const errorMatch = displayContent.match(/__ERROR__:(.+)/s);
          if (errorMatch) {
              displayContent = displayContent.replace(/__ERROR__:.+/s, '').trim() + "\n\n" + errorMatch[1].trim();
              isError = true;
          }
          return { ...m, content: displayContent, isError };
        });
        setMessages(parsedData);
      } else {
        setMessages([]);
      }
    } catch (error) {
      console.error("Error fetching messages:", error);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (activeSession) {
      if (skipNextFetchRef.current) {
        skipNextFetchRef.current = false;
      } else {
        fetchMessages(activeSession);
      }
    } else {
      setMessages([]);
    }
  }, [activeSession]);

  const handleDeleteSession = async (sessionIdToDelete = activeSession) => {
    if (!sessionIdToDelete) return;
    if (window.confirm('Are you sure you want to delete this chat history?')) {
      try {
        await fetch(`${API_URL}/api/chat/sessions/${sessionIdToDelete}`, {
          method: 'DELETE'
        });
        if (activeSession === sessionIdToDelete) {
          setActiveSession(null);
        }
        fetchSessions();
      } catch (error) {
        console.error("Error deleting session:", error);
      }
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setIsTyping(true);

    try {
      // Setup payload matching Backend Request Model
      const payload = {
        session_id: activeSession,
        messages: newMessages.map(m => ({ role: m.role, content: m.content })),
        user_id: USER_ID
      };

      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let assistantMessage = "";
      
      // Add empty assistant message to be filled by stream
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunkValue = decoder.decode(value);
        
        // Handle custom session ID injection from backend stream
        const sessionPrefix = "__session_id__:";
        if (chunkValue.startsWith(sessionPrefix)) {
          const lines = chunkValue.split('\n\n');
          const sessionLine = lines[0];
          const newSessionId = sessionLine.replace(sessionPrefix, "").trim();
          
          if (!activeSession) {
             skipNextFetchRef.current = true;
             setActiveSession(newSessionId);
             fetchSessions(); // Refresh sidebar
          }
          
          // If there's more content in this chunk besides the session ID, process it
          if (lines.length > 1 && lines.slice(1).join('').trim()) {
             assistantMessage += lines.slice(1).join('\n\n');
          } else {
             continue;
          }
        } else {
          assistantMessage += chunkValue;
        }
        
        let displayContent = assistantMessage;
        let isError = false;
        
        if (assistantMessage.includes("__ERROR__:text__") || assistantMessage.includes("__ERROR__:炎")) {
            // just in case, but usually regex handles it
        }
        
        const errorMatch = assistantMessage.match(/__ERROR__:(.+)/s);
        if (errorMatch) {
            displayContent = assistantMessage.replace(/__ERROR__:.+/s, '').trim() + "\n\n" + errorMatch[1].trim();
            isError = true;
        }
        
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1].content = displayContent;
          if (isError) updated[updated.length - 1].isError = true;
          return updated;
        });
      }
    } catch (error) {
      console.error("Error during chat stream:", error);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden font-sans relative">
      
      {/* SIDEBAR */}
      <div className={`fixed inset-y-0 left-0 z-20 bg-gray-900/95 backdrop-blur-xl border-r border-gray-800 flex flex-col transition-all duration-300 ease-in-out overflow-hidden md:relative ${isSidebarOpen ? 'w-64 opacity-100 translate-x-0' : 'w-0 opacity-0 -translate-x-full border-r-0'}`}>
        <div className="p-4 border-b border-gray-700 w-64">
          <button 
            onClick={() => {setActiveSession(null); setMessages([]);}}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
            New Chat
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 space-y-1 w-64">
          {sessions.map(s => (
            <div 
              key={s.id}
              className={`group flex items-center justify-between w-full rounded-lg text-sm transition-colors ${activeSession === s.id ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50'}`}
            >
              <button 
                onClick={() => setActiveSession(s.id)}
                className="flex-1 text-left px-3 py-3 truncate"
              >
                {s.title}
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }}
                className={`p-2 mr-1 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors ${activeSession === s.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                title="Delete Session"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CHAT AREA */}
      <div className="flex-1 flex flex-col relative w-full">
        {/* Header (Glassmorphism) */}
        <div className="h-16 border-b border-white/5 flex items-center justify-between px-4 bg-gray-950/60 backdrop-blur-md z-10 sticky top-0">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 rounded-lg hover:bg-white/10 text-gray-400 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-lg font-semibold text-gray-100 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">Stocklytics AI</h1>
          </div>
          
          {activeSession && (
            <button 
              onClick={() => handleDeleteSession(activeSession)}
              className="p-2 rounded-lg hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
              title="Delete Chat History"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6 pb-32">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-500 space-y-4">
              <div className="w-16 h-16 bg-blue-900/30 rounded-2xl flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <p className="text-lg font-medium text-gray-400">What stock should we analyze today?</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} px-4 md:px-12`}>
                <div className={`w-full flex gap-4 transition-all duration-300 ${isSidebarOpen ? 'max-w-3xl' : 'max-w-5xl'} ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold shadow-lg ${msg.role === 'user' ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white' : 'bg-gradient-to-br from-teal-400 to-emerald-600 text-white'}`}>
                    {msg.role === 'user' ? 'ME' : 'AI'}
                  </div>
                  
                  {/* Message Content */}
                  <div className={`prose prose-invert max-w-none text-sm md:text-base leading-relaxed ${msg.role === 'user' ? 'bg-gradient-to-br from-blue-600 to-indigo-700 px-5 py-3 rounded-2xl rounded-tr-sm shadow-md' : (msg.isError ? 'bg-red-900/30 border border-red-700/50 px-5 py-4 rounded-2xl text-red-200 w-full' : 'pt-1 text-gray-200 w-full')}`}>
                    {msg.role === 'assistant' && msg.content === '' && isTyping ? (
                      <div className="flex items-center space-x-2 h-6 mt-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        <span className="text-gray-400 text-sm ml-2 animate-pulse">Analyzing & gathering data...</span>
                      </div>
                    ) : (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          table: ({node, ...props}) => <div className="overflow-x-auto my-4"><table className="min-w-full divide-y divide-gray-700 border border-gray-700 rounded-lg" {...props} /></div>,
                          th: ({node, ...props}) => <th className="px-4 py-3 bg-gray-800 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider" {...props} />,
                          td: ({node, ...props}) => <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300 border-t border-gray-700" {...props} />,
                          code: ({node, inline, className, children, ...props}) => {
                            const match = /language-(\w+)/.exec(className || '');
                            const isWidget = match && match[1] === 'widget';
                            if (!inline && isWidget) {
                              const ticker = String(children).replace(/\n$/, '').trim();
                              return (
                                <div className="my-6 rounded-xl overflow-hidden border border-gray-700 shadow-2xl h-[400px] w-full bg-gray-900">
                                  <iframe
                                    title={`TradingView Chart ${ticker}`}
                                    src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_123&symbol=${ticker}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=MACD%40tv-basicstudies%1FRSI%40tv-basicstudies&theme=dark&style=1&timezone=Etc%2FUTC&studies_overrides=%7B%7D&overrides=%7B%7D&enabled_features=%5B%5D&disabled_features=%5B%5D&locale=en&utm_source=&utm_medium=widget&utm_campaign=chart&utm_term=${ticker}`}
                                    width="100%"
                                    height="100%"
                                    frameBorder="0"
                                    allowTransparency="true"
                                    scrolling="no"
                                    allowFullScreen
                                  ></iframe>
                                </div>
                              );
                            }
                            return <code className={`${className} bg-gray-800 rounded px-1.5 py-0.5 text-blue-300`} {...props}>{children}</code>;
                          }
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Floating Input Box */}
        <div className="absolute bottom-0 w-full bg-gradient-to-t from-gray-950 via-gray-950 to-transparent pt-12 pb-6 px-4 md:px-12 pointer-events-none">
          <div className={`mx-auto relative pointer-events-auto shadow-2xl rounded-2xl overflow-hidden ring-1 ring-white/10 focus-within:ring-blue-500/50 focus-within:ring-2 transition-all duration-300 bg-gray-900 ${isSidebarOpen ? 'max-w-3xl' : 'max-w-5xl'}`}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask for an analysis, e.g., 'Phân tích AAPL'..."
              className="w-full bg-transparent text-gray-100 pl-5 pr-14 py-4 focus:outline-none resize-none h-14"
              rows="1"
            />
            <button
              onClick={handleSend}
              disabled={isTyping || !input.trim()}
              className="absolute right-2 top-2 p-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 disabled:from-gray-700 disabled:to-gray-700 transition-all text-white shadow-md"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            </button>
          </div>
          <div className="text-center mt-3 text-xs text-gray-500">
            AI có thể mắc lỗi. Vui lòng kiểm chứng các thông tin quan trọng.
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
