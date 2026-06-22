import React from 'react';
import { Home, ChevronRight, Plus, Trophy, Cpu, HeartPulse, Building2, ShoppingBag, Zap, MessageSquare, Search, LayoutList } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PageLayout from '../components/layout/PageLayout';

const categories = [
  { id: 'new', title: 'Create New Screener', desc: 'Custom Rules', icon: Plus, isNew: true },
  { id: 'top25', title: 'Stocklytics Top 25', desc: 'Stocklytics Score', icon: Trophy },
  { id: 'technology', title: 'Technology Stocks', desc: 'Market Cap', icon: Cpu },
  { id: 'healthcare', title: 'Healthcare Stocks', desc: 'Score', icon: HeartPulse },
  { id: 'financial', title: 'Bank Stocks', desc: 'Score', icon: Building2 },
  { id: 'consumer', title: 'Consumer Cyclical', desc: 'Score', icon: ShoppingBag },
  { id: 'energy', title: 'Energy Stocks', desc: 'Market Cap', icon: Zap },
  { id: 'communication', title: 'Communication Stocks', desc: 'Score', icon: MessageSquare }
];

const ScreenerCard = ({ cat, onClick }) => {
  const Icon = cat.icon;
  if (cat.isNew) {
    return (
      <div onClick={onClick} className="cursor-pointer bg-primary/10 border-2 border-primary border-dashed rounded-xl p-6 hover:bg-primary/20 transition-colors flex flex-col justify-center min-h-[140px]">
        <div className="bg-primary text-white w-10 h-10 rounded-md flex items-center justify-center mb-4">
          <Icon size={20} />
        </div>
        <h3 className="text-white font-bold text-lg mb-1">{cat.title}</h3>
        <p className="text-text-muted text-sm flex items-center gap-1">
           <LayoutList size={14} /> {cat.desc}
        </p>
      </div>
    );
  }

  return (
    <div onClick={onClick} className="cursor-pointer bg-dark-card border border-dark-border rounded-xl p-6 hover:border-text-muted transition-colors flex flex-col justify-center min-h-[140px]">
      <div className="text-primary mb-4">
        <Icon size={24} />
      </div>
      <h3 className="text-white font-bold text-lg mb-1">{cat.title}</h3>
      <p className="text-text-muted text-sm">{cat.desc}</p>
    </div>
  );
};

const ScreenerPage = () => {
  const navigate = useNavigate();

  return (
    <PageLayout>
      {/* Breadcrumbs */}
      <div className="flex items-center text-sm text-text-muted mb-6">
        <Home size={16} className="mr-2" />
        <span>Home</span>
        <ChevronRight size={16} className="mx-2" />
        <span className="text-white">Screeners</span>
      </div>

      {/* Header Area */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Screeners by Stocklytics</h1>
          <p className="text-text-muted max-w-2xl">
            Browse our collection of pre-built stock screeners to find the best investment opportunities across different categories.
          </p>
        </div>
        
        {/* Search Box */}
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input 
            type="text" 
            placeholder="Search screeners..." 
            className="w-full md:w-64 bg-dark-card border border-dark-border rounded-md py-2 pl-10 pr-4 text-white focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      {/* Grid of Categories */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {categories.map((cat) => (
          <ScreenerCard key={cat.id} cat={cat} onClick={() => navigate(`/screeners/${cat.id}`)} />
        ))}
      </div>
    </PageLayout>
  );
};

export default ScreenerPage;
