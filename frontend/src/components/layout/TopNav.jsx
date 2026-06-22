import React from 'react';
import { Search, Sun, Sparkles, Wrench, Crown, Target, ChevronDown } from 'lucide-react';

const TopNav = () => {
  return (
    <div className="h-16 flex items-center justify-between px-6 bg-dark-bg border-b border-dark-border ml-20 md:ml-24">
      
      {/* Left: Logo & Links */}
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2 cursor-pointer">
          <Target size={24} className="text-primary" />
          <span className="text-xl font-bold text-white tracking-wide">Stocklytics</span>
        </div>
        
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-text-primary">
          <a href="#" className="flex items-center gap-1.5 hover:text-primary transition-colors">
            <Sparkles size={16} className="text-yellow-500" /> AI Picks
          </a>
          <a href="#" className="flex items-center gap-1.5 hover:text-primary transition-colors">
            <Wrench size={16} className="text-text-muted" /> Tools <ChevronDown size={14} className="text-text-muted ml-0.5" />
          </a>
          <a href="#" className="flex items-center gap-1.5 hover:text-primary transition-colors">
            <Crown size={16} className="text-text-muted" /> Best Stocks <ChevronDown size={14} className="text-text-muted ml-0.5" />
          </a>
        </nav>
      </div>

      {/* Right: Search, Theme, Auth */}
      <div className="flex items-center gap-4">
        <div className="relative hidden lg:block">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input 
            type="text" 
            placeholder="Search 10,000+ stocks..." 
            className="bg-[#1A2234] border border-[#2D3748] rounded-full py-1.5 pl-10 pr-4 text-sm w-64 text-text-primary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder-text-muted transition-all"
          />
        </div>
        
        <button className="w-8 h-8 rounded-full bg-[#1A2234] flex items-center justify-center text-text-muted hover:text-white transition-colors">
          <Sun size={16} />
        </button>
        
        <button className="text-sm font-medium text-text-primary hover:text-white transition-colors px-2">
          Login
        </button>
        <button className="text-sm font-medium bg-primary hover:bg-primary-hover text-white py-1.5 px-4 rounded-md transition-colors">
          Sign Up
        </button>
      </div>

    </div>
  );
};

export default TopNav;
