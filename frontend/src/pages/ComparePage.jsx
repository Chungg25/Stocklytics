import React, { useState, useEffect } from 'react';
import { Home, ChevronRight, Activity, Search, X, TrendingUp, Settings } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine, BarChart, Bar, ComposedChart
} from 'recharts';
import PageLayout from '../components/layout/PageLayout';
import ReactMarkdown from 'react-markdown';

const COLORS = ['#00E5FF', '#00E676', '#FF9100', '#D500F9', '#FF1744', '#FFEA00'];

const LastPointLabel = (props) => {
  const { x, y, color, value, index, name, dataLength } = props;

  if (index !== dataLength - 1) {
    return null;
  }

  const valNum = parseFloat(value);
  if (isNaN(valNum)) return null;

  const labelText = `${name} | ${valNum >= 0 ? '+' : ''}${valNum.toFixed(2)}%`;
  const width = name.length * 6 + 55;

  return (
    <g>
      <line x1={x} y1={y} x2={x + 6} y2={y} stroke={color} strokeWidth={1.5} />
      <rect
        x={x + 6}
        y={y - 11}
        width={width}
        height={22}
        rx={3}
        fill={color}
        stroke="#0b0f1a"
        strokeWidth={1}
      />
      <text
        x={x + 6 + width / 2}
        y={y + 4}
        fill="#0b0f1a"
        fontSize={10}
        fontWeight="bold"
        fontFamily="sans-serif"
        textAnchor="middle"
      >
        {labelText}
      </text>
    </g>
  );
};

const timeframes = ['1M', '3M', '6M', '1Y', '3Y', '5Y'];

