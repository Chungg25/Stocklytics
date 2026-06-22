import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Home, ChevronRight, Bell, Link as LinkIcon, Cpu, HeartPulse, Building2, ShoppingBag, Zap, MessageSquare, Trophy } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import StockTable from '../components/screener/StockTable';
import PageLayout from '../components/layout/PageLayout';

const categoryMap = {
  'top25': { title: 'Stocklytics Top 25', filter: (s) => true, icon: Trophy },
  'technology': { title: 'Technology Stocks', filter: (s) => s.sector === 'Technology', icon: Cpu },
  'healthcare': { title: 'Healthcare Stocks', filter: (s) => s.sector === 'Healthcare', icon: HeartPulse },
  'financial': { title: 'Financial Services', filter: (s) => s.sector === 'Financial Services', icon: Building2 },
  'consumer': { title: 'Consumer Cyclical', filter: (s) => s.sector === 'Consumer Cyclical', icon: ShoppingBag },
  'energy': { title: 'Energy Stocks', filter: (s) => s.sector === 'Energy', icon: Zap },
  'communication': { title: 'Communication Services', filter: (s) => s.sector === 'Communication Services', icon: MessageSquare }
};

const ScreenerDetailPage = () => {
  const { id } = useParams();
  const category = categoryMap[id] || { title: 'All Stocks', filter: () => true, icon: Trophy };
  const Icon = category.icon;

  const [stocks, setStocks] = useState([]);
  const [benchmarkData, setBenchmarkData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch stocks and benchmark concurrently
      Promise.all([
        fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/stocks`).then(res => res.json()),
        fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/benchmark?sector=${id}`).then(res => res.json())
      ])
    .then(([stocksData, benchmarkData]) => {
      setStocks(stocksData);
      setBenchmarkData(benchmarkData);
      setLoading(false);
    })
    .catch(err => {
      console.error("Error fetching detail data:", err);
      setLoading(false);
    });
  }, [id]);

  const displayedStocks = useMemo(() => {
    return stocks.filter(category.filter);
  }, [stocks, category]);

  // Format data for Recharts tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-dark-card border border-dark-border p-3 rounded-md shadow-lg">
          <p className="text-white font-medium mb-2">{label}</p>
          <p className="text-[#3B82F6] text-sm">
            {category.title}: {payload[0]?.value > 0 ? '+' : ''}{payload[0]?.value}%
          </p>
          <p className="text-text-muted text-sm">
            S&P 500: {payload[1]?.value > 0 ? '+' : ''}{payload[1]?.value}%
          </p>
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
        <Link to="/screeners" className="hover:text-white transition-colors">Screener</Link>
        <ChevronRight size={16} className="mx-2" />
        <span className="text-white">{category.title}</span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="text-primary bg-primary/10 p-2 rounded-md">
            <Icon size={24} />
          </div>
          <h1 className="text-3xl font-bold text-white">{category.title}</h1>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary hover:bg-primary hover:text-white transition-colors rounded-md font-medium mt-4 md:mt-0 border border-primary">
          <Bell size={16} /> Alert
        </button>
      </div>
      <p className="text-text-muted mb-8 max-w-3xl">
        Discover top-performing stocks in this category with our advanced screening tools. Track performance against the S&P 500 benchmark and access key metrics.
      </p>

      {/* Chart Section */}
      <div className="bg-dark-card border border-dark-border rounded-lg p-6 mb-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-white font-semibold text-lg">{category.title} vs S&P 500</h2>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#3B82F6]"></div>
              <span className="text-text-muted">{category.title}</span>
              <span className="text-stock-green font-medium">
                {benchmarkData.length > 0 ? `+${benchmarkData[benchmarkData.length-1].sector}%` : ''}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-text-muted"></div>
              <span className="text-text-muted">S&P 500</span>
              <span className="text-stock-green font-medium">
                {benchmarkData.length > 0 ? `+${benchmarkData[benchmarkData.length-1].sp500}%` : ''}
              </span>
            </div>
          </div>
        </div>

        <div className="h-[300px] w-full">
          {loading ? (
            <div className="w-full h-full flex items-center justify-center text-text-muted">Loading chart data...</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={benchmarkData} margin={{ top: 5, right: 0, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D3348" vertical={false} />
                <XAxis dataKey="date" stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} dy={10} tickFormatter={(val) => val.split('-')[0]} />
                <YAxis stroke="#6B7280" tick={{ fill: '#6B7280', fontSize: 12 }} dx={-10} tickFormatter={(val) => `${val}%`} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="sector" stroke="#3B82F6" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="sp500" stroke="#9CA3AF" strokeWidth={2} strokeDasharray="5 5" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Table Section */}
      <h2 className="text-2xl font-bold text-white mb-6">{category.title}</h2>
      <div className="bg-dark-bg rounded-lg border border-dark-border overflow-hidden">
        <StockTable stocks={displayedStocks} loading={loading} />
      </div>
    </PageLayout>
  );
};

export default ScreenerDetailPage;
