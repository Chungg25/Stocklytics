import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Home, ChevronRight, LayoutList, Grid, Plus, ChevronDown, Search, Loader2 } from 'lucide-react';
import StockTable from '../components/screener/StockTable';
import PageLayout from '../components/layout/PageLayout';

const FilterButton = ({ label, icon: Icon, rightIcon: RightIcon, active }) => (
  <button className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border transition-colors
    ${active ? 'border-primary text-primary bg-primary/10' : 'border-dark-border text-text-primary hover:bg-dark-hover'}`}>
    {Icon && <Icon size={14} />}
    {label}
    {RightIcon && <RightIcon size={14} className={active ? "text-primary" : "text-text-muted"} />}
  </button>
);

const FilterInputBadge = ({ label, filterKey, currentFilter, onApply, onClear }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [minVal, setMinVal] = useState(currentFilter?.min || '');
  const [maxVal, setMaxVal] = useState(currentFilter?.max || '');
  const ref = useRef(null);
  
  const isActive = !!currentFilter;

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleApply = () => {
    if (minVal === '' && maxVal === '') {
      onClear(filterKey);
    } else {
      onApply(filterKey, { 
        min: minVal !== '' ? Number(minVal) : null, 
        max: maxVal !== '' ? Number(maxVal) : null 
      });
    }
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={ref}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors
          ${isActive ? 'bg-primary/20 text-primary border-primary/50' : 'bg-[#1A2234] text-text-primary hover:bg-[#252E42] border-[#2D3748]'}`}>
        {label} 
        {isActive ? (
           <span className="ml-1 bg-primary text-dark-bg px-1.5 py-0.5 rounded-full text-[10px]">
             {currentFilter.min !== null ? `>${currentFilter.min}` : ''} 
             {currentFilter.max !== null ? ` <${currentFilter.max}` : ''}
           </span>
        ) : <Plus size={12} className="text-text-muted" />}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-48 bg-[#151C2C] border border-dark-border rounded-lg shadow-xl z-30 p-3">
          <div className="text-xs font-semibold text-white mb-2">{label} Filter</div>
          <div className="flex items-center gap-2 mb-3">
            <input 
              type="number" 
              placeholder="Min" 
              value={minVal} 
              onChange={e => setMinVal(e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-primary"
            />
            <span className="text-text-muted">-</span>
            <input 
              type="number" 
              placeholder="Max" 
              value={maxVal} 
              onChange={e => setMaxVal(e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-primary"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={() => { setMinVal(''); setMaxVal(''); onClear(filterKey); setIsOpen(false); }} className="flex-1 py-1.5 text-xs bg-dark-bg border border-dark-border rounded text-text-muted hover:text-white">Clear</button>
            <button onClick={handleApply} className="flex-1 py-1.5 text-xs bg-primary text-dark-bg rounded font-semibold hover:bg-primary/90">Apply</button>
          </div>
        </div>
      )}
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

const TodayPage = () => {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [selectedSector, setSelectedSector] = useState("All Sectors");
  const [isSectorDropdownOpen, setIsSectorDropdownOpen] = useState(false);
  
  // Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  
  // Parametric Filters State (e.g. { price: {min: 10, max: 100}, change: {min: 5, max: null} })
  const [activeFilters, setActiveFilters] = useState({});
  
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/stocks`)
      .then(res => res.json())
      .then(data => {
        setStocks(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Lỗi khi tải dữ liệu:", err);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsSectorDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const sectors = useMemo(() => {
    const uniqueSectors = new Set(stocks.map(s => s.sector).filter(Boolean));
    return ["All Sectors", ...Array.from(uniqueSectors).sort()];
  }, [stocks]);

  const handleSearch = async (e) => {
    e.preventDefault();
    const query = searchQuery.trim().toUpperCase();
    if (!query) return;

    const existsLocally = stocks.some(s => s.ticker === query || s.name.toUpperCase().includes(query));
    if (existsLocally) return;

    setIsSearching(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/stocks/${query}`);
      const data = await res.json();
      if (data.status === 'success' && data.data) {
        setStocks(prev => [data.data, ...prev]);
        setSearchQuery("");
      } else {
        alert("Không tìm thấy mã cổ phiếu: " + query);
      }
    } catch (err) {
      console.error(err);
      alert("Lỗi kết nối khi tìm kiếm.");
    } finally {
      setIsSearching(false);
    }
  };

  const applyFilter = (key, bounds) => {
    setActiveFilters(prev => ({ ...prev, [key]: bounds }));
  };

  const clearFilter = (key) => {
    setActiveFilters(prev => {
      const newFilters = { ...prev };
      delete newFilters[key];
      return newFilters;
    });
  };

  const filteredStocks = useMemo(() => {
    let result = stocks;
    
    // 1. Sector Filter
    if (selectedSector !== "All Sectors") {
      result = result.filter(s => s.sector === selectedSector);
    }
    
    // 2. Search Filter
    if (searchQuery.trim() !== "") {
      const query = searchQuery.toLowerCase();
      result = result.filter(s => 
        (s.ticker || "").toLowerCase().includes(query) || 
        (s.name || "").toLowerCase().includes(query)
      );
    }
    
    // 3. Parametric Filters
    Object.entries(activeFilters).forEach(([key, bounds]) => {
      result = result.filter(s => {
        let val = 0;
        if (key === 'price') val = s.price;
        if (key === 'change') val = s.change;
        if (key === 'marketCap') val = parseMarketCap(s.marketCap);
        if (key === 'score') val = s.score;
        if (key === 'roi1y') val = s.roi1y;
        
        if (bounds.min !== null && val < bounds.min) return false;
        if (bounds.max !== null && val > bounds.max) return false;
        return true;
      });
    });

    return result;
  }, [stocks, selectedSector, searchQuery, activeFilters]);

  return (
    <PageLayout>
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-text-muted mb-6">
        <Home size={14} />
        <span className="hover:text-white cursor-pointer">Home</span>
        <ChevronRight size={14} />
        <span className="text-text-primary">Stock Screener</span>
      </div>

      {/* Header Info */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Stock Screener</h1>
          <p className="text-text-muted text-sm">Filter and analyze US stocks with our advanced screening tools.</p>
        </div>
        
        {/* Search Bar */}
        <form onSubmit={handleSearch} className="relative w-full md:w-72">
          {isSearching ? (
            <Loader2 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary animate-spin" />
          ) : (
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          )}
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search symbol (e.g. AAPL)..." 
            className="w-full bg-dark-card border border-dark-border rounded-lg py-2 pl-10 pr-4 text-sm text-white focus:outline-none focus:border-primary transition-colors"
          />
        </form>
      </div>

      {/* Action Bar (Filters) */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative" ref={dropdownRef}>
            <div onClick={() => setIsSectorDropdownOpen(!isSectorDropdownOpen)} className="cursor-pointer">
              <FilterButton label={selectedSector === "All Sectors" ? "All Sectors" : selectedSector} rightIcon={ChevronDown} active={true} />
            </div>
            {isSectorDropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-[#151C2C] border border-dark-border rounded-md shadow-lg z-20 py-1 max-h-60 overflow-y-auto no-scrollbar">
                {sectors.map(sector => (
                  <button 
                    key={sector} 
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-dark-hover transition-colors ${selectedSector === sector ? 'text-primary' : 'text-text-primary'}`}
                    onClick={() => {
                      setSelectedSector(sector);
                      setIsSectorDropdownOpen(false);
                    }}
                  >
                    {sector}
                  </button>
                ))}
              </div>
            )}
          </div>
          <FilterButton label="Columns" icon={LayoutList} />
          <FilterButton label="Filters" icon={LayoutList} active={true} />
          
          <div className="h-6 w-px bg-dark-border mx-1 hidden sm:block"></div>
          
          <FilterInputBadge label="Price ($)" filterKey="price" currentFilter={activeFilters.price} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="Price Change (%)" filterKey="change" currentFilter={activeFilters.change} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="Market Cap" filterKey="marketCap" currentFilter={activeFilters.marketCap} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="Score" filterKey="score" currentFilter={activeFilters.score} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="ROI% 1Y" filterKey="roi1y" currentFilter={activeFilters.roi1y} onApply={applyFilter} onClear={clearFilter} />
        </div>
        
        <div className="flex items-center gap-2 border border-dark-border rounded-md p-1 bg-dark-bg">
          <button className="p-1 rounded bg-dark-hover text-white"><LayoutList size={16} /></button>
          <button className="p-1 rounded text-text-muted hover:text-white"><Grid size={16} /></button>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-dark-bg rounded-lg border border-dark-border overflow-hidden mb-4">
        <StockTable 
          stocks={filteredStocks} 
          loading={loading} 
        />
      </div>

    </PageLayout>
  );
};

export default TodayPage;
