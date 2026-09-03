import React, { useState, useEffect, useMemo } from 'react';
import { Home, ChevronRight, Activity, X, TrendingUp, Settings, Trophy, AlertTriangle, Target, Info, CheckCircle2, ShieldCheck, BarChart2, Zap, LayoutGrid, ChevronDown, ChevronUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import PageLayout from '../components/layout/PageLayout';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const COLORS = ['#00E5FF', '#00E676', '#FF9100', '#D500F9', '#FF1744', '#FFEA00'];
const API_URL = import.meta.env.VITE_API_URL ?? '';

const LastPointLabel = (props) => {
  const { x, y, color, value, index, name, dataLength } = props;
  if (index !== dataLength - 1) return null;
  const valNum = parseFloat(value);
  if (isNaN(valNum)) return null;
  const labelText = `${name} | ${valNum >= 0 ? '+' : ''}${valNum.toFixed(2)}%`;
  const width = name.length * 6 + 55;
  return (
    <g>
      <line x1={x} y1={y} x2={x + 6} y2={y} stroke={color} strokeWidth={1.5} />
      <rect x={x + 6} y={y - 11} width={width} height={22} rx={3} fill={color} stroke="#0b0f1a" strokeWidth={1} />
      <text x={x + 6 + width / 2} y={y + 4} fill="#0b0f1a" fontSize={10} fontWeight="bold" fontFamily="sans-serif" textAnchor="middle">{labelText}</text>
    </g>
  );
};

const ComparePage = () => {
  const [groups, setGroups] = useState({});
  const [selectedGroup, setSelectedGroup] = useState('');
  const [tickers, setTickers] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [newGroupName, setNewGroupName] = useState('');
  const [timeframe, setTimeframe] = useState('3M');
  const [autoPeers, setAutoPeers] = useState(false);

  // Basic Fast Chart State
  const [fullBasicData, setFullBasicData] = useState([]);
  const [loadingBasic, setLoadingBasic] = useState(false);

  // Deep AI Analysis State
  const [compareData, setCompareData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});
  const [showAdvancedMetrics, setShowAdvancedMetrics] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    const fetchGroups = async () => {
      try {
        const response = await fetch(`${API_URL}/api/trading/groups`);
        const resData = await response.json();
        if (resData.status === 'success' && resData.groups && Object.keys(resData.groups).length > 0) {
          setGroups(resData.groups);
        } else {
          // Default groups if empty or failed to load
          setGroups({
            "Tech Giants": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
            "Semiconductors": ["NVDA", "AMD", "TSM", "AVGO", "INTC"],
            "AI Winners": ["NVDA", "SMCI", "PLTR", "ARM", "CRWD"]
          });
        }
      } catch (err) {
        console.error("Failed to load stock groups:", err);
      }
    };
    fetchGroups();
  }, []);

  // Auto-fetch basic fast chart data ONCE (5Y) when tickers change
  useEffect(() => {
    const fetchBasicChart = async () => {
      if (tickers.length === 0) {
        setFullBasicData([]);
        return;
      }
      setLoadingBasic(true);
      setError(null);
      try {
        const response = await fetch(`${API_URL}/api/compare`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers, timeframe: '5Y', indicators: [] })
        });
        const resData = await response.json();
        if (resData.status === 'success') {
          setFullBasicData(resData.data);
        } else {
          setError(resData.message);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingBasic(false);
      }
    };
    fetchBasicChart();
  }, [tickers]); // Only refetch when tickers change!

  const handleRunComparison = async () => {
    if (tickers.length === 0) {
      setError("Please add at least one ticker.");
      return;
    }
    if (!autoPeers && tickers.length < 2) {
      setError("Please add at least 2 tickers for comparison, or enable 'Auto-find Peers'.");
      return;
    }
    setLoading(true);
    setError(null);
    setCompareData(null);
    setExpandedCategories({});
    try {
      const response = await fetch(`${API_URL}/api/analysis/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers, auto_peers: autoPeers })
      });
      const resData = await response.json();
      if (resData.status === 'success') {
        setCompareData(resData.data);
      } else {
        setError(resData.detail || resData.message || "An error occurred.");
      }
    } catch (err) {
      setError("Analysis Failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGroupChange = (groupName) => {
    setSelectedGroup(groupName);
    setTickers(groups[groupName] || []);
    setError(null);
    setSuccessMsg(null);
  };

  const handleAddTicker = (e) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      const newTicker = inputValue.trim().toUpperCase();
      if (tickers.length >= 50) {
        setError("Maximum 50 tickers allowed for basic charting.");
        return;
      }
      if (!tickers.includes(newTicker)) {
        const updatedTickers = [...tickers, newTicker];
        setTickers(updatedTickers);
        if (selectedGroup) {
          setGroups({ ...groups, [selectedGroup]: updatedTickers });
        }
        setError(null);
      }
      setInputValue('');
    }
  };

  const removeTicker = (t) => {
    const updatedTickers = tickers.filter(ticker => ticker !== t);
    setTickers(updatedTickers);
    if (selectedGroup) {
      setGroups({ ...groups, [selectedGroup]: updatedTickers });
    }
    setError(null);
  };

  const handleCreateGroup = () => {
    if (!newGroupName.trim()) return;
    const name = newGroupName.trim();
    if (groups[name]) {
      setError("Group already exists!");
      return;
    }
    const updatedGroups = { ...groups, [name]: [] };
    setGroups(updatedGroups);
    setSelectedGroup(name);
    setTickers([]);
    setNewGroupName('');
  };

  const handleDeleteGroup = () => {
    if (!selectedGroup) return;
    if (window.confirm(`Delete the group "${selectedGroup}"?`)) {
      const updatedGroups = { ...groups };
      delete updatedGroups[selectedGroup];
      setGroups(updatedGroups);
      const nextGroup = Object.keys(updatedGroups)[0] || '';
      setSelectedGroup(nextGroup);
      setTickers(nextGroup ? updatedGroups[nextGroup] : []);
    }
  };

  const handleSaveToSheets = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/trading/groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groups })
      });
      const resData = await response.json();
      if (resData.status === 'success') {
        setSuccessMsg("Successfully saved to database!");
        setTimeout(() => setSuccessMsg(null), 3000);
      } else {
        setError(resData.message);
      }
    } catch (err) {
      setError("Failed to save: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const formattedBasicChartData = useMemo(() => {
    // Process fullBasicData based on timeframe locally to avoid API calls!
    if (!fullBasicData || fullBasicData.length === 0) return [];
    
    let daysToSubtract = 90;
    if (timeframe === '1M') daysToSubtract = 30;
    else if (timeframe === '3M') daysToSubtract = 90;
    else if (timeframe === '6M') daysToSubtract = 180;
    else if (timeframe === '1Y') daysToSubtract = 365;
    else if (timeframe === '3Y') daysToSubtract = 365 * 3;
    else if (timeframe === '5Y') daysToSubtract = 365 * 5;

    const endDate = new Date(fullBasicData[fullBasicData.length - 1].date);
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - daysToSubtract);
    
    // 1. Slice
    const slicedData = fullBasicData.filter(d => new Date(d.date) >= startDate);
    if (slicedData.length === 0) return [];

    // 2. Re-base everything so starting point is 0%
    const baseRow = slicedData[0];
    
    return slicedData.map(row => {
      const newRow = { ...row };
      tickers.forEach(t => {
        const perfKey = `${t}_perf`;
        if (baseRow[perfKey] !== undefined && row[perfKey] !== undefined) {
           const r_k = baseRow[perfKey] / 100; // Return at start of timeframe
           const r_t = row[perfKey] / 100;     // Return today
           newRow[perfKey] = (((1 + r_t) / (1 + r_k)) - 1) * 100;
        }
      });
      return newRow;
    });

  }, [fullBasicData, timeframe, tickers]);

  const formattedAIChartData = useMemo(() => {
    if (!compareData || !compareData.chart_data) return [];
    const merged = {};
    Object.keys(compareData.chart_data).forEach(ticker => {
      const arr = compareData.chart_data[ticker];
      if (Array.isArray(arr)) {
        arr.forEach(pt => {
          if (!merged[pt.date]) merged[pt.date] = { date: pt.date };
          merged[pt.date][ticker] = pt.value;
        });
      }
    });
    return Object.values(merged).sort((a, b) => new Date(a.date) - new Date(b.date));
  }, [compareData]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-dark-card border border-dark-border p-3 rounded-md shadow-lg min-w-[150px]">
          <p className="text-white font-medium mb-2 pb-2 border-b border-dark-border">{label}</p>
          {payload.map((p, idx) => (
            <div key={idx} className="flex justify-between items-center text-sm my-1 gap-4">
              <span style={{ color: p.color }}>{p.name}:</span>
              <span className="font-bold text-white">
                {Number(p.value).toFixed(2)}
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
      <div className="flex items-center text-sm text-text-muted mb-6">
        <Home size={16} className="mr-2" />
        <span>Home</span>
        <ChevronRight size={16} className="mx-2" />
        <span className="text-white">AI Compare</span>
      </div>

      <div className="flex items-center gap-3 mb-6">
        <Activity className="text-primary drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]" size={32} />
        <div>
          <h1 className="text-3xl font-bold text-white">Compare Stocks & Industry Peers</h1>
          <p className="text-sm text-text-secondary mt-1">Multi-dimensional analysis using AI and Quant metrics</p>
        </div>
      </div>

      {/* Controls Area */}
      <div className="bg-gradient-to-b from-dark-card to-dark-bg border border-dark-border rounded-2xl p-6 mb-8 shadow-xl relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px] pointer-events-none -mr-40 -mt-40"></div>

        <div className="flex flex-col gap-6 relative z-10">
          
          {/* Top Row: Search & Action */}
          <div className="flex flex-col lg:flex-row justify-between items-stretch lg:items-center gap-4">
            
            {/* Ticker Input Area */}
            <div className="flex-1 flex flex-wrap items-center gap-2 bg-[#0d1326] border border-[#1e293b] rounded-xl p-2 shadow-inner min-h-[56px] focus-within:border-primary/50 transition-colors">
              {tickers.map((t, idx) => (
                <span key={t} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-bold shadow-sm transition-transform hover:scale-105"
                  style={{ backgroundColor: `${COLORS[idx % COLORS.length]}20`, color: COLORS[idx % COLORS.length], border: `1px solid ${COLORS[idx % COLORS.length]}40` }}>
                  {t}
                  <X size={14} className="cursor-pointer hover:text-white transition-colors" onClick={() => removeTicker(t)} />
                </span>
              ))}
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleAddTicker}
                placeholder={tickers.length >= 50 ? "Maximum 50 tickers reached" : tickers.length === 0 ? "Search tickers (e.g. NVDA)..." : "Add another ticker..."}
                disabled={tickers.length >= 50}
                className={`bg-transparent text-white outline-none flex-1 min-w-[150px] px-3 py-1.5 text-sm font-medium placeholder:text-slate-500 ${tickers.length >= 50 ? 'cursor-not-allowed opacity-50' : ''}`}
              />
            </div>

            {/* Timeframe Buttons */}
            <div className="flex items-center bg-[#0d1326] border border-[#1e293b] rounded-xl overflow-hidden shadow-inner h-[56px]">
              {['1M', '3M', '6M', '1Y', '3Y', '5Y'].map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-4 h-full text-sm font-bold transition-colors border-r border-[#1e293b] last:border-0 ${
                    timeframe === tf ? 'bg-primary text-white shadow-inner' : 'text-text-muted hover:bg-white/5 hover:text-white'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>

            {/* Actions (Auto-peers & Compare) */}
            <div className="flex items-center gap-3 bg-[#0d1326] border border-[#1e293b] rounded-xl p-2 shadow-inner">
              <label className="flex items-center gap-2 cursor-pointer select-none px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors">
                <div className="relative flex items-center">
                  <input 
                    type="checkbox" 
                    checked={autoPeers} 
                    onChange={(e) => setAutoPeers(e.target.checked)}
                    className="sr-only"
                  />
                  <div className={`w-10 h-5 bg-dark-bg rounded-full border ${autoPeers ? 'border-primary' : 'border-dark-border'} transition-colors`}></div>
                  <div className={`absolute left-1 top-1 w-3 h-3 rounded-full transition-transform ${autoPeers ? 'translate-x-5 bg-primary shadow-[0_0_8px_rgba(59,130,246,0.8)]' : 'bg-text-muted'}`}></div>
                </div>
                <span className={`text-sm font-bold ${autoPeers ? 'text-white' : 'text-text-muted'}`}>Auto-Peers</span>
              </label>
              
              <div className="w-px h-6 bg-[#1e293b]"></div>
              
              <button
                onClick={handleRunComparison}
                disabled={loading || (tickers.length === 0)}
                className="flex items-center gap-2 bg-gradient-to-r from-primary to-purple-600 text-white px-8 h-[40px] rounded-lg text-sm font-bold hover:from-primary-hover hover:to-purple-700 disabled:opacity-50 disabled:grayscale transition-all shadow-[0_0_15px_rgba(59,130,246,0.3)] hover:shadow-[0_0_25px_rgba(59,130,246,0.5)]"
                title="Deep AI analysis (requires 2-5 tickers)"
              >
                {loading ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div> : <Zap size={16} className={tickers.length > 0 && tickers.length <= 5 ? "animate-pulse" : ""} />}
                {loading ? "Analyzing..." : "Deep AI Compare"}
              </button>
            </div>
          </div>

          {/* Bottom Row: Groups & Presets */}
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pt-5 border-t border-[#1e293b]">
            
            {/* Presets List */}
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="text-text-muted text-xs font-black uppercase tracking-widest mr-2 flex items-center gap-1.5">
                <Settings size={14} /> Presets
              </div>
              {Object.keys(groups).map(groupName => (
                <button
                  key={groupName}
                  onClick={() => handleGroupChange(groupName)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                    selectedGroup === groupName 
                    ? 'bg-primary/20 border-primary/50 text-primary shadow-[0_0_10px_rgba(59,130,246,0.2)]' 
                    : 'bg-[#0d1326] border-[#1e293b] text-text-secondary hover:border-primary/30 hover:text-white'
                  }`}
                >
                  {groupName}
                </button>
              ))}
            </div>

            {/* Manage Groups */}
            <div className="flex items-center gap-3">
              <div className="flex items-center bg-[#0d1326] border border-[#1e293b] rounded-lg overflow-hidden focus-within:border-primary/30 transition-colors">
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="New preset name..."
                  className="bg-transparent text-white outline-none px-3 py-1.5 text-xs placeholder:text-slate-500 w-32 focus:w-40 transition-all"
                />
                <button 
                  onClick={handleCreateGroup} 
                  className="bg-[#1e293b] hover:bg-primary hover:text-white text-text-secondary px-3 py-1.5 text-xs font-bold transition-colors"
                >
                  Add
                </button>
              </div>

              {selectedGroup && (
                <>
                  <div className="w-px h-5 bg-[#1e293b]"></div>
                  <button onClick={handleDeleteGroup} className="text-stock-red/70 hover:text-stock-red text-xs font-bold transition-colors flex items-center gap-1">
                    <X size={14} /> Delete
                  </button>
                </>
              )}
              
              <div className="w-px h-5 bg-[#1e293b]"></div>
              
              <button 
                onClick={handleSaveToSheets} 
                disabled={saving || !selectedGroup} 
                className="text-stock-green/80 hover:text-stock-green disabled:opacity-50 text-xs font-bold transition-colors flex items-center gap-1"
              >
                <CheckCircle2 size={14} /> {saving ? "Saving..." : "Save"}
              </button>
            </div>

          </div>
        </div>
      </div>

      {error && <div className="text-stock-red mb-6 p-4 border border-stock-red/20 bg-stock-red/10 rounded-lg font-medium flex items-center gap-2"><AlertTriangle size={18}/> {error}</div>}
      {successMsg && <div className="text-stock-green mb-6 p-4 border border-stock-green/20 bg-stock-green/10 rounded-lg font-medium flex items-center gap-2"><CheckCircle2 size={18}/> {successMsg}</div>}

      {/* BASIC CHART RENDER */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-6 mb-6 shadow-lg relative min-h-[450px]">
        {loadingBasic && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-dark-card/50 backdrop-blur-sm rounded-xl">
            <div className="text-primary font-bold animate-pulse flex items-center gap-2"><div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div> Loading Chart Data...</div>
          </div>
        )}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <TrendingUp className="text-primary" size={20} /> Percentage Comparison Chart
          </h2>
          {tickers.length > 5 && !compareData && (
            <div className="text-xs font-bold text-stock-red bg-stock-red/10 px-3 py-1 rounded-full border border-stock-red/20">
              Note: Reduce to 5 tickers or less to run Deep AI Compare.
            </div>
          )}
        </div>
        <div className="h-[380px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formattedBasicChartData} margin={{ top: 10, right: 100, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis dataKey="date" stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} minTickGap={40} />
              <YAxis stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} domain={['auto', 'auto']} tickFormatter={(v) => `${v}%`} />
              <RechartsTooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px', fontWeight: 'bold' }} />
              <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" opacity={0.5} />
              {tickers.map((t, idx) => (
                <Line
                  key={t}
                  type="monotone"
                  dataKey={`${t}_perf`}
                  name={t}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2.5}
                  dot={false}
                  isAnimationActive={true}
                  connectNulls={true}
                  label={<LastPointLabel name={t} dataLength={formattedBasicChartData.length} color={COLORS[idx % COLORS.length]} />}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* DASHBOARD RENDER */}
      {compareData && (
        <div className="space-y-6 animate-fade-in">
          
          {/* Executive Summary & Winner */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="xl:col-span-2 bg-dark-card border border-dark-border rounded-xl p-6 shadow-lg relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Target className="text-primary" size={24} /> AI Executive Summary
              </h2>
              <div className="prose prose-invert max-w-none text-sm text-text-secondary prose-strong:text-white leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{compareData.summary || "No summary provided."}</ReactMarkdown>
              </div>
            </div>

            <div className="flex flex-col gap-6">
              {compareData.winner && (
                <div className="bg-gradient-to-br from-yellow-500/20 to-orange-500/5 border border-yellow-500/30 rounded-xl p-6 flex flex-col items-center justify-center text-center shadow-[0_0_30px_rgba(234,179,8,0.1)] relative overflow-hidden">
                  <Trophy size={48} className="text-yellow-500 mb-2 drop-shadow-lg" />
                  <div className="text-xs font-bold text-yellow-500/80 uppercase tracking-widest mb-1">Overall Winner</div>
                  <div className="text-4xl font-black text-white tracking-tight">{compareData.winner.ticker}</div>
                  <div className="text-sm font-bold text-yellow-400 mt-2 bg-yellow-500/10 px-3 py-1 rounded-full border border-yellow-500/20">
                    AI Score: {compareData.winner.score}
                  </div>
                </div>
              )}
              
              {compareData.anomalies && compareData.anomalies.length > 0 && (
                <div className="bg-dark-card border border-stock-red/20 rounded-xl p-5 flex-1 shadow-lg">
                  <h3 className="text-sm font-bold text-stock-red uppercase tracking-wider mb-3 flex items-center gap-2">
                    <AlertTriangle size={16} /> Key Anomalies
                  </h3>
                  <div className="space-y-3">
                    {compareData.anomalies.map((ano, i) => (
                      <div key={i} className="text-xs text-text-primary bg-stock-red/5 p-2.5 rounded border border-stock-red/10 leading-relaxed">
                        {ano}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>



          {/* Comparison Matrix & Best For */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-dark-card border border-dark-border rounded-xl shadow-lg overflow-hidden flex flex-col">
              <div className="p-5 border-b border-dark-border bg-dark-bg/50">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <LayoutGrid className="text-primary" size={20} /> Fundamental Matrix
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left whitespace-nowrap">
                  <thead>
                    <tr className="bg-dark-bg text-xs font-bold text-text-muted uppercase tracking-wider border-b border-dark-border">
                      <th className="p-4">Metric</th>
                      {compareData.tickers.map(t => <th key={t} className="p-4 text-white">{t}</th>)}
                      {compareData.sector_median && <th className="p-4 text-primary bg-primary/5">Sector Median</th>}
                    </tr>
                  </thead>
                  <tbody className="text-sm font-medium">
                    <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                      <td className="p-4 text-text-secondary">AI Score</td>
                      {compareData.tickers.map(t => <td key={t} className="p-4 text-white font-bold">{compareData.comparison_table[t]?.score || '-'}</td>)}
                      {compareData.sector_median && <td className="p-4 text-primary bg-primary/5">{compareData.sector_median.score || '-'}</td>}
                    </tr>
                    <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                      <td className="p-4 text-text-secondary">P/E (Trailing)</td>
                      {compareData.tickers.map(t => <td key={t} className="p-4">{compareData.comparison_table[t]?.pe_trailing ? compareData.comparison_table[t].pe_trailing.toFixed(2) : 'N/A'}</td>)}
                      {compareData.sector_median && <td className="p-4 text-primary bg-primary/5">{compareData.sector_median.pe_trailing ? compareData.sector_median.pe_trailing.toFixed(2) : 'N/A'}</td>}
                    </tr>
                    <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                      <td className="p-4 text-text-secondary">Rev Growth</td>
                      {compareData.tickers.map(t => <td key={t} className={`p-4 ${(compareData.comparison_table[t]?.rev_growth || 0) >= 0 ? 'text-stock-green' : 'text-stock-red'}`}>{((compareData.comparison_table[t]?.rev_growth || 0) * 100).toFixed(1)}%</td>)}
                      {compareData.sector_median && <td className="p-4 text-primary bg-primary/5">{((compareData.sector_median.rev_growth || 0) * 100).toFixed(1)}%</td>}
                    </tr>
                    <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                      <td className="p-4 text-text-secondary">DCF Upside</td>
                      {compareData.tickers.map(t => <td key={t} className={`p-4 font-bold ${(compareData.comparison_table[t]?.dcf_upside_pct || 0) >= 0 ? 'text-stock-green' : 'text-stock-red'}`}>{((compareData.comparison_table[t]?.dcf_upside_pct || 0)).toFixed(1)}%</td>)}
                      {compareData.sector_median && <td className="p-4 text-primary bg-primary/5 font-bold">{((compareData.sector_median.dcf_upside_pct || 0)).toFixed(1)}%</td>}
                    </tr>
                    <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                      <td className="p-4 text-text-secondary">ROE</td>
                      {compareData.tickers.map(t => <td key={t} className="p-4">{((compareData.comparison_table[t]?.roe || 0) * 100).toFixed(1)}%</td>)}
                      {compareData.sector_median && <td className="p-4 text-primary bg-primary/5">{((compareData.sector_median.roe || 0) * 100).toFixed(1)}%</td>}
                    </tr>
                    <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                      <td className="p-4 text-text-secondary">Profit Margin</td>
                      {compareData.tickers.map(t => <td key={t} className="p-4">{((compareData.comparison_table[t]?.profit_margin || 0) * 100).toFixed(1)}%</td>)}
                      {compareData.sector_median && <td className="p-4 text-primary bg-primary/5">{((compareData.sector_median.profit_margin || 0) * 100).toFixed(1)}%</td>}
                    </tr>
                    <tr className="hover:bg-dark-bg/30 border-b border-dark-border/50">
                      <td className="p-4 text-text-secondary">Piotroski Score</td>
                      {compareData.tickers.map(t => <td key={t} className="p-4">{compareData.comparison_table[t]?.piotroski || '-'}</td>)}
                      {compareData.sector_median && <td className="p-4 text-primary bg-primary/5">{compareData.sector_median.piotroski || '-'}</td>}
                    </tr>
                    
                    {/* Advanced Metrics Expansion */}
                    {showAdvancedMetrics && (
                      <>
                        <tr className="border-b border-dark-border/50 bg-dark-bg/50">
                          <td colSpan={compareData.tickers.length + 2} className="p-2 text-xs font-bold text-text-muted uppercase tracking-wider text-center">
                            Advanced Financial & Technical Data
                          </td>
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">Current Price</td>
                          {compareData.tickers.map(t => <td key={t} className="p-4 font-mono">${compareData.comparison_table[t]?.price ? compareData.comparison_table[t].price.toFixed(2) : 'N/A'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">Quant Rating</td>
                          {compareData.tickers.map(t => <td key={t} className={`p-4 font-bold ${compareData.comparison_table[t]?.rating === 'BUY' ? 'text-stock-green' : compareData.comparison_table[t]?.rating === 'SELL' ? 'text-stock-red' : 'text-text-muted'}`}>{compareData.comparison_table[t]?.rating || '-'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">DCF Fair Value</td>
                          {compareData.tickers.map(t => <td key={t} className="p-4 font-mono">{compareData.comparison_table[t]?.dcf_fair_value ? `$${compareData.comparison_table[t].dcf_fair_value.toFixed(2)}` : 'N/A'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">Altman Z-Score</td>
                          {compareData.tickers.map(t => <td key={t} className="p-4">{compareData.comparison_table[t]?.altman_z ? compareData.comparison_table[t].altman_z.toFixed(2) : '-'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">Beta</td>
                          {compareData.tickers.map(t => <td key={t} className="p-4">{compareData.comparison_table[t]?.beta ? compareData.comparison_table[t].beta.toFixed(2) : '-'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">RSI (14D)</td>
                          {compareData.tickers.map(t => <td key={t} className={`p-4 ${compareData.comparison_table[t]?.rsi > 70 ? 'text-stock-red' : compareData.comparison_table[t]?.rsi < 30 ? 'text-stock-green' : ''}`}>{compareData.comparison_table[t]?.rsi ? compareData.comparison_table[t].rsi.toFixed(1) : '-'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">Trend</td>
                          {compareData.tickers.map(t => <td key={t} className="p-4 text-xs capitalize">{compareData.comparison_table[t]?.trend ? compareData.comparison_table[t].trend.replace('_', ' ') : '-'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="border-b border-dark-border/50 hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">Return (1Y)</td>
                          {compareData.tickers.map(t => <td key={t} className={`p-4 ${compareData.comparison_table[t]?.total_return_1y >= 0 ? 'text-stock-green' : 'text-stock-red'}`}>{compareData.comparison_table[t]?.total_return_1y ? `${compareData.comparison_table[t].total_return_1y.toFixed(1)}%` : '-'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                        <tr className="hover:bg-dark-bg/30">
                          <td className="p-4 text-text-secondary">Max Drawdown</td>
                          {compareData.tickers.map(t => <td key={t} className="p-4 text-stock-red">{compareData.comparison_table[t]?.max_drawdown_1y ? `${compareData.comparison_table[t].max_drawdown_1y.toFixed(1)}%` : '-'}</td>)}
                          {compareData.sector_median && <td className="p-4 bg-primary/5"></td>}
                        </tr>
                      </>
                    )}
                  </tbody>
                </table>
              </div>
              <div 
                className="bg-dark-bg/40 border-t border-dark-border p-3 text-center cursor-pointer hover:bg-dark-bg/60 transition-colors flex items-center justify-center gap-2 text-sm font-bold text-primary"
                onClick={() => setShowAdvancedMetrics(!showAdvancedMetrics)}
              >
                {showAdvancedMetrics ? (
                  <><ChevronUp size={16} /> Hide Advanced Metrics</>
                ) : (
                  <><ChevronDown size={16} /> Show Advanced Metrics (Correlation, Risk, DCF, etc)</>
                )}
              </div>
            </div>

            <div className="bg-dark-card border border-dark-border rounded-xl shadow-lg p-5 flex flex-col">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <ShieldCheck className="text-primary" size={20} /> AI Categorization
              </h2>
              <div className="space-y-4 flex-1">
                {compareData.best_for && Object.entries(compareData.best_for).map(([category, info]) => {
                  const isExpanded = expandedCategories[category];
                  return (
                    <div key={category} className="bg-dark-bg border border-dark-border/80 rounded-lg transition-all hover:border-primary/40 group overflow-hidden">
                      <div 
                        className="p-4 cursor-pointer flex flex-col gap-2"
                        onClick={() => setExpandedCategories(prev => ({ ...prev, [category]: !prev[category] }))}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
                            {category.replace('_', ' ')}
                          </span>
                          <div className="flex items-center gap-3">
                            <span className="text-sm font-black text-primary px-2 py-0.5 bg-primary/10 rounded">{info.ticker}</span>
                            {info.all_assessments && info.all_assessments.length > 0 && (
                              <button className="text-text-muted hover:text-white transition-colors">
                                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                              </button>
                            )}
                          </div>
                        </div>
                        <p className="text-xs text-text-secondary leading-relaxed group-hover:text-text-primary transition-colors pr-6">{info.reason}</p>
                      </div>
                      
                      {/* Expanded Section for all other assessments */}
                      {isExpanded && info.all_assessments && info.all_assessments.length > 0 && (
                        <div className="px-4 pb-4 pt-2 border-t border-dark-border/50 bg-black/20">
                          <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-3">All Assessments</div>
                          <div className="space-y-3">
                            {info.all_assessments.filter(a => a.ticker !== info.ticker).map((assessment, idx) => (
                              <div key={idx} className="flex flex-col gap-1">
                                <span className="text-xs font-bold text-white">{assessment.ticker}</span>
                                <p className="text-xs text-text-secondary leading-snug">{assessment.analysis}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Rankings */}
          <div className="bg-dark-card border border-dark-border rounded-xl shadow-lg p-6">
            <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <BarChart2 className="text-primary" size={20} /> Metric Rankings (Top 3)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {compareData.rankings && compareData.rankings.by_metric && Object.entries(compareData.rankings.by_metric).map(([metric, ranks]) => (
                <div key={metric} className="bg-dark-bg rounded-lg p-4 border border-dark-border">
                  <div className="text-xs font-bold text-text-muted uppercase tracking-wider mb-3 border-b border-dark-border/50 pb-2">{metric.replace('_', ' ')}</div>
                  <div className="space-y-2">
                    {ranks.map((r, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <span className={`w-5 h-5 flex items-center justify-center rounded-full text-[10px] font-bold ${i === 0 ? 'bg-yellow-500/20 text-yellow-500' : i === 1 ? 'bg-gray-400/20 text-gray-300' : 'bg-orange-700/20 text-orange-600'}`}>
                            {r.rank}
                          </span>
                          <span className="font-bold text-white">{r.ticker}</span>
                        </div>
                        <span className="text-text-secondary text-xs">{typeof r.value === 'number' ? r.value.toFixed(2) : r.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Advanced Raw Data Tables (Only shown when expanded) */}
          {showAdvancedMetrics && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in">
              {/* Correlation Matrix */}
              {compareData.correlation && (
                <div className="bg-dark-card border border-dark-border rounded-xl shadow-lg p-6">
                  <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Activity className="text-primary" size={20} /> Correlation Matrix (1Y)
                  </h2>
                  <p className="text-xs text-text-secondary mb-4">Values close to 1 mean stocks move together. Close to 0 means they move independently (good for diversification).</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-center whitespace-nowrap">
                      <thead>
                        <tr className="text-xs font-bold text-text-muted">
                          <th className="p-2 border-b border-r border-dark-border"></th>
                          {compareData.tickers.map(t => <th key={t} className="p-2 border-b border-dark-border">{t}</th>)}
                        </tr>
                      </thead>
                      <tbody className="text-sm">
                        {compareData.tickers.map(t1 => (
                          <tr key={t1}>
                            <th className="p-2 border-r border-b border-dark-border/50 text-text-muted">{t1}</th>
                            {compareData.tickers.map(t2 => {
                              const val = compareData.correlation[t1]?.[t2];
                              let colorClass = 'text-white';
                              if (val > 0.8) colorClass = 'text-stock-red font-bold'; // High correlation
                              else if (val < 0.3) colorClass = 'text-stock-green font-bold'; // Low correlation
                              return (
                                <td key={t2} className={`p-2 border-b border-dark-border/50 ${colorClass}`}>
                                  {val !== undefined ? val.toFixed(2) : '-'}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      )}

    </PageLayout>
  );
};

export default ComparePage;
