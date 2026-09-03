import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Star, Bell, Copy, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

const formatPercent = (val) => {
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
};

const StockCard = ({ stock }) => {
  const navigate = useNavigate();
  const isPositiveChange = stock.change > 0;
  const changeColorClass = isPositiveChange ? 'text-stock-green' : 'text-stock-red';
  
  // Format data for Recharts
  const chartData = stock.history.map((val, index) => ({ uv: val }));
  const chartColor = isPositiveChange ? '#10B981' : '#EF4444';

  return (
    <div 
      className="bg-[#151C2C] border border-dark-border hover:border-primary/50 rounded-xl p-4 transition-all duration-200 shadow-sm hover:shadow-xl hover:shadow-primary/5 group flex flex-col cursor-pointer"
      onClick={() => navigate(`/stock/${stock.ticker}`)}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-white text-lg group-hover:text-primary transition-colors">{stock.ticker}</h3>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-dark-bg text-text-muted border border-dark-border">
              {stock.sector || 'Stock'}
            </span>
          </div>
          <p className="text-xs text-text-muted mt-0.5 line-clamp-1">{stock.name}</p>
        </div>
        
        {/* Quick Actions (Hidden until hover) */}
        <div className="hidden group-hover:flex items-center gap-1.5 text-text-muted bg-dark-bg p-1 rounded-md border border-dark-border">
          <Star size={14} className="hover:text-yellow-500 transition-colors" onClick={(e) => { e.stopPropagation(); }} />
          <Bell size={14} className="hover:text-white transition-colors" onClick={(e) => { e.stopPropagation(); }} />
        </div>
      </div>

      {/* Price Info */}
      <div className="flex items-end gap-3 mb-4">
        <span className="text-2xl font-bold text-white font-mono">${stock.price.toFixed(2)}</span>
        <span className={`font-semibold mb-1 ${changeColorClass}`}>
          {formatPercent(stock.change)}
        </span>
      </div>

      {/* Mini Chart */}
      <div className="h-16 w-full mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <YAxis domain={['dataMin', 'dataMax']} hide />
            <Line type="monotone" dataKey="uv" stroke={chartColor} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Badges/Stats */}
      <div className="mt-auto grid grid-cols-2 gap-2 text-xs">
        <div className="bg-dark-bg p-2 rounded-lg border border-dark-border">
          <div className="text-text-muted mb-1">Mkt Cap</div>
          <div className="font-medium text-white">{stock.marketCap}</div>
        </div>
        <div className="bg-dark-bg p-2 rounded-lg border border-dark-border">
          <div className="text-text-muted mb-1">ROI 1Y</div>
          <div className={`font-medium ${stock.roi1y > 0 ? 'text-stock-green' : 'text-stock-red'}`}>
            {formatPercent(stock.roi1y)}
          </div>
        </div>
        <div className="bg-dark-bg p-2 rounded-lg border border-dark-border flex flex-col justify-center">
          <div className="flex justify-between items-center">
            <span className="text-text-muted">Score</span>
            <span className={`px-1.5 rounded text-[10px] font-bold ${stock.score >= 70 ? 'bg-stock-green/20 text-stock-green' : 'bg-yellow-500/20 text-yellow-500'}`}>
              {stock.score}
            </span>
          </div>
        </div>
        <div className="bg-dark-bg p-2 rounded-lg border border-dark-border flex flex-col justify-center">
          <div className="flex justify-between items-center">
            <span className="text-text-muted">Sent</span>
            <span className={`px-1.5 rounded text-[10px] font-medium ${stock.sentiment === 'Bullish' ? 'bg-stock-green/10 text-stock-green' : 'bg-stock-red/10 text-stock-red'}`}>
              {stock.sentiment === 'Bullish' ? 'Bull' : 'Bear'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

const parseMarketCap = (str) => {
  if (typeof str !== 'string' || !str || str === 'N/A') return 0;
  const val = parseFloat(str.replace(/[^0-9.-]/g, ''));
  if (str.includes('T')) return val * 1e12;
  if (str.includes('B')) return val * 1e9;
  if (str.includes('M')) return val * 1e6;
  return val;
};

const StockGrid = ({ stocks, loading, itemsPerPage = 20 }) => {
  const [sortConfig, setSortConfig] = useState({ key: 'marketCap', direction: 'desc' });
  const [currentPage, setCurrentPage] = useState(1);

  const handleSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) return <ChevronDown size={14} className="opacity-0 group-hover:opacity-50 transition-opacity ml-1"/>;
    return sortConfig.direction === 'asc' ? <ChevronUp size={14} className="ml-1 text-primary"/> : <ChevronDown size={14} className="ml-1 text-primary"/>;
  };

  const sortedStocks = useMemo(() => {
    let sortableItems = [...stocks];
    if (sortConfig.key !== null) {
      sortableItems.sort((a, b) => {
        let aValue = a[sortConfig.key];
        let bValue = b[sortConfig.key];
        
        if (sortConfig.key === 'marketCap') {
          aValue = parseMarketCap(aValue);
          bValue = parseMarketCap(bValue);
        } else if (sortConfig.key === 'ticker') {
          aValue = (a.ticker || "").toLowerCase();
          bValue = (b.ticker || "").toLowerCase();
        } else {
          aValue = aValue ?? 0;
          bValue = bValue ?? 0;
        }

        if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableItems;
  }, [stocks, sortConfig]);

  // Pagination logic
  const totalPages = Math.ceil(sortedStocks.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedStocks = sortedStocks.slice(startIndex, startIndex + itemsPerPage);

  // Reset to page 1 when stocks change or sort changes
  useEffect(() => {
    setCurrentPage(1);
  }, [stocks, sortConfig]);

  return (
    <div className="w-full flex flex-col">
      {/* Grid Sorting Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 border-b border-dark-border bg-dark-card rounded-t-lg">
        <div className="text-sm font-semibold text-white">Grid View ({stocks.length} assets)</div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Sort by:</span>
          <div className="flex bg-[#151C2C] border border-dark-border rounded-md overflow-hidden p-0.5">
            <button 
              onClick={() => handleSort('marketCap')}
              className={`px-3 py-1.5 text-xs font-medium rounded-sm flex items-center transition-colors ${sortConfig.key === 'marketCap' ? 'bg-primary/20 text-primary' : 'text-text-muted hover:text-white hover:bg-dark-hover'}`}
            >
              Mkt Cap {sortConfig.key === 'marketCap' && getSortIcon('marketCap')}
            </button>
            <button 
              onClick={() => handleSort('change')}
              className={`px-3 py-1.5 text-xs font-medium rounded-sm flex items-center transition-colors ${sortConfig.key === 'change' ? 'bg-primary/20 text-primary' : 'text-text-muted hover:text-white hover:bg-dark-hover'}`}
            >
              Change {sortConfig.key === 'change' && getSortIcon('change')}
            </button>
            <button 
              onClick={() => handleSort('roi1y')}
              className={`px-3 py-1.5 text-xs font-medium rounded-sm flex items-center transition-colors ${sortConfig.key === 'roi1y' ? 'bg-primary/20 text-primary' : 'text-text-muted hover:text-white hover:bg-dark-hover'}`}
            >
              ROI {sortConfig.key === 'roi1y' && getSortIcon('roi1y')}
            </button>
          </div>
        </div>
      </div>

      {/* Grid Layout */}
      <div className="p-4 bg-dark-bg min-h-[400px]">
        {loading ? (
          <div className="w-full py-12 text-center text-text-muted">Loading data...</div>
        ) : paginatedStocks.length === 0 ? (
          <div className="w-full py-12 text-center text-text-muted">No stocks found matching the criteria.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
            {paginatedStocks.map(stock => (
              <StockCard key={stock.ticker || stock.id} stock={stock} />
            ))}
          </div>
        )}
      </div>
      
      {/* Pagination Controls */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-end px-4 py-4 border-t border-dark-border bg-[#151C2C] rounded-b-lg mt-auto">
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 text-sm rounded-md border border-dark-border bg-dark-bg text-text-primary hover:text-white hover:bg-dark-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <div className="flex items-center gap-1">
              {[...Array(totalPages)].map((_, i) => {
                const page = i + 1;
                if (
                  page === 1 || 
                  page === totalPages || 
                  (page >= currentPage - 1 && page <= currentPage + 1)
                ) {
                  return (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`min-w-[32px] h-8 flex items-center justify-center rounded-md text-sm transition-colors ${
                        currentPage === page 
                          ? 'bg-primary text-white border-primary font-medium border' 
                          : 'bg-transparent text-text-muted hover:text-white hover:bg-dark-hover border-transparent hover:border-dark-border border'
                      }`}
                    >
                      {page}
                    </button>
                  );
                }
                if (
                  (page === 2 && currentPage > 3) ||
                  (page === totalPages - 1 && currentPage < totalPages - 2)
                ) {
                  return <span key={page} className="text-text-muted px-1">...</span>;
                }
                return null;
              })}
            </div>
            <button 
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 text-sm rounded-md border border-dark-border bg-dark-bg text-text-primary hover:text-white hover:bg-dark-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default StockGrid;
