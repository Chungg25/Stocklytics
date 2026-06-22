import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Home, ChevronRight, LayoutList, Grid, Plus, ChevronDown } from 'lucide-react';
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
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/stocks`)
      .then(res => res.json())
      .then(data => {
        setStocks(data);
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

  const displayedStocks = useMemo(() => {
    if (selectedSector === "All Sectors") return stocks;
    return stocks.filter(s => s.sector === selectedSector);
  }, [stocks, selectedSector]);

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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Stock Screener</h1>
        <p className="text-text-muted text-sm">Filter and analyze US stocks with our advanced screening tools.</p>
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
      <div className="bg-dark-bg rounded-lg border border-dark-border overflow-hidden">
        <StockTable stocks={displayedStocks} loading={loading} />
      </div>

      {/* Floating Ask AI Button */}
      <button className="fixed bottom-8 right-8 w-14 h-14 bg-primary hover:bg-primary-hover rounded-full shadow-lg shadow-primary/30 flex items-center justify-center text-white transition-transform hover:scale-105 z-50">
        <div className="relative">
          <span className="absolute -top-6 -right-2 text-[10px] font-bold text-primary whitespace-nowrap">ASK AI</span>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/></svg>
        </div>
      </button>

    </PageLayout>
  );
};

export default TodayPage;
