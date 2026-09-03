import React, { Suspense, lazy, useState, useEffect } from 'react';
import PageLayout from '../components/layout/PageLayout';
import { TrendingUp, Search, CheckSquare, FileText, Users, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const AdvancedRealTimeChart = lazy(() => import('react-ts-tradingview-widgets').then(m => ({ default: m.AdvancedRealTimeChart })));

const TradingViewPage = () => {
  const [symbol, setSymbol] = useState("AAPL");
  const [studies, setStudies] = useState([]);
  const [studiesOverrides, setStudiesOverrides] = useState({});
  
  const [prompt, setPrompt] = useState("");
  const [loadingIntent, setLoadingIntent] = useState(false);
  
  const [assessmentMode, setAssessmentMode] = useState(null);
  const [assessmentResult, setAssessmentResult] = useState(null);
  const [loadingAssessment, setLoadingAssessment] = useState(false);
  
  const [activeKey, setActiveKey] = useState(1);

  const fetchKeyStatus = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/ai/status`);
      const data = await res.json();
      if (data.status === 'success') {
        setActiveKey(data.active_key);
      }
    } catch(e) {
      console.error("Failed to fetch API key status", e);
    }
  };

  useEffect(() => {
    fetchKeyStatus();
  }, []);

  const handlePromptSubmit = async (e) => {
    if (e.key === 'Enter' && prompt.trim()) {
      setLoadingIntent(true);
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/ai/intent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt })
        });
        const result = await response.json();
        if (result.status === 'success' && result.data) {
          const { target_ticker, indicators, find_peers } = result.data;
          
          if (target_ticker) {
            setSymbol(target_ticker);
          }
          
          if (indicators && Array.isArray(indicators)) {
            // Map common indicators to TradingView study IDs
            let newOverrides = { ...studiesOverrides };
            
            const mappedStudies = indicators.map(ind => {
              const str = ind.toUpperCase();
              
              const match = str.match(/\d+/);
              const length = match ? parseInt(match[0]) : null;

              if (str.includes("EMA")) {
                if (length) newOverrides["Moving Average Exponential.length"] = length;
                return "MAExp@tv-basicstudies";
              }
              if (str.includes("SMA") || str === "MA") {
                if (length) newOverrides["Moving Average.length"] = length;
                return "MASimple@tv-basicstudies";
              }
              if (str.includes("RSI")) {
                if (length) newOverrides["Relative Strength Index.length"] = length;
                return "RSI@tv-basicstudies";
              }
              if (str.includes("MACD")) return "MACD@tv-basicstudies";
              if (str.includes("VOL")) return "Volume@tv-basicstudies";
              if (str.includes("BB") || str.includes("BOLL")) {
                if (length) newOverrides["Bollinger Bands.length"] = length;
                return "BB@tv-basicstudies";
              }
              return null;
            }).filter(Boolean);
            
            setStudiesOverrides(newOverrides);
            setStudies(prev => {
              return [...new Set([...prev, ...mappedStudies])];
            });
          }
        }
      } catch (err) {
        console.error("Error parsing intent:", err);
      } finally {
        setLoadingIntent(false);
        fetchKeyStatus();
      }
    }
  };

  const handleAssessment = async (mode) => {
    setAssessmentMode(mode);
    setLoadingAssessment(true);
    setAssessmentResult("");
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/ai/assessment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: symbol, mode, user_prompt: prompt })
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
      fetchKeyStatus();
    }
  };

  return (
    <PageLayout>
      <div className="flex flex-col min-h-screen">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-6 gap-4 px-2">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-white flex items-center gap-3 whitespace-nowrap">
              <TrendingUp className="text-stock-green" size={28} /> 
              AI Terminal
            </h1>
            <div className="flex items-center gap-2 px-3 py-1 bg-dark-card border border-dark-border rounded-full shadow">
              <div className={`w-2.5 h-2.5 rounded-full ${activeKey === 1 ? 'bg-stock-green' : 'bg-blue-500'} animate-pulse`}></div>
              <span className="text-xs font-semibold text-text-muted">Key {activeKey}</span>
            </div>
          </div>
          
          {/* AI Prompt Input */}
          <div className="relative w-full max-w-xl">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              {loadingIntent ? <Loader2 className="animate-spin text-stock-green" size={18} /> : <Search className="text-text-muted" size={18} />}
            </div>
            <input 
              type="text" 
              className="w-full bg-dark-card border border-dark-border text-white text-sm rounded-lg focus:ring-stock-green focus:border-stock-green block pl-10 p-2.5 shadow-inner" 
              placeholder="Ask AI (e.g., Analyze MSFT with MACD and RSI...)"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handlePromptSubmit}
              disabled={loadingIntent}
            />
          </div>
        </div>
        
        {/* TradingView Chart */}
        <div className="w-full h-[600px] bg-dark-bg rounded-xl overflow-hidden border border-dark-border shadow-lg mb-6">
          <Suspense fallback={<div className="flex h-full items-center justify-center text-text-muted animate-pulse">Loading TradingView Widget...</div>}>
            <AdvancedRealTimeChart 
              key={symbol + studies.join(",") + JSON.stringify(studiesOverrides)}
              symbol={symbol} 
              theme="dark" 
              autosize={true}
              allow_symbol_change={true}
              studies={studies.length > 0 ? studies : undefined}
              studiesOverrides={Object.keys(studiesOverrides).length > 0 ? studiesOverrides : undefined}
            />
          </Suspense>
        </div>

        {/* AI Assessment Actions */}
        <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-6 shadow-lg">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            AI Rating for {symbol}
          </h2>
          <div className="flex flex-wrap gap-4">
            <button 
              onClick={() => handleAssessment('team')}
              disabled={loadingAssessment}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${assessmentMode === 'team' ? 'bg-stock-green text-dark-bg shadow-lg' : 'bg-dark-bg text-text-primary hover:bg-stock-green hover:text-dark-bg border border-dark-border'}`}
            >
              <Users size={18} /> Rating
            </button>
          </div>
          
          {/* Assessment Result */}
          {(loadingAssessment || assessmentResult) && (
            <div className="mt-6 p-6 bg-dark-bg rounded-lg border border-dark-border max-h-[500px] overflow-y-auto no-scrollbar">
              {loadingAssessment && !assessmentResult && (
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <Loader2 className="w-8 h-8 animate-spin text-primary" />
                  <p className="text-text-secondary animate-pulse text-sm">AI is gathering data (Web Search)...</p>
                </div>
              )}
              
              {assessmentResult && (
                <div className="prose prose-invert max-w-none text-sm text-text-primary prose-headings:text-white prose-a:text-primary prose-strong:text-stock-green prose-p:leading-relaxed prose-th:text-white prose-td:text-text-secondary">
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
      </div>
    </PageLayout>
  );
};

export default TradingViewPage;
