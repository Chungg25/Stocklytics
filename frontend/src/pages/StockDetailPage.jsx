import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageLayout from '../components/layout/PageLayout';
import { ArrowLeft, TrendingUp, TrendingDown, ExternalLink } from 'lucide-react';
import StockChartPanel from '../components/stock-detail/StockChartPanel';
import StockSidebar from '../components/stock-detail/StockSidebar';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function StockDetailPage() {
  const { ticker: paramTicker } = useParams();
  const navigate = useNavigate();
  const [ticker, setTicker] = useState(paramTicker?.toUpperCase() || 'AAPL');
  const [stockInfo, setStockInfo] = useState(null);

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

  const changePercent = stockInfo ? stockInfo.change_percent : 0;
  const isPositive = changePercent >= 0;

  return (
    <PageLayout>
      <div className="flex flex-col h-[calc(100vh-2rem)] min-h-[800px] pb-4">
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
        <div className="flex-1 flex flex-col lg:flex-row gap-4 overflow-hidden">
          
          {/* Left Panel: Chart (75%) */}
          <div className="flex-none lg:flex-1 lg:w-3/4 h-[500px] lg:h-full">
            <StockChartPanel ticker={ticker} />
          </div>
          
          {/* Right Panel: Sidebar (25%) */}
          <div className="flex-none lg:w-1/4 h-[500px] lg:h-full">
            <StockSidebar ticker={ticker} stockInfo={stockInfo} />
          </div>
          
        </div>
      </div>
    </PageLayout>
  );
}
