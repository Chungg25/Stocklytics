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

const FilterBadge = ({ label }) => (
  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-[#1A2234] text-text-primary hover:bg-[#252E42] border border-[#2D3748] transition-colors">
    {label} <Plus size={12} className="text-text-muted" />
  </button>
);

const TodayPage = () => {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSector, setSelectedSector] = useState("All Sectors");
  const [isSectorDropdownOpen, setIsSectorDropdownOpen] = useState(false);
  
  // Search & Pagination State
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;
  
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

  // Handle Dynamic Search
  const handleSearch = async (e) => {
    e.preventDefault();
    const query = searchQuery.trim().toUpperCase();
    if (!query) return;

    // Check if we already have it locally
    const existsLocally = stocks.some(s => s.ticker === query || s.name.toUpperCase().includes(query));
    if (existsLocally) {
      setCurrentPage(1);
      return;
    }

    // Not found locally -> fetch from backend
    setIsSearching(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/stocks/${query}`);
      const data = await res.json();
      if (data.status === 'success' && data.data) {
        // Add to our list
        setStocks(prev => [data.data, ...prev]);
        setSearchQuery("");
        setCurrentPage(1);
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

  const filteredStocks = useMemo(() => {
    let result = stocks;
    if (selectedSector !== "All Sectors") {
      result = result.filter(s => s.sector === selectedSector);
    }
    if (searchQuery.trim() !== "") {
      const query = searchQuery.toLowerCase();
      result = result.filter(s => 
        s.ticker.toLowerCase().includes(query) || 
        s.name.toLowerCase().includes(query)
      );
    }
    return result;
  }, [stocks, selectedSector, searchQuery]);

  // Pagination Logic
  const totalEntries = filteredStocks.length;
  const totalPages = Math.ceil(totalEntries / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = Math.min(startIndex + itemsPerPage, totalEntries);
  
  const displayedStocks = filteredStocks.slice(startIndex, endIndex);

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
            placeholder="Search symbol (e.g. AAPL) and Enter..." 
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
              <div className="absolute top-full left-0 mt-1 w-48 bg-[#151C2C] border border-dark-border rounded-md shadow-lg z-20 py-1">
                {sectors.map(sector => (
                  <button 
                    key={sector} 
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-dark-hover transition-colors ${selectedSector === sector ? 'text-primary' : 'text-text-primary'}`}
                    onClick={() => {
                      setSelectedSector(sector);
                      setIsSectorDropdownOpen(false);
                      setCurrentPage(1);
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
          
          <FilterBadge label="Price" />
          <FilterBadge label="Price Change (%)" />
          <FilterBadge label="Market Cap" />
          <FilterBadge label="Dividend Yield (%)" />
          <FilterBadge label="P/E Ratio" />
          <FilterBadge label="EPS" />
        </div>
        
        <div className="flex items-center gap-2 border border-dark-border rounded-md p-1 bg-dark-bg">
          <button className="p-1 rounded bg-dark-hover text-white"><LayoutList size={16} /></button>
          <button className="p-1 rounded text-text-muted hover:text-white"><Grid size={16} /></button>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-dark-bg rounded-lg border border-dark-border overflow-hidden mb-4">
        <StockTable stocks={displayedStocks} loading={loading} />
      </div>
      
      {/* Pagination Footer */}
      {!loading && totalEntries > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-text-muted">
          <div>
            Showing <strong className="text-white">{startIndex + 1}</strong> to <strong className="text-white">{endIndex}</strong>
          </div>
          <div className="flex items-center gap-2">
            <button 
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              className="px-3 py-1 rounded bg-dark-card border border-dark-border hover:bg-dark-hover hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <span className="px-3">
              Page {currentPage} / {totalPages}
            </span>
            <button 
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              className="px-3 py-1 rounded bg-dark-card border border-dark-border hover:bg-dark-hover hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

    </PageLayout>
  );
};

export default TodayPage;
