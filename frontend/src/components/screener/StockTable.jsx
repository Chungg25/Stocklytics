import React, { useState, useMemo, useEffect } from 'react';
import { Star, Bell, Copy, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

const formatPercent = (val) => {
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
};

const StockTableRow = ({ stock }) => {
  const isPositiveChange = stock.change > 0;
  const changeColorClass = isPositiveChange ? 'text-stock-green' : 'text-stock-red';
  
  // Format data for Recharts
  const chartData = stock.history.map((val, index) => ({ uv: val }));
  const chartColor = isPositiveChange ? '#10B981' : '#EF4444';

  return (
    <tr className="border-b border-dark-border hover:bg-dark-hover/50 transition-colors group">
      <td className="py-4 px-2">
        <div className="flex items-center gap-3">
          <div>
            <div className="font-bold text-white flex items-center gap-2">
              {stock.ticker}
              <div className="hidden group-hover:flex items-center gap-1.5 text-text-muted">
                <Star size={14} className="hover:text-yellow-500 cursor-pointer" />
                <Bell size={14} className="hover:text-white cursor-pointer" />
                <Copy size={14} className="hover:text-white cursor-pointer" />
              </div>
            </div>
            <div className="text-xs text-text-muted">{stock.name}</div>
          </div>
        </div>
      </td>
      <td className="py-4 px-2 font-medium text-white">${stock.price.toFixed(2)}</td>
      <td className={`py-4 px-2 font-medium ${changeColorClass}`}>
        {formatPercent(stock.change)}
      </td>
      <td className="py-4 px-2">
        <div className="text-white font-medium">${stock.forecastAmt.toFixed(2)}</div>
        <div className="text-xs text-stock-green">+{stock.forecastPct.toFixed(1)}%</div>
      </td>
      <td className="py-4 px-2 font-medium text-white">{stock.marketCap}</td>
      <td className="py-4 px-2">
        <span className={`px-2 py-1 rounded text-xs font-bold 
          ${stock.score >= 70 ? 'bg-stock-green/20 text-stock-green' : 'bg-yellow-500/20 text-yellow-500'}`}>
          {stock.score}
        </span>
      </td>
      <td className="py-4 px-2">
        <span className={`px-2.5 py-1 rounded text-xs font-medium 
          ${stock.sentiment === 'Bullish' ? 'bg-stock-green/10 text-stock-green' : 'bg-stock-red/10 text-stock-red'}`}>
          {stock.sentiment}
        </span>
      </td>
      <td className={`py-4 px-2 font-medium ${stock.roi1y > 0 ? 'text-stock-green' : 'text-stock-red'}`}>
        {formatPercent(stock.roi1y)}
      </td>
      <td className="py-4 px-2 w-32">
        <div className="h-8 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <YAxis domain={['dataMin', 'dataMax']} hide />
              <Line type="monotone" dataKey="uv" stroke={chartColor} strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </td>
    </tr>
  );
};

const StockTable = ({ stocks, loading, itemsPerPage = 15 }) => {
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

  const parseMarketCap = (str) => {
    if (typeof str !== 'string' || !str || str === 'N/A') return 0;
    const val = parseFloat(str.replace(/[^0-9.-]/g, ''));
    if (str.includes('T')) return val * 1e12;
    if (str.includes('B')) return val * 1e9;
    if (str.includes('M')) return val * 1e6;
    return val;
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
    <div className="w-full overflow-x-auto flex flex-col">
      <table className="w-full text-left text-sm whitespace-nowrap">
        <thead className="bg-[#151C2C] border-b-2 border-dark-border">
          <tr className="text-text-muted text-xs uppercase tracking-wider select-none">
            <th className="py-4 px-3 font-semibold cursor-pointer hover:text-white transition-colors group" onClick={() => handleSort('ticker')}>
              <div className="flex items-center gap-1">COMPANY <Info size={12}/> {getSortIcon('ticker')}</div>
            </th>
            <th className="py-4 px-3 font-semibold cursor-pointer hover:text-white transition-colors group" onClick={() => handleSort('price')}>
              <div className="flex items-center">PRICE <Info size={12} className="inline ml-1"/> {getSortIcon('price')}</div>
            </th>
            <th className="py-4 px-3 font-semibold cursor-pointer hover:text-white transition-colors group" onClick={() => handleSort('change')}>
              <div className="flex items-center">CHANGE <Info size={12} className="inline ml-1"/> {getSortIcon('change')}</div>
            </th>
            <th className="py-4 px-3 font-semibold text-text-muted">
              <div className="flex items-center">FORECAST <Info size={12} className="inline ml-1"/></div>
            </th>
            <th className="py-4 px-3 font-semibold cursor-pointer transition-colors group" onClick={() => handleSort('marketCap')}>
              <div className={`flex items-center ${sortConfig.key === 'marketCap' ? 'text-primary' : 'hover:text-white'}`}>MARKET CAP <Info size={12} className="inline ml-1"/> {getSortIcon('marketCap')}</div>
            </th>
            <th className="py-4 px-3 font-semibold cursor-pointer hover:text-white transition-colors group" onClick={() => handleSort('score')}>
              <div className="flex items-center">SCORE <Info size={12} className="inline ml-1"/> {getSortIcon('score')}</div>
            </th>
            <th className="py-4 px-3 font-semibold text-text-muted">
              <div className="flex items-center">SENTIMENT <Info size={12} className="inline ml-1"/></div>
            </th>
            <th className="py-4 px-3 font-semibold cursor-pointer hover:text-white transition-colors group" onClick={() => handleSort('roi1y')}>
              <div className="flex items-center">ROI% 1Y <Info size={12} className="inline ml-1"/> {getSortIcon('roi1y')}</div>
            </th>
            <th className="py-4 px-3 font-semibold text-text-muted">
              <div className="flex items-center">LAST 30 DAYS <Info size={12} className="inline ml-1"/></div>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan="9" className="text-center py-8 text-text-muted">Loading data...</td></tr>
          ) : (
            paginatedStocks.map(stock => (
              <StockTableRow key={stock.ticker || stock.id} stock={stock} />
            ))
          )}
        </tbody>
      </table>
      
      {/* Pagination Controls */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-4 border-t-2 border-dark-border bg-[#151C2C]">
          <div className="text-sm text-text-muted">
            Showing <span className="text-white font-medium">{startIndex + 1}</span> to <span className="text-white font-medium">{Math.min(startIndex + itemsPerPage, sortedStocks.length)}</span> of <span className="text-white font-medium">{sortedStocks.length}</span> entries
          </div>
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

export default StockTable;
