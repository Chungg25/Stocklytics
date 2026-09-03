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
        setNews(data.data.articles.slice(0, 5)); // Limit to 5 articles
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
    <div className="flex flex-col bg-dark-card rounded-xl border border-dark-border overflow-hidden shadow-lg mt-6">
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-border bg-dark-bg/50">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Newspaper className="text-primary" size={20} /> Latest News
        </h3>
      </div>

      {/* Content */}
      <div className="p-6">
        {loadingNews ? (
          <div className="flex justify-center py-8"><Loader2 className="animate-spin text-primary" /></div>
        ) : news.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {news.map((item, idx) => (
              <div key={idx} className="flex flex-col p-4 bg-dark-bg rounded-xl border border-dark-border hover:border-primary/50 transition-all hover:shadow-md hover:shadow-primary/10 group">
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="block flex-1 flex flex-col">
                  <h4 className="text-sm font-bold text-white group-hover:text-primary mb-2 line-clamp-2 leading-snug">{item.title}</h4>
                  <p className="text-xs text-text-muted mb-4 line-clamp-3 flex-1">{item.body}</p>
                  <div className="flex justify-between items-center text-[10px] text-text-muted font-medium mt-auto">
                    <span className="bg-[#1A2234] px-2 py-1 rounded border border-white/5">{item.source || 'Finnhub'}</span>
                    <span>{item.date}</span>
                  </div>
                </a>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-text-muted text-sm text-center py-8 italic">No recent news for this stock.</p>
        )}
      </div>
    </div>
  );
}
