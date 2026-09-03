import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Newspaper, Users, Info, Loader2, ExternalLink } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function StockSidebar({ ticker, stockInfo }) {
  // News state
  const [news, setNews] = useState([]);
  const [loadingNews, setLoadingNews] = useState(false);

  useEffect(() => {
    fetchNews();
  }, [ticker]);

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



  return (
    <div className="flex flex-col h-full bg-dark-card rounded-xl border border-dark-border overflow-hidden shadow-lg">
      <div className="flex border-b border-dark-border">
        <div className="flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 text-primary border-b-2 border-primary bg-primary/10">
          <Newspaper size={16} /> Tin tức
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto no-scrollbar p-4">
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
      </div>
    </div>
  );
}
