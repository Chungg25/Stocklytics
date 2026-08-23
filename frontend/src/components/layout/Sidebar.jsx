import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutGrid, Briefcase, Eye, Filter, List, 
  TrendingUp, BookOpen, MessageCircle
} from 'lucide-react';

const navItems = [
  { icon: LayoutGrid, label: 'TODAY', id: 'today', path: '/today' },
  { icon: Briefcase, label: 'PORTFOLIO', id: 'portfolio', path: '/portfolio' },
  { icon: Eye, label: 'WATCHLIST', id: 'watchlist', path: '/portfolio' },
  { icon: Filter, label: 'SCREENERS', id: 'screeners', path: '/screeners' },
  { icon: List, label: 'COMPARE', id: 'compare', path: '/compare' },
  { icon: TrendingUp, label: 'CHART', id: 'chart', path: '/chart' },
  { icon: BookOpen, label: 'BACKTEST', id: 'backtest', path: '/backtest' },
  { icon: MessageCircle, label: 'AI CHAT', id: 'ai-chat', path: '/chat' },
];

const Sidebar = () => {
  return (
    <div className="w-20 md:w-24 bg-dark-sidebar h-screen fixed left-0 top-0 flex flex-col items-center py-4 border-r border-dark-border overflow-y-auto no-scrollbar">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink 
            key={item.id}
            to={item.path}
            className={({ isActive }) => `w-full flex flex-col items-center justify-center py-3 transition-colors ${
              isActive 
                ? 'text-primary bg-[#1e293b]/50 border-r-2 border-primary' 
                : 'text-text-muted hover:text-text-primary hover:bg-dark-hover'
            }`}
          >
            <Icon size={20} className="mb-1" />
            <span className="text-[10px] uppercase font-semibold text-center leading-tight px-1">
              {item.label}
            </span>
          </NavLink>
        );
      })}
    </div>
  );
};

export default Sidebar;
