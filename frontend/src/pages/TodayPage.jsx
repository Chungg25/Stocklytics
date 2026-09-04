import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Home, ChevronRight, LayoutList, Grid, Plus, ChevronDown, Search, Loader2, Sparkles, Trophy, Cpu, Zap } from 'lucide-react';
import StockTable from '../components/screener/StockTable';
import StockGrid from '../components/screener/StockGrid';
import PageLayout from '../components/layout/PageLayout';
import AISuggestionModal from '../components/screener/AISuggestionModal';

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
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200
          ${isActive 
            ? 'bg-primary/10 text-primary border-primary hover:bg-primary/20 shadow-[0_0_10px_rgba(37,99,235,0.2)]' 
            : 'bg-[#151C2C] text-text-primary hover:bg-[#1A2234] border-dark-border hover:border-text-muted'}`}>
        {label} 
        {isActive ? (
           <span className="ml-1 bg-primary text-white px-1.5 py-0.5 rounded-full text-[10px] font-bold">
             {currentFilter.min !== null ? `>${currentFilter.min}` : ''}
             {currentFilter.min !== null && currentFilter.max !== null ? ' ' : ''}
             {currentFilter.max !== null ? `<${currentFilter.max}` : ''}
           </span>
        ) : <Plus size={12} className="text-text-muted transition-transform group-hover:rotate-90" />}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-[#151C2C]/95 backdrop-blur-xl border border-dark-border rounded-xl shadow-2xl z-30 p-4 animate-in fade-in slide-in-from-top-2">
          <div className="text-sm font-semibold text-white mb-4 flex items-center justify-between">
            {label} 
            <span className="text-[10px] bg-dark-hover px-2 py-1 rounded text-text-muted font-normal uppercase tracking-wider">Filter</span>
          </div>
          
          <div className="space-y-3 mb-5">
            <div>
              <label className="text-xs text-text-muted mb-1 block">Minimum Value</label>
              <div className="relative">
                <input 
                  type="number" 
                  placeholder="e.g. 10" 
                  value={minVal} 
                  onChange={e => setMinVal(e.target.value)}
                  className="w-full bg-[#0D111A] border border-dark-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Maximum Value</label>
              <div className="relative">
                <input 
                  type="number" 
                  placeholder="e.g. 500" 
                  value={maxVal} 
                  onChange={e => setMaxVal(e.target.value)}
                  className="w-full bg-[#0D111A] border border-dark-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
              </div>
            </div>
          </div>
          
          <div className="flex gap-2">
            <button 
              onClick={() => { setMinVal(''); setMaxVal(''); onClear(filterKey); setIsOpen(false); }} 
              className="flex-1 py-2 text-xs font-medium bg-[#1A2234] border border-dark-border rounded-lg text-text-muted hover:text-white hover:bg-dark-hover transition-colors"
            >
              Reset
            </button>
            <button 
              onClick={handleApply} 
              className="flex-1 py-2 text-xs font-semibold bg-primary text-white rounded-lg shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all"
            >
              Apply Filter
            </button>
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
  
  // View Mode State
  const [viewMode, setViewMode] = useState('list'); // 'list' | 'grid'

  // Parametric Filters State (e.g. { price: {min: 10, max: 100}, change: {min: 5, max: null} })
  const [activeFilters, setActiveFilters] = useState({});
  
  // AI Suggestion State
  const [showSuggestModal, setShowSuggestModal] = useState(false);
  const [suggestData, setSuggestData] = useState(null);
  const [isLoadingSuggest, setIsLoadingSuggest] = useState(false);
  const [suggestPrompt, setSuggestPrompt] = useState("");

  const handleSuggest = async (screen = "quality_growth", theme = null) => {
    setIsLoadingSuggest(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/analysis/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screen, theme })
      });
      const result = await res.json();
      if (result.status === 'success') {
        setSuggestData(result.data);
        setShowSuggestModal(true);
      } else {
        alert("Error: " + result.detail);
      }
    } catch (e) {
      alert("Failed to fetch suggestions.");
    } finally {
      setIsLoadingSuggest(false);
    }
  };
  
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/stocks`)
      .then(res => res.json())
      .then(data => {
        setStocks(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading data:", err);
        setLoading(false);
      });
  }, []);

  // Columns State
  const allColumns = [
    { id: 'price', label: 'Price' },
    { id: 'change', label: 'Change' },
    { id: 'forecast', label: 'Forecast' },
    { id: 'marketCap', label: 'Market Cap' },
    { id: 'score', label: 'Score' },
    { id: 'sentiment', label: 'Sentiment' },
    { id: 'roi1y', label: 'ROI 1Y' },
    { id: 'history', label: 'Last 30 Days' }
  ];
  const [visibleColumns, setVisibleColumns] = useState(allColumns.map(c => c.id));
  const [isColumnsOpen, setIsColumnsOpen] = useState(false);
  const columnsRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsSectorDropdownOpen(false);
      }
      if (columnsRef.current && !columnsRef.current.contains(event.target)) {
        setIsColumnsOpen(false);
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
        alert("Ticker not found: " + query);
      }
    } catch (err) {
      console.error(err);
      alert("Connection error during search.");
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

      {/* AI Command Bar */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-4 mb-8">
        <div className="relative mb-3">
          <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 text-primary" size={20} />
          <input 
            type="text" 
            value={suggestPrompt}
            onChange={e => setSuggestPrompt(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                const text = suggestPrompt.toLowerCase();
                let screen = 'quality_growth';
                let theme = null;
                
                // Screen parsing
                if (text.includes('value')) screen = 'value';
                else if (text.includes('growth')) screen = 'growth';
                else if (text.includes('momentum')) screen = 'momentum';
                else if (text.includes('dividend') && text.includes('safe')) screen = 'dividend_safety';
                
                // Theme parsing
                if (text.includes('ai') || text.includes('tech') || text.includes('công nghệ')) theme = 'ai';
                else if (text.includes('cloud')) theme = 'cloud';
                else if (text.includes('cybersecurity') || text.includes('bảo mật')) theme = 'cybersecurity';
                else if (text.includes('ev') || text.includes('xe điện')) theme = 'ev';
                else if (text.includes('health') || text.includes('y tế')) theme = 'healthcare_innovation';
                else if (text.includes('energy') || text.includes('năng lượng')) theme = 'energy';
                else if (text.includes('dividend') || text.includes('cổ tức')) theme = 'dividend';
                else if (text.includes('fintech') || text.includes('tài chính')) theme = 'fintech';
                
                handleSuggest(screen, theme);
              }
            }}
            placeholder="Ask AI (e.g., Build a Tech stock portfolio...)" 
            className="w-full bg-[#0D111A] border border-dark-border rounded-xl py-3 pl-12 pr-12 text-sm text-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 transition-all shadow-inner"
          />
          {isLoadingSuggest && (
            <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 text-primary animate-spin" size={20} />
          )}
        </div>
        
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-text-muted mr-2 font-medium">Quick Suggestions:</span>
          <button onClick={() => handleSuggest('quality_growth')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-colors border border-primary/20">
            <Trophy size={14} /> Quality Growth
          </button>
          <button onClick={() => handleSuggest('growth', 'ai')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#8b5cf6]/10 text-[#8b5cf6] text-xs font-semibold hover:bg-[#8b5cf6]/20 transition-colors border border-[#8b5cf6]/20">
            <Cpu size={14} /> Tech & AI Portfolio
          </button>
          <button onClick={() => handleSuggest('value')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stock-green/10 text-stock-green text-xs font-semibold hover:bg-stock-green/20 transition-colors border border-stock-green/20">
            <Zap size={14} /> Deep Value Picks
          </button>
          
          {suggestData && (
            <button onClick={() => setShowSuggestModal(true)} className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-dark-bg text-text-muted text-xs hover:text-white transition-colors border border-dark-border hover:border-text-muted">
              View Last Result
            </button>
          )}
        </div>
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
          <div className="relative" ref={columnsRef}>
            <div onClick={() => setIsColumnsOpen(!isColumnsOpen)} className="cursor-pointer">
              <FilterButton label="Columns" icon={LayoutList} rightIcon={ChevronDown} />
            </div>
            {isColumnsOpen && (
              <div className="absolute top-full left-0 mt-2 w-48 bg-[#151C2C]/95 backdrop-blur-xl border border-dark-border rounded-xl shadow-2xl z-30 p-2 animate-in fade-in slide-in-from-top-2">
                <div className="text-xs font-semibold text-text-muted mb-2 px-2">Show Columns</div>
                {allColumns.map(col => (
                  <label key={col.id} className="flex items-center gap-2 px-2 py-1.5 hover:bg-dark-hover rounded cursor-pointer transition-colors">
                    <input 
                      type="checkbox"
                      checked={visibleColumns.includes(col.id)}
                      onChange={(e) => {
                        if (e.target.checked) setVisibleColumns([...visibleColumns, col.id]);
                        else setVisibleColumns(visibleColumns.filter(id => id !== col.id));
                      }}
                      className="w-3.5 h-3.5 rounded border-dark-border text-primary focus:ring-0 bg-dark-bg"
                    />
                    <span className="text-sm text-white">{col.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
          
          {Object.keys(activeFilters).length > 0 && (
            <button 
              onClick={() => setActiveFilters({})}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border border-stock-red/50 text-stock-red bg-stock-red/10 hover:bg-stock-red/20 transition-colors"
            >
              Clear Filters
            </button>
          )}
          
          <div className="h-6 w-px bg-dark-border mx-1 hidden sm:block"></div>
          
          <FilterInputBadge label="Price ($)" filterKey="price" currentFilter={activeFilters.price} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="Price Change (%)" filterKey="change" currentFilter={activeFilters.change} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="Market Cap" filterKey="marketCap" currentFilter={activeFilters.marketCap} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="Score" filterKey="score" currentFilter={activeFilters.score} onApply={applyFilter} onClear={clearFilter} />
          <FilterInputBadge label="ROI% 1Y" filterKey="roi1y" currentFilter={activeFilters.roi1y} onApply={applyFilter} onClear={clearFilter} />
        </div>
        
        <div className="flex items-center gap-2 border border-dark-border rounded-md p-1 bg-dark-bg">
          <button 
            onClick={() => setViewMode('list')}
            className={`p-1 rounded transition-colors ${viewMode === 'list' ? 'bg-dark-hover text-white' : 'text-text-muted hover:text-white'}`}
          >
            <LayoutList size={16} />
          </button>
          <button 
            onClick={() => setViewMode('grid')}
            className={`p-1 rounded transition-colors ${viewMode === 'grid' ? 'bg-dark-hover text-white' : 'text-text-muted hover:text-white'}`}
          >
            <Grid size={16} />
          </button>
        </div>
      </div>

      {/* Data View */}
      <div className="bg-dark-bg rounded-lg border border-dark-border overflow-hidden mb-4">
        {viewMode === 'list' ? (
          <StockTable 
            stocks={filteredStocks} 
            loading={loading} 
            visibleColumns={visibleColumns}
          />
        ) : (
          <StockGrid 
            stocks={filteredStocks} 
            loading={loading}
          />
        )}
      </div>

      {/* AI Suggestion Modal */}
      <AISuggestionModal 
        isOpen={showSuggestModal} 
        onClose={() => setShowSuggestModal(false)} 
        data={suggestData} 
      />
    </PageLayout>
  );
};

export default TodayPage;
