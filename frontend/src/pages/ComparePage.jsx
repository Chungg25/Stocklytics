import React, { useState, useEffect } from 'react';
import { Home, ChevronRight, Activity, Search, X, TrendingUp, Settings } from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine, BarChart, Bar, ComposedChart
} from 'recharts';
import PageLayout from '../components/layout/PageLayout';

const COLORS = ['#00E5FF', '#00E676', '#FF9100', '#D500F9', '#FF1744', '#FFEA00'];

const timeframes = ['1M', '3M', '6M', '1Y', '3Y', '5Y'];

const indicatorOptions = [
  { id: 'SMA_20', label: 'SMA 20' },
  { id: 'SMA_50', label: 'SMA 50' },
  { id: 'SMA_200', label: 'SMA 200' },
  { id: 'EMA_20', label: 'EMA 20' },
  { id: 'EMA_50', label: 'EMA 50' },
  { id: 'BB', label: 'Bollinger Bands' },
  { id: 'RSI', label: 'RSI (14)' },
  { id: 'MACD', label: 'MACD' },
  { id: 'Volume', label: 'Volume' }
];

const ComparePage = () => {
  const [tickers, setTickers] = useState(['AAPL', 'MSFT', 'GOOGL']);
  const [inputValue, setInputValue] = useState('');
  const [timeframe, setTimeframe] = useState('3M');
  const [indicators, setIndicators] = useState([]);
  
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    if (tickers.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers, timeframe, indicators })
      });
      const resData = await response.json();
      if (resData.status === 'success') {
        setData(resData.data);
      } else {
        setError(resData.message);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [tickers, timeframe, indicators]);

  const handleAddTicker = (e) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      const newTicker = inputValue.trim().toUpperCase();
      if (!tickers.includes(newTicker)) {
        setTickers([...tickers, newTicker]);
      }
      setInputValue('');
    }
  };

  const removeTicker = (t) => {
    setTickers(tickers.filter(ticker => ticker !== t));
  };

  const toggleIndicator = (id) => {
    if (indicators.includes(id)) {
      setIndicators(indicators.filter(i => i !== id));
    } else {
      setIndicators([...indicators, id]);
    }
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-dark-card border border-dark-border p-3 rounded-md shadow-lg min-w-[150px]">
          <p className="text-white font-medium mb-2 pb-2 border-b border-dark-border">{label}</p>
          {payload.map((p, idx) => (
            <div key={idx} className="flex justify-between items-center text-sm my-1 gap-4">
              <span style={{ color: p.color }}>{p.name}:</span>
              <span className="font-bold text-white">
                {p.name.includes('Volume') ? p.value.toLocaleString() : 
                 (p.name.includes('RSI') || p.name.includes('MACD') ? p.value : `${p.value}%`)}
              </span>
            </div>
          ))}
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
        <span className="text-white">Compare</span>
      </div>

      <div className="flex items-center gap-3 mb-6">
        <Activity className="text-primary" size={28} />
        <h1 className="text-3xl font-bold text-white">Relative Price Performance</h1>
      </div>

      {/* Controls Area */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-6 space-y-4">
        
        {/* Row 1: Tickers and Timeframe */}
        <div className="flex flex-col xl:flex-row justify-between gap-4">
          {/* Ticker Input */}
          <div className="flex-1 flex flex-wrap items-center gap-2 bg-dark-bg border border-dark-border rounded-md p-2">
            {tickers.map((t, idx) => (
              <span key={t} className="flex items-center gap-1 px-3 py-1 rounded text-sm font-bold" 
                    style={{ backgroundColor: `${COLORS[idx % COLORS.length]}20`, color: COLORS[idx % COLORS.length], border: `1px solid ${COLORS[idx % COLORS.length]}50` }}>
                {t}
                <X size={14} className="cursor-pointer hover:text-white" onClick={() => removeTicker(t)} />
              </span>
            ))}
            <input 
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleAddTicker}
              placeholder="Add ticker..."
              className="bg-transparent text-white outline-none flex-1 min-w-[100px] px-2 text-sm"
            />
          </div>

          {/* Timeframe */}
          <div className="flex items-center bg-dark-bg border border-dark-border rounded-md overflow-hidden">
            {timeframes.map(tf => (
              <button 
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-4 py-2 text-sm font-medium transition-colors border-r border-dark-border last:border-0 ${
                  timeframe === tf ? 'bg-primary text-white' : 'text-text-muted hover:bg-dark-hover hover:text-white'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Indicators */}
        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-dark-border">
          <div className="flex items-center gap-2 text-text-muted mr-2">
            <Settings size={16} /> <span className="text-sm font-medium">Indicators:</span>
          </div>
          {indicatorOptions.map(ind => (
            <button
              key={ind.id}
              onClick={() => toggleIndicator(ind.id)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                indicators.includes(ind.id) 
                  ? 'bg-primary/20 border-primary text-primary' 
                  : 'bg-dark-bg border-dark-border text-text-muted hover:border-text-muted'
              }`}
            >
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="text-stock-red mb-4 p-4 border border-stock-red/20 rounded-lg">{error}</div>}

      {/* Main Chart */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-4 relative min-h-[400px]">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-dark-card/50 backdrop-blur-sm rounded-xl">
            <div className="text-primary font-bold animate-pulse">Loading Chart Data...</div>
          </div>
        )}
        
        <h2 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Performance (%)</h2>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3348" vertical={false} />
              <XAxis dataKey="date" stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} minTickGap={30} />
              <YAxis stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} />
              <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
              
              {/* Plot Main Tickers */}
              {tickers.map((t, idx) => (
                <Line key={t} type="monotone" dataKey={`${t}_perf`} name={t} stroke={COLORS[idx % COLORS.length]} strokeWidth={2} dot={false} isAnimationActive={false} />
              ))}

              {/* Plot Overlays (Only for the first ticker to avoid clutter) */}
              {tickers.length > 0 && indicators.includes('SMA_20') && <Line type="monotone" dataKey={`${tickers[0]}_SMA_20`} name={`${tickers[0]} SMA 20`} stroke="#FFEA00" strokeWidth={1} strokeDasharray="5 5" dot={false} isAnimationActive={false} />}
              {tickers.length > 0 && indicators.includes('SMA_50') && <Line type="monotone" dataKey={`${tickers[0]}_SMA_50`} name={`${tickers[0]} SMA 50`} stroke="#00E5FF" strokeWidth={1} strokeDasharray="5 5" dot={false} isAnimationActive={false} />}
              {tickers.length > 0 && indicators.includes('SMA_200') && <Line type="monotone" dataKey={`${tickers[0]}_SMA_200`} name={`${tickers[0]} SMA 200`} stroke="#FF1744" strokeWidth={1} strokeDasharray="5 5" dot={false} isAnimationActive={false} />}
              {tickers.length > 0 && indicators.includes('EMA_20') && <Line type="monotone" dataKey={`${tickers[0]}_EMA_20`} name={`${tickers[0]} EMA 20`} stroke="#D500F9" strokeWidth={1} strokeDasharray="3 3" dot={false} isAnimationActive={false} />}
              {tickers.length > 0 && indicators.includes('EMA_50') && <Line type="monotone" dataKey={`${tickers[0]}_EMA_50`} name={`${tickers[0]} EMA 50`} stroke="#00E676" strokeWidth={1} strokeDasharray="3 3" dot={false} isAnimationActive={false} />}
              
              {tickers.length > 0 && indicators.includes('BB') && <Line type="monotone" dataKey={`${tickers[0]}_BB_High`} name="BB High" stroke="#6B7280" strokeWidth={1} dot={false} isAnimationActive={false} />}
              {tickers.length > 0 && indicators.includes('BB') && <Line type="monotone" dataKey={`${tickers[0]}_BB_Low`} name="BB Low" stroke="#6B7280" strokeWidth={1} dot={false} isAnimationActive={false} />}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Sub Charts */}
      <div className="grid grid-cols-1 gap-4">
        {/* RSI Subchart */}
        {indicators.includes('RSI') && (
          <div className="bg-dark-card border border-dark-border rounded-xl p-4 h-[200px]">
            <h2 className="text-white font-semibold mb-2 text-sm uppercase tracking-wider text-text-muted">RSI (14)</h2>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D3348" vertical={false} />
                <XAxis dataKey="date" hide />
                <YAxis stroke="#6B7280" domain={[0, 100]} tick={{ fill: '#6B7280', fontSize: 10 }} ticks={[30, 70]} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={70} stroke="#FF1744" strokeDasharray="3 3" strokeOpacity={0.5} />
                <ReferenceLine y={30} stroke="#00E676" strokeDasharray="3 3" strokeOpacity={0.5} />
                {tickers.map((t, idx) => (
                  <Line key={`rsi-${t}`} type="monotone" dataKey={`${t}_RSI`} name={`${t} RSI`} stroke={COLORS[idx % COLORS.length]} strokeWidth={1} dot={false} isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Volume Subchart */}
        {indicators.includes('Volume') && (
          <div className="bg-dark-card border border-dark-border rounded-xl p-4 h-[200px]">
            <h2 className="text-white font-semibold mb-2 text-sm uppercase tracking-wider text-text-muted">Volume</h2>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <XAxis dataKey="date" hide />
                <YAxis stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 10 }} tickFormatter={(v) => `${(v/1000000).toFixed(0)}M`} />
                <Tooltip content={<CustomTooltip />} />
                {tickers.map((t, idx) => (
                  <Bar key={`vol-${t}`} dataKey={`${t}_Volume`} name={`${t} Vol`} fill={COLORS[idx % COLORS.length]} opacity={0.6} isAnimationActive={false} />
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* MACD Subchart */}
        {indicators.includes('MACD') && (
          <div className="bg-dark-card border border-dark-border rounded-xl p-4 h-[200px]">
            <h2 className="text-white font-semibold mb-2 text-sm uppercase tracking-wider text-text-muted">MACD</h2>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D3348" vertical={false} />
                <XAxis dataKey="date" hide />
                <YAxis stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 10 }} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
                {tickers.map((t, idx) => (
                  <Line key={`macd-${t}`} type="monotone" dataKey={`${t}_MACD`} name={`${t} MACD`} stroke={COLORS[idx % COLORS.length]} strokeWidth={1} dot={false} isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

    </PageLayout>
  );
};

export default ComparePage;
