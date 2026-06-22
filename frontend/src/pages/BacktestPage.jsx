import React, { useState } from 'react';
import { Home, ChevronRight, Play, Code, AlertTriangle, Sparkles, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import PageLayout from '../components/layout/PageLayout';

const BacktestPage = () => {
  const [ticker, setTicker] = useState('AAPL');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2024-01-01');
  const [prompt, setPrompt] = useState('Buy when 20 SMA crosses above 50 SMA. Sell when it crosses below.');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleBacktest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, start_date: startDate, end_date: endDate, prompt })
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        setResult(data.data);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const isBuy = payload[0].payload.signal === 1;
      const isSell = payload[0].payload.signal === -1;
      return (
        <div className="bg-dark-card border border-dark-border p-3 rounded-md shadow-lg">
          <p className="text-white font-medium mb-1">{label}</p>
          <p className="text-primary text-sm">Equity: ${payload[0].value}</p>
          <p className="text-text-muted text-sm">Close: ${payload[0].payload.close}</p>
          {isBuy && <p className="text-stock-green text-sm font-bold mt-1">BUY SIGNAL</p>}
          {isSell && <p className="text-stock-red text-sm font-bold mt-1">SELL SIGNAL</p>}
        </div>
      );
    }
    return null;
  };

  return (
    <PageLayout>
      {/* Breadcrumbs */}
      <div className="flex items-center text-sm text-text-muted mb-6">
        <Home size={16} className="mr-2" />
        <span>Home</span>
        <ChevronRight size={16} className="mx-2" />
        <span className="text-white">AI Strategies</span>
      </div>

      <div className="flex items-center gap-3 mb-2">
        <Sparkles className="text-primary" size={28} />
        <h1 className="text-3xl font-bold text-white">AI Strategy Backtest</h1>
      </div>
      <p className="text-text-muted mb-8 max-w-2xl">
        Describe your trading strategy in plain English. Our AI will automatically translate it into code and backtest it on historical market data.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Form */}
        <div className="lg:col-span-1 bg-dark-card border border-dark-border rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Configuration</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Ticker Symbol</label>
              <input 
                type="text" 
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-full bg-dark-bg border border-dark-border rounded-md px-3 py-2 text-white focus:border-primary focus:outline-none"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">Start Date</label>
                <input 
                  type="date" 
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-md px-3 py-2 text-white focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">End Date</label>
                <input 
                  type="date" 
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-md px-3 py-2 text-white focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Strategy Prompt</label>
              <textarea 
                rows="4"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded-md px-3 py-2 text-white focus:border-primary focus:outline-none resize-none"
                placeholder="e.g., Buy when RSI < 30, sell when RSI > 70"
              />
            </div>

            <button 
              onClick={handleBacktest}
              disabled={loading}
              className={`w-full flex justify-center items-center gap-2 py-3 rounded-md font-bold text-white transition-colors
                ${loading ? 'bg-primary/50 cursor-not-allowed' : 'bg-primary hover:bg-blue-600'}`}
            >
              {loading ? (
                <>Loading AI & Backtesting...</>
              ) : (
                <><Play size={18} fill="currentColor" /> Run Backtest</>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-6 p-4 bg-stock-red/10 border border-stock-red/20 rounded-md">
              <div className="flex items-start gap-2">
                <AlertTriangle className="text-stock-red mt-0.5" size={16} shrink-0 />
                <p className="text-stock-red text-sm whitespace-pre-wrap">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Results */}
        <div className="lg:col-span-2 space-y-6">
          {result ? (
            <>
              {/* Metrics Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-dark-card border border-dark-border rounded-xl p-4">
                  <p className="text-text-muted text-sm mb-1">Total Return</p>
                  <p className={`text-2xl font-bold ${result.metrics.total_return >= 0 ? 'text-stock-green' : 'text-stock-red'}`}>
                    {result.metrics.total_return > 0 ? '+' : ''}{result.metrics.total_return}%
                  </p>
                </div>
                <div className="bg-dark-card border border-dark-border rounded-xl p-4">
                  <p className="text-text-muted text-sm mb-1">Buy & Hold Return</p>
                  <p className="text-2xl font-bold text-white">
                    {result.metrics.buy_hold_return > 0 ? '+' : ''}{result.metrics.buy_hold_return}%
                  </p>
                </div>
                <div className="bg-dark-card border border-dark-border rounded-xl p-4">
                  <p className="text-text-muted text-sm mb-1">Win Rate</p>
                  <p className="text-2xl font-bold text-white">{result.metrics.win_rate}%</p>
                </div>
                <div className="bg-dark-card border border-dark-border rounded-xl p-4">
                  <p className="text-text-muted text-sm mb-1">Max Drawdown</p>
                  <p className="text-2xl font-bold text-stock-red">{result.metrics.max_drawdown}%</p>
                </div>
              </div>

              {/* Chart */}
              <div className="bg-dark-card border border-dark-border rounded-xl p-6">
                <div className="flex items-center gap-2 mb-6">
                  <Activity className="text-primary" size={20} />
                  <h2 className="text-white font-semibold text-lg">Equity Curve</h2>
                </div>
                <div className="h-[350px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={result.equity_curve} margin={{ top: 5, right: 0, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2D3348" vertical={false} />
                      <XAxis dataKey="date" stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} dy={10} minTickGap={30} />
                      <YAxis stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} dx={-10} domain={['auto', 'auto']} tickFormatter={(v) => `$${v}`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="equity" stroke="#3B82F6" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Generated Code */}
              <div className="bg-dark-card border border-dark-border rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Code className="text-text-muted" size={20} />
                  <h2 className="text-white font-semibold">AI Generated Python Code</h2>
                </div>
                <pre className="bg-[#0f141f] p-4 rounded-md overflow-x-auto text-sm text-text-muted font-mono">
                  {result.generated_code}
                </pre>
              </div>
            </>
          ) : (
            <div className="h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed border-dark-border rounded-xl text-text-muted">
              <Sparkles size={48} className="mb-4 opacity-50" />
              <p>Enter a strategy and run backtest to see results here.</p>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
};

export default BacktestPage;
