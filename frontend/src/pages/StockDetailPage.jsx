import React, { Suspense, lazy, useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageLayout from '../components/layout/PageLayout';
import AgentPanel from '../components/AgentPanel';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  ArrowLeft, TrendingUp, TrendingDown, BarChart3, Target, Zap, Activity,
  CheckSquare, FileText, Users, Loader2, Newspaper, ChartLine, Info,
  ThumbsUp, ThumbsDown, Minus, ExternalLink
} from 'lucide-react';

const AdvancedRealTimeChart = lazy(() => 
  import('react-ts-tradingview-widgets').then(m => ({ default: m.AdvancedRealTimeChart }))
);

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function StockDetailPage() {
  const { ticker: paramTicker } = useParams();
  const navigate = useNavigate();
  const [ticker, setTicker] = useState(paramTicker?.toUpperCase() || 'AAPL');
  const [stockInfo, setStockInfo] = useState(null);
  const [studies, setStudies] = useState([]);
  const [activeTab, setActiveTab] = useState('analysis');
  
  // Analysis state
  const [assessmentMode, setAssessmentMode] = useState(null);
  const [assessmentResult, setAssessmentResult] = useState(null);
  const [loadingAssessment, setLoadingAssessment] = useState(false);
  
  // News state
  const [news, setNews] = useState(null);
  const [loadingNews, setLoadingNews] = useState(false);
  
  // S/R levels state
  const [srLevels, setSrLevels] = useState(null);
  const [loadingSR, setLoadingSR] = useState(false);

  // Fetch stock info from existing stocks endpoint
  useEffect(() => {
    fetch(`${API_URL}/api/stocks`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          const found = data.find(s => s.ticker === ticker);
          if (found) setStockInfo(found);
        }
      })
      .catch(console.error);
  }, [ticker]);

  // Fetch news when News tab is active
  useEffect(() => {
    if (activeTab === 'news' && !news) {
      fetchNews();
    }
  }, [activeTab, ticker]);

  const fetchNews = async () => {
    setLoadingNews(true);
    try {
      const res = await fetch(`${API_URL}/api/news/${ticker}/summary`);
      const data = await res.json();
      if (data.status === 'success') {
        setNews(data.data);
      }
    } catch (err) {
      console.error('News fetch error:', err);
    } finally {
      setLoadingNews(false);
    }
  };

  const fetchSRLevels = async () => {
    setLoadingSR(true);
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: `Find support and resistance levels for ${ticker}` }],
          user_id: '00000000-0000-0000-0000-000000000000'
        })
      });
      // Just read as text for streaming
      const text = await res.text();
      // Clean session ID prefix if present
      const cleaned = text.replace(/__session_id__:[^\n]+\n\n/, '');
      setSrLevels(cleaned);
    } catch (err) {
      console.error('S/R fetch error:', err);
    } finally {
      setLoadingSR(false);
    }
  };

  const handleAssessment = async (mode) => {
    setAssessmentMode(mode);
    setLoadingAssessment(true);
    setAssessmentResult('');
    try {
      const response = await fetch(`${API_URL}/api/ai/assessment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, mode, user_prompt: '' })
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let text = '';
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        text += decoder.decode(value, { stream: true });
        setAssessmentResult(text);
      }
    } catch (err) {
      setAssessmentResult('**Error:** ' + err.message);
    } finally {
      setLoadingAssessment(false);
    }
  };

  const handleAgentAction = (action) => {
    if (action.type === 'change_ticker') {
      setTicker(action.value.toUpperCase());
      navigate(`/stock/${action.value.toUpperCase()}`, { replace: true });
    } else if (action.type === 'add_indicator') {
      const indicatorMap = {
        'RSI': 'RSI@tv-basicstudies',
        'MACD': 'MACD@tv-basicstudies',
        'EMA': 'MAExp@tv-basicstudies',
        'SMA': 'MASimple@tv-basicstudies',
        'BB': 'BB@tv-basicstudies',
        'VOL': 'Volume@tv-basicstudies',
      };
      const study = indicatorMap[action.value.toUpperCase()];
      if (study) setStudies(prev => [...new Set([...prev, study])]);
    } else if (action.type === 'run_analysis') {
      handleAssessment(action.value);
    }
  };

  const chartOverlayButtons = [
    { label: 'Key Levels', icon: Target, action: fetchSRLevels, loading: loadingSR },
    { label: 'RSI', icon: Activity, action: () => setStudies(p => [...new Set([...p, 'RSI@tv-basicstudies'])]) },
    { label: 'MACD', icon: BarChart3, action: () => setStudies(p => [...new Set([...p, 'MACD@tv-basicstudies'])]) },
    { label: 'Supertrend', icon: Zap, action: () => setStudies(p => [...new Set([...p, 'Supertrend@tv-basicstudies'])]) },
  ];

  const assessmentButtons = [
    { mode: 'team', label: 'Đánh giá Chuyên gia', icon: Users, color: 'green' },
  ];

  const colorMap = { blue: 'bg-blue-600', purple: 'bg-purple-600', green: 'bg-stock-green', orange: 'bg-orange-600', red: 'bg-red-600' };
  const hoverMap = { blue: 'hover:bg-blue-600/80', purple: 'hover:bg-purple-600/80', green: 'hover:bg-stock-green', orange: 'hover:bg-orange-600/80', red: 'hover:bg-red-600/80' };

  const sentimentIcon = (impact) => {
    if (impact === 'positive') return <ThumbsUp size={14} className="text-stock-green" />;
    if (impact === 'negative') return <ThumbsDown size={14} className="text-stock-red" />;
    return <Minus size={14} className="text-text-muted" />;
  };

  return (
    <PageLayout>
      <div className="flex flex-col min-h-screen">
        {/* Header */}
        <div className="flex items-center gap-4 mb-4 px-2">
          <button onClick={() => navigate(-1)} className="text-text-muted hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              {ticker}
              {stockInfo && <span className="text-text-muted text-base font-normal">· {stockInfo.name}</span>}
            </h1>
            {stockInfo && (
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xl font-semibold text-white">${stockInfo.price?.toFixed(2)}</span>
                <span className={`flex items-center gap-1 text-sm font-semibold ${stockInfo.change >= 0 ? 'text-stock-green' : 'text-stock-red'}`}>
                  {stockInfo.change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {stockInfo.change >= 0 ? '+' : ''}{stockInfo.change?.toFixed(2)}%
                </span>
                {stockInfo.marketCap && (
                  <span className="text-xs text-text-muted bg-dark-bg px-2 py-0.5 rounded">MCap: {stockInfo.marketCap}</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Chart with overlay buttons */}
        <div className="relative mb-4">
          <div className="absolute top-3 left-3 z-10 flex gap-2 flex-wrap">
            {chartOverlayButtons.map((btn, i) => {
              const Icon = btn.icon;
              return (
                <button
                  key={i}
                  onClick={btn.action}
                  disabled={btn.loading}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-card/90 backdrop-blur border border-dark-border rounded-lg text-xs font-semibold text-text-primary hover:bg-primary hover:text-white hover:border-primary transition-all disabled:opacity-50"
                >
                  {btn.loading ? <Loader2 size={12} className="animate-spin" /> : <Icon size={12} />}
                  {btn.label}
                </button>
              );
            })}
          </div>
          
          <div className="w-full h-[500px] bg-dark-bg rounded-xl overflow-hidden border border-dark-border shadow-lg">
            <Suspense fallback={<div className="flex h-full items-center justify-center text-text-muted animate-pulse">Loading Chart...</div>}>
              <AdvancedRealTimeChart 
                key={ticker + studies.join(',')}
                symbol={ticker} 
                theme="dark" 
                autosize={true}
                allow_symbol_change={true}
                studies={studies.length > 0 ? studies : undefined}
              />
            </Suspense>
          </div>
        </div>

        {/* S/R Levels Display */}
        {srLevels && (
          <div className="mb-4 p-4 bg-dark-card border border-dark-border rounded-xl">
            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <Target size={16} className="text-primary" /> Support & Resistance Levels
            </h3>
            <div className="prose prose-invert prose-sm max-w-none text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{srLevels}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-dark-card border border-dark-border rounded-xl p-1">
          {[
            { id: 'analysis', label: 'Analysis', icon: ChartLine },
            { id: 'news', label: 'News', icon: Newspaper },
            { id: 'stats', label: 'Statistics', icon: Info },
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  activeTab === tab.id 
                    ? 'bg-primary text-white shadow-lg shadow-primary/20' 
                    : 'text-text-muted hover:text-white hover:bg-dark-hover'
                }`}
              >
                <Icon size={16} /> {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        {activeTab === 'analysis' && (
          <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-6">
            <h2 className="text-white font-semibold mb-4">Đánh giá AI cho cổ phiếu {ticker}</h2>
            <div className="flex flex-wrap gap-3 mb-4">
              {assessmentButtons.map(btn => {
                const Icon = btn.icon;
                return (
                  <button
                    key={btn.mode}
                    onClick={() => handleAssessment(btn.mode)}
                    disabled={loadingAssessment}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                      assessmentMode === btn.mode 
                        ? `${colorMap[btn.color]} text-white shadow-lg` 
                        : `bg-dark-bg text-text-primary ${hoverMap[btn.color]} border border-dark-border`
                    }`}
                  >
                    <Icon size={16} /> {btn.label}
                  </button>
                );
              })}
            </div>
            
            {(loadingAssessment || assessmentResult) && (
              <div className="p-4 bg-dark-bg rounded-lg border border-dark-border max-h-[500px] overflow-y-auto no-scrollbar">
                {loadingAssessment && !assessmentResult && (
                  <div className="flex flex-col items-center justify-center py-8 space-y-4">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    <p className="text-text-secondary animate-pulse text-sm">AI đang tổng hợp dữ liệu...</p>
                  </div>
                )}
                {assessmentResult && (
                  <div className="prose prose-invert max-w-none text-sm text-text-primary prose-headings:text-white prose-a:text-primary prose-strong:text-stock-green">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{assessmentResult}</ReactMarkdown>
                    {loadingAssessment && <span className="inline-block w-2 h-4 ml-1 bg-stock-green animate-pulse"></span>}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'news' && (
          <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Newspaper size={18} /> Latest News for {ticker}
            </h2>
            
            {loadingNews && (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <p className="text-text-secondary animate-pulse text-sm">Fetching & analyzing news...</p>
              </div>
            )}
            
            {news && (
              <>
                {/* AI Summary */}
                <div className={`p-4 rounded-xl mb-4 border ${
                  news.sentiment === 'bullish' ? 'bg-stock-green/5 border-stock-green/20' :
                  news.sentiment === 'bearish' ? 'bg-stock-red/5 border-stock-red/20' :
                  'bg-dark-bg border-dark-border'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      news.sentiment === 'bullish' ? 'bg-stock-green/20 text-stock-green' :
                      news.sentiment === 'bearish' ? 'bg-stock-red/20 text-stock-red' :
                      'bg-dark-hover text-text-muted'
                    }`}>
                      {news.sentiment?.toUpperCase()} {news.sentiment_score && `(${news.sentiment_score}/100)`}
                    </span>
                    <span className="text-xs text-text-muted">AI Summary</span>
                  </div>
                  <p className="text-sm text-text-primary leading-relaxed">{news.summary}</p>
                  
                  {news.key_events && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {news.key_events.map((event, i) => (
                        <span key={i} className="px-2 py-1 bg-dark-bg rounded text-xs text-text-secondary border border-dark-border">
                          {event}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Article List */}
                <div className="space-y-3">
                  {news.articles?.map((article, i) => {
                    const rated = news.rated_articles?.find(r => r.title === article.title);
                    return (
                      <a
                        key={i}
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-3 bg-dark-bg rounded-lg border border-dark-border hover:border-primary/50 transition-colors group"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-1">
                            <h3 className="text-sm font-medium text-white group-hover:text-primary transition-colors line-clamp-2">
                              {article.title}
                            </h3>
                            <p className="text-xs text-text-muted mt-1 line-clamp-2">{article.body}</p>
                            <div className="flex items-center gap-3 mt-2">
                              <span className="text-[10px] text-text-muted">{article.source}</span>
                              <span className="text-[10px] text-text-muted">{article.date}</span>
                              {rated && (
                                <span className="flex items-center gap-1 text-[10px]">
                                  {sentimentIcon(rated.impact)}
                                  <span className="text-text-muted">{rated.reason}</span>
                                </span>
                              )}
                            </div>
                          </div>
                          <ExternalLink size={14} className="text-text-muted flex-shrink-0 mt-1" />
                        </div>
                      </a>
                    );
                  })}
                </div>
              </>
            )}
            
            {!loadingNews && !news && (
              <button onClick={fetchNews} className="w-full py-3 text-sm text-primary hover:text-white hover:bg-primary rounded-lg transition-colors border border-primary/30">
                Load News
              </button>
            )}
          </div>
        )}

        {activeTab === 'stats' && stockInfo && (
          <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Info size={18} /> Statistics for {ticker}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Price', value: `$${stockInfo.price?.toFixed(2)}` },
                { label: 'Change', value: `${stockInfo.change?.toFixed(2)}%`, color: stockInfo.change >= 0 ? 'text-stock-green' : 'text-stock-red' },
                { label: 'Market Cap', value: stockInfo.marketCap || 'N/A' },
                { label: 'Score', value: `${stockInfo.score}/100` },
                { label: 'Sentiment', value: stockInfo.sentiment || 'N/A' },
                { label: 'ROI 1Y', value: `${stockInfo.roi1y?.toFixed(1)}%`, color: stockInfo.roi1y >= 0 ? 'text-stock-green' : 'text-stock-red' },
                { label: 'Forecast', value: `$${stockInfo.forecastAmt?.toFixed(2)}` },
                { label: 'Forecast %', value: `+${stockInfo.forecastPct}%`, color: 'text-stock-green' },
              ].map((stat, i) => (
                <div key={i} className="bg-dark-bg rounded-lg p-3 border border-dark-border">
                  <p className="text-[10px] text-text-muted uppercase font-semibold">{stat.label}</p>
                  <p className={`text-lg font-bold ${stat.color || 'text-white'} mt-1`}>{stat.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Agent Panel */}
      <AgentPanel ticker={ticker} onAction={handleAgentAction} />
    </PageLayout>
  );
}
