import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageLayout from '../components/layout/PageLayout';
import { ArrowLeft, TrendingUp, TrendingDown, ExternalLink, BrainCircuit, Loader2 } from 'lucide-react';
import StockChartPanel from '../components/stock-detail/StockChartPanel';
import StockSidebar from '../components/stock-detail/StockSidebar';
import AiAnalysisReport from '../components/stock-detail/AiAnalysisReport';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function StockDetailPage() {
  const { ticker: paramTicker } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [ticker, setTicker] = useState(paramTicker?.toUpperCase() || 'AAPL');
  const [stockInfo, setStockInfo] = useState(null);
  
  // AI Analysis State
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [showReport, setShowReport] = useState(false);

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
      
    // Reset AI state on ticker change
    setAnalysisData(null);
    setShowReport(false);
  }, [ticker]);

  const runAiAnalysis = async () => {
    if (analysisData) {
      setShowReport(true);
      return;
    }
    
    setIsAnalyzing(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user) headers['x-user-id'] = user.id;

      const res = await fetch(`${API_URL}/api/analysis/analyze`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ticker })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setAnalysisData(data.data);
        setShowReport(true);
      } else {
        alert("Lỗi phân tích: " + (data.detail || data.message));
      }
    } catch (err) {
      console.error(err);
      alert("Đã xảy ra lỗi khi gọi AI Analysis.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const changePercent = stockInfo ? stockInfo.change_percent : 0;
  const isPositive = changePercent >= 0;

  return (
    <PageLayout>
      <div className="flex flex-col min-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 bg-dark-card p-3 rounded-xl border border-dark-border shadow-sm">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/screener')}
              className="p-2 hover:bg-dark-hover rounded-lg transition-colors text-text-muted hover:text-white"
            >
              <ArrowLeft size={20} />
            </button>
            
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-white tracking-tight">{ticker}</h1>
                {stockInfo && (
                  <span className="text-sm font-medium text-text-muted px-2 py-0.5 bg-dark-bg rounded-md border border-dark-border">
                    {stockInfo.company}
                  </span>
                )}
                
                {/* AI Analysis Button */}
                <button
                  onClick={runAiAnalysis}
                  disabled={isAnalyzing}
                  className={`ml-4 px-3 py-1.5 rounded-lg flex items-center gap-2 text-sm font-bold transition-all shadow-sm ${
                    isAnalyzing 
                      ? 'bg-dark-bg border border-dark-border text-text-muted cursor-wait' 
                      : analysisData 
                        ? 'bg-primary/20 border border-primary/40 text-primary hover:bg-primary/30'
                        : 'bg-gradient-to-r from-primary to-purple-500 hover:from-primary-hover hover:to-purple-600 text-white border border-transparent shadow-[0_0_15px_rgba(59,130,246,0.3)] hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]'
                  }`}
                >
                  {isAnalyzing ? (
                    <><Loader2 size={16} className="animate-spin" /> Đang phân tích...</>
                  ) : analysisData ? (
                    <><BrainCircuit size={16} /> Xem báo cáo AI</>
                  ) : (
                    <><BrainCircuit size={16} /> AI Phân tích (4 Masters)</>
                  )}
                </button>
              </div>
              <p className="text-xs text-text-muted mt-1 flex items-center gap-1">
                NASDAQ <span className="w-1 h-1 rounded-full bg-text-muted"></span> IT Services
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-2xl font-bold text-white font-mono">
                ${stockInfo ? stockInfo.price.toFixed(2) : '---'}
              </div>
              <div className={`text-sm font-semibold flex items-center justify-end gap-1 ${isPositive ? 'text-stock-green' : 'text-stock-red'}`}>
                {isPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                {isPositive ? '+' : ''}{changePercent ? changePercent.toFixed(2) : '0.00'}%
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Area - 75/25 Split */}
        <div className="flex-1 flex flex-col lg:flex-row gap-4">
          
          {/* Left Panel: Chart (75%) */}
          <div className="flex-none lg:flex-1 lg:w-3/4 h-[600px] lg:min-h-[800px]">
            <StockChartPanel ticker={ticker} />
          </div>
          
          {/* Right Panel: Sidebar (25%) */}
          <div className="flex-none lg:w-1/4 h-[500px] lg:h-full">
            <StockSidebar ticker={ticker} stockInfo={stockInfo} />
          </div>
          
        </div>
      </div>

      <AiAnalysisReport 
        isOpen={showReport} 
        onClose={() => setShowReport(false)} 
        data={analysisData} 
      />
    </PageLayout>
  );
}
