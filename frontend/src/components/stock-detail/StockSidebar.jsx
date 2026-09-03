import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Newspaper, Users, Info, Loader2, ExternalLink } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function StockSidebar({ ticker, stockInfo }) {
  const [activeTab, setActiveTab] = useState('news');
  
  // News state
  const [news, setNews] = useState([]);
  const [loadingNews, setLoadingNews] = useState(false);
  
  // AI state
  const [assessmentResult, setAssessmentResult] = useState('');
  const [loadingAssessment, setLoadingAssessment] = useState(false);

  useEffect(() => {
    if (activeTab === 'news' && news.length === 0) {
      fetchNews();
    }
  }, [activeTab, ticker]);

  const fetchNews = async () => {
    setLoadingNews(true);
    try {
      const res = await fetch(`${API_URL}/api/news/${ticker}/summary`);
      const data = await res.json();
      if (data.status === 'success' && data.data && data.data.articles) {
        setNews(data.data.articles);
      } else {
        setNews([]);
      }
    } catch (err) {
      console.error('News fetch error:', err);
    } finally {
      setLoadingNews(false);
    }
  };

  const handleAssessment = async (mode) => {
    setLoadingAssessment(true);
    setAssessmentResult('');
    try {
      const response = await fetch(`${API_URL}/api/ai/assessment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, mode })
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let text = "";
      
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          text += decoder.decode(value, { stream: true });
          setAssessmentResult(text);
        }
      }
    } catch (err) {
      setAssessmentResult("**Error:** " + err.message);
    } finally {
      setLoadingAssessment(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-dark-card rounded-xl border border-dark-border overflow-hidden shadow-lg">
      {/* Tabs Header */}
      <div className="flex border-b border-dark-border">
        <button
          onClick={() => setActiveTab('news')}
          className={`flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-colors ${activeTab === 'news' ? 'text-primary border-b-2 border-primary bg-primary/10' : 'text-text-muted hover:text-white hover:bg-dark-hover'}`}
        >
          <Newspaper size={16} /> Tin tức
        </button>
        <button
          onClick={() => setActiveTab('ai')}
          className={`flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-colors ${activeTab === 'ai' ? 'text-stock-green border-b-2 border-stock-green bg-stock-green/10' : 'text-text-muted hover:text-white hover:bg-dark-hover'}`}
        >
          <Users size={16} /> Đánh giá AI
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          className={`flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-colors ${activeTab === 'stats' ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-400/10' : 'text-text-muted hover:text-white hover:bg-dark-hover'}`}
        >
          <Info size={16} /> Chỉ số
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto no-scrollbar p-4">
        {activeTab === 'news' && (
          <div className="space-y-4">
            {loadingNews ? (
              <div className="flex justify-center py-8"><Loader2 className="animate-spin text-primary" /></div>
            ) : news.length > 0 ? (
              news.map((item, idx) => (
                <div key={idx} className="p-3 bg-dark-bg rounded-lg border border-dark-border hover:border-primary/50 transition-colors">
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="block group">
                    <h4 className="text-sm font-semibold text-white group-hover:text-primary mb-1 line-clamp-2">{item.title}</h4>
                    <p className="text-xs text-text-muted mb-2 line-clamp-3">{item.body}</p>
                    <div className="flex justify-between items-center text-[10px] text-text-muted">
                      <span className="bg-[#1A2234] px-2 py-1 rounded">{item.source || 'Finnhub'}</span>
                      <span>{item.date}</span>
                    </div>
                  </a>
                </div>
              ))
            ) : (
              <p className="text-text-muted text-sm text-center py-8">Chưa có tin tức mới cho cổ phiếu này.</p>
            )}
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-4">
            <button 
              onClick={() => handleAssessment('team')}
              disabled={loadingAssessment}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-bold bg-dark-bg text-text-primary hover:bg-stock-green hover:text-dark-bg border border-dark-border transition-all disabled:opacity-50"
            >
              <Users size={16} /> Yêu cầu 4 Chuyên gia phân tích
            </button>
            
            {(loadingAssessment || assessmentResult) && (
              <div className="p-4 bg-dark-bg rounded-lg border border-dark-border">
                {loadingAssessment && !assessmentResult && (
                  <div className="flex flex-col items-center justify-center py-6 space-y-3">
                    <Loader2 className="w-6 h-6 animate-spin text-stock-green" />
                    <p className="text-text-secondary animate-pulse text-xs">AI đang tổng hợp dữ liệu...</p>
                  </div>
                )}
                
                {assessmentResult && (
                  <div className="prose prose-sm prose-invert max-w-none text-text-primary prose-headings:text-white prose-a:text-primary prose-strong:text-stock-green">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {assessmentResult
                        .replace(/\[ACTION:.*?\]/g, '')
                        .replace(/<[^>]*tool_calls>[\s\S]*?<\/[^>]*tool_calls>/g, '')
                        .replace(/<[^>]*tool_calls>[\s\S]*$/g, '')
                        .replace(/```(?:xml|bash|json)?\s*```/g, '')}
                    </ReactMarkdown>
                    {loadingAssessment && <span className="inline-block w-2 h-4 ml-1 bg-stock-green animate-pulse"></span>}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'stats' && (
          <div className="space-y-4">
            <h3 className="text-white font-semibold mb-3">Thống kê tài chính</h3>
            {stockInfo ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-dark-bg p-3 rounded-lg border border-dark-border">
                  <p className="text-xs text-text-muted mb-1">Vốn hóa</p>
                  <p className="text-sm font-semibold text-white">${(stockInfo.market_cap / 1e9).toFixed(2)}B</p>
                </div>
                <div className="bg-dark-bg p-3 rounded-lg border border-dark-border">
                  <p className="text-xs text-text-muted mb-1">P/E Ratio</p>
                  <p className="text-sm font-semibold text-white">{stockInfo.pe_ratio || 'N/A'}</p>
                </div>
                <div className="bg-dark-bg p-3 rounded-lg border border-dark-border">
                  <p className="text-xs text-text-muted mb-1">Cổ tức (Yield)</p>
                  <p className="text-sm font-semibold text-white">{stockInfo.dividend_yield ? (stockInfo.dividend_yield * 100).toFixed(2) + '%' : 'N/A'}</p>
                </div>
                <div className="bg-dark-bg p-3 rounded-lg border border-dark-border">
                  <p className="text-xs text-text-muted mb-1">Khối lượng</p>
                  <p className="text-sm font-semibold text-white">{(stockInfo.volume / 1e6).toFixed(1)}M</p>
                </div>
              </div>
            ) : (
              <p className="text-text-muted text-sm text-center py-4">Chưa có thông số cho cổ phiếu này.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