const ComparePage = () => {
  const [groups, setGroups] = useState({});
  const [selectedGroup, setSelectedGroup] = useState('');
  const [tickers, setTickers] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [timeframe, setTimeframe] = useState('3M');
  const [newGroupName, setNewGroupName] = useState('');

  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);

  // Fetch groups from Google Sheets on mount
  useEffect(() => {
    const fetchGroups = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/trading/groups`);
        const resData = await response.json();
        if (resData.status === 'success') {
          setGroups(resData.groups);
          // Start with an empty selection as requested
        } else {
          setError(resData.message);
        }
      } catch (err) {
        setError("Failed to load stock groups: " + err.message);
      }
    };
    fetchGroups();
  }, []);

  const fetchData = async () => {
    if (tickers.length === 0) {
      setData([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers, timeframe, indicators: [] })
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
  }, [tickers, timeframe]);

  const handleAIAnalysis = async () => {
    if (tickers.length === 0) {
      setError("Please select at least one ticker for AI analysis.");
      return;
    }
    setAiLoading(true);
    setAiResult(null);
    setError(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/ai/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tickers,
          prompt: "Which stock has the fastest expected revenue growth over the next 2 years over 25 % Which stock has the fastest expected EPS growth over the next 2 years over 20 % Which stock has the strongest technical chart today? Which stock has the best combination of growth and valuation? Which stock has the widest competitive moat? Which stock is most likely to outperform over the next 3–5 years? If you were managing a $1 million growth portfolio, which stocks would you buy today and what percentage would you allocate to each? Give each stock an overall score from 0–100, and rank them from best to worst. End with a clear Buy / Hold / Sell / Watch recommendation for every stock"
        })
      });
      const resData = await response.json();
      if (resData.status === 'success') {
        setAiResult(resData.data);
      } else {
        setError(resData.message);
      }
    } catch (err) {
      setError("AI Analysis Failed: " + err.message);
    } finally {
      setAiLoading(false);
    }
  };

  // Handle changing group selection
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
        setError("You can compare a maximum of 50 tickers.");
        return;
      }
      if (!tickers.includes(newTicker)) {
        const updatedTickers = [...tickers, newTicker];
        setTickers(updatedTickers);
        setGroups({
          ...groups,
          [selectedGroup]: updatedTickers
        });
        setError(null);
      }
      setInputValue('');
    }
  };

  const removeTicker = (t) => {
    const updatedTickers = tickers.filter(ticker => ticker !== t);
    setTickers(updatedTickers);
    setGroups({
      ...groups,
      [selectedGroup]: updatedTickers
    });
    setError(null);
  };

  const handleCreateGroup = () => {
    if (!newGroupName.trim()) return;
    const name = newGroupName.trim();
    if (groups[name]) {
      setError("Group already exists!");
      return;
    }
    const updatedGroups = {
      ...groups,
      [name]: []
    };
    setGroups(updatedGroups);
    setSelectedGroup(name);
    setTickers([]);
    setNewGroupName('');
    setError(null);
    setSuccessMsg(null);
  };

  const handleDeleteGroup = () => {
    if (!selectedGroup) return;
    if (window.confirm(`Are you sure you want to delete the group "${selectedGroup}"?`)) {
      const updatedGroups = { ...groups };
      delete updatedGroups[selectedGroup];
      setGroups(updatedGroups);

      const nextGroup = Object.keys(updatedGroups)[0] || '';
      setSelectedGroup(nextGroup);
      setTickers(nextGroup ? updatedGroups[nextGroup] : []);
      setError(null);
      setSuccessMsg(null);
    }
  };

  // Save modified groups back to Google Sheets
  const handleSaveToSheets = async () => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/trading/groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groups })
      });
      const resData = await response.json();
      if (resData.status === 'success') {
        setSuccessMsg("Successfully saved changes to Google Sheets!");
      } else {
        setError(resData.message);
      }
    } catch (err) {
      setError("Failed to save changes: " + err.message);
    } finally {
      setSaving(false);
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
              placeholder={tickers.length >= 50 ? "Maximum 50 tickers reached" : "Add ticker... (max 50)"}
              disabled={tickers.length >= 50}
              className={`bg-transparent text-white outline-none flex-1 min-w-[120px] px-2 text-sm ${tickers.length >= 50 ? 'cursor-not-allowed opacity-50' : ''}`}
            />
          </div>

          {/* Timeframe */}
          <div className="flex items-center bg-dark-bg border border-dark-border rounded-md overflow-hidden">
            {timeframes.map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-4 py-2 text-sm font-medium transition-colors border-r border-dark-border last:border-0 ${timeframe === tf ? 'bg-primary text-white' : 'text-text-muted hover:bg-dark-hover hover:text-white'
                  }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Groups Selection and Management */}
        <div className="flex flex-col gap-6 pt-4 border-t border-dark-border">
          {/* Group Selector Chips */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-text-secondary text-xs font-semibold uppercase tracking-wider mb-1">
              <Settings size={14} className="text-primary" /> <span>Stock Groups</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.keys(groups).map(groupName => (
                <button
                  key={groupName}
                  onClick={() => handleGroupChange(groupName)}
                  className={`px-4 py-2 rounded-full text-xs font-semibold border transition-all ${selectedGroup === groupName
                      ? 'bg-primary border-primary text-white shadow-lg shadow-primary/20 scale-105'
                      : 'bg-dark-bg border-dark-border text-text-secondary hover:border-primary hover:text-white'
                    }`}
                >
                  {groupName}
                </button>
              ))}
            </div>
          </div>

          {/* Group Action Tools: Create, Delete, Save */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-dark-border/40">
            {/* Create Group Tool */}
            <div className="flex items-center gap-2 bg-dark-bg border border-dark-border rounded-md p-1 max-w-sm w-full sm:w-auto">
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="Create custom group name..."
                className="bg-transparent text-white outline-none flex-1 px-3 py-1.5 text-xs placeholder:text-text-muted"
              />
              <button
                onClick={handleCreateGroup}
                className="bg-primary hover:bg-primary-hover text-white px-4 py-1.5 rounded text-xs font-bold transition-all"
              >
                + Create Group
              </button>
            </div>

            {/* Delete / Save Actions */}
            <div className="flex items-center gap-2.5">
              <button
                onClick={handleAIAnalysis}
                disabled={aiLoading || tickers.length === 0}
                className="flex items-center gap-2 bg-primary text-white px-5 py-2 rounded-md text-xs font-extrabold hover:bg-primary-hover disabled:opacity-50 transition-all shadow-md shadow-primary/20"
              >
                {aiLoading ? "Thinking..." : "AI Analysis"}
              </button>
              {selectedGroup && (
                <button
                  onClick={handleDeleteGroup}
                  className="px-4 py-2 rounded border border-stock-red text-stock-red text-xs font-bold hover:bg-stock-red hover:text-white transition-all bg-transparent"
                >
                  Delete Group
                </button>
              )}
              <button
                onClick={handleSaveToSheets}
                disabled={saving || !selectedGroup}
                className="flex items-center gap-2 bg-stock-green text-dark-bg px-5 py-2 rounded-md text-xs font-extrabold hover:bg-stock-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md shadow-stock-green/10"
              >
                {saving ? "Saving..." : "Save Group"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="text-stock-red mb-4 p-4 border border-stock-red/20 bg-stock-red/10 rounded-lg">{error}</div>}
      {successMsg && <div className="text-green mb-4 p-4 border border-green/20 bg-green/10 rounded-lg">{successMsg}</div>}

      {/* Compare Chart Area */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-6 relative min-h-[400px]">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-dark-card/50 backdrop-blur-sm rounded-xl">
            <div className="text-primary font-bold animate-pulse">Loading Chart Data...</div>
          </div>
        )}
        <h2 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider flex items-center gap-2">
          <Activity size={16} /> Percentage Comparison
        </h2>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 120, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D3348" vertical={false} />
              <XAxis dataKey="date" stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} minTickGap={30} />
              <YAxis stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} />
              <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />

              {/* Plot Main Tickers */}
              {tickers.map((t, idx) => (
                <Line
                  key={t}
                  type="monotone"
                  dataKey={`${t}_perf`}
                  name={t}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                  label={<LastPointLabel name={t} dataLength={data.length} color={COLORS[idx % COLORS.length]} />}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI Analysis Result */}
      {(aiLoading || aiResult) && (
        <div className="bg-dark-card border border-dark-border rounded-xl p-6 mt-6 shadow-lg shadow-black/20">
          <div className="flex items-center gap-2 text-primary font-bold mb-6 border-b border-dark-border pb-4">
            <Activity size={20} />
            <h2 className="text-lg">Deep Analysis</h2>
          </div>
          {aiLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
              <p className="text-text-secondary animate-pulse text-sm">Searching the web and analyzing fundamentals / technicals...</p>
            </div>
          ) : (
            <div className="prose prose-invert max-w-none text-sm text-text-primary prose-headings:text-white prose-a:text-primary hover:prose-a:text-primary-hover prose-strong:text-stock-green prose-p:leading-relaxed">
              <ReactMarkdown>{aiResult}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </PageLayout>
  );
};

export default ComparePage;
