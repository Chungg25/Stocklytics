import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import { Eye, Loader2, Plus, X, Search, Folder, TrendingUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PageLayout from '../components/layout/PageLayout';

export default function WatchlistPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Watchlist form
  const [newTicker, setNewTicker] = useState("");
  const [newGroup, setNewGroup] = useState("Default");
  const [stockData, setStockData] = useState([]);

  useEffect(() => {
    // Fetch stock details to enrich the watchlist
    fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/stocks`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setStockData(data);
      })
      .catch(console.error);

    if (!user) return;
    fetchData();
    
    // Subscribe to realtime changes
    const channel = supabase
      .channel('schema-db-changes-watchlist')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'ai_watchlist' }, () => {
        fetchData();
      })
      .subscribe();
      
    return () => supabase.removeChannel(channel);
  }, [user]);

  const fetchData = async () => {
    if (!user) return;
    try {
      const { data: watchData } = await supabase.from('ai_watchlist').select('*').eq('user_id', user.id).order('created_at', { ascending: false });
      setWatchlist(watchData || []);
    } catch (err) {
      console.error("Error fetching data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTicker = async () => {
    const tickerName = newTicker.trim().toUpperCase();
    if (!tickerName) return;

    // Client-side validation for duplicates
    if (watchlist.some(w => w.ticker === tickerName)) {
      alert(`Ticker ${tickerName} is already in your Watchlist!`);
      return;
    }

    try {
      const { error } = await supabase.from('ai_watchlist').insert({ 
        ticker: tickerName,
        group_name: newGroup.trim() || 'Default',
        user_id: user.id
      });
      
      if (error) {
        if (error.code === '23505') throw new Error("This ticker already exists in your Watchlist!");
        throw error;
      }
      
      setNewTicker("");
      fetchData();
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const handleRemoveTicker = async (id) => {
    try {
      await supabase.from('ai_watchlist').delete().eq('id', id);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  // Group watchlist by group_name
  const groupedWatchlist = watchlist.reduce((acc, curr) => {
    const g = curr.group_name || 'Default';
    if (!acc[g]) acc[g] = [];
    acc[g].push(curr);
    return acc;
  }, {});

  if (loading) return (
    <PageLayout>
      <div className="flex items-center justify-center h-full"><Loader2 className="animate-spin text-primary" /></div>
    </PageLayout>
  );

  return (
    <PageLayout>
      <div className="max-w-6xl mx-auto">
        
        {/* Premium Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1A1F2C] to-[#121620] border border-dark-border p-8 mb-8 shadow-2xl">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-pink-500/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2"></div>
          
          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold mb-4 tracking-wide uppercase">
                <Eye size={14} /> Personal Tracking
              </div>
              <h1 className="text-3xl md:text-4xl font-bold text-white mb-3 tracking-tight">Your Watchlist</h1>
              <p className="text-text-secondary max-w-md text-sm leading-relaxed">
                Track your favorite stocks, organize them into custom groups, and never miss a market movement.
              </p>
            </div>

            {/* Sleek Add Bar */}
            <div className="w-full md:w-auto flex-1 max-w-lg bg-dark-bg/60 backdrop-blur-xl p-2.5 rounded-xl border border-dark-border shadow-inner">
              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" size={16} />
                  <input 
                    type="text" 
                    placeholder="TICKER (e.g. NVDA)..." 
                    value={newTicker}
                    onChange={e => setNewTicker(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-dark-card border border-dark-border hover:border-primary/50 focus:border-primary rounded-lg text-sm font-semibold text-white focus:outline-none transition-colors uppercase placeholder:normal-case placeholder:font-normal"
                  />
                </div>
                <div className="flex gap-2.5">
                  <input 
                    type="text" 
                    placeholder="Group name..." 
                    value={newGroup}
                    onChange={e => setNewGroup(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAddTicker()}
                    className="w-28 sm:w-36 px-4 py-2.5 bg-dark-card border border-dark-border hover:border-primary/50 focus:border-primary rounded-lg text-sm text-white focus:outline-none transition-colors"
                  />
                  <button onClick={handleAddTicker} className="px-5 py-2.5 bg-primary hover:bg-primary-hover text-white rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-primary/25 hover:shadow-primary/40 whitespace-nowrap">
                    <Plus size={18} /> Add
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Watchlist Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {Object.keys(groupedWatchlist).length === 0 ? (
            <div className="col-span-full py-24 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 bg-dark-card rounded-full flex items-center justify-center mb-5 border border-dark-border shadow-xl">
                <Eye className="text-text-muted/50" size={36} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">No stocks tracked yet</h3>
              <p className="text-text-secondary max-w-sm">Use the search bar above to add your first stock to the watchlist and start monitoring its performance.</p>
            </div>
          ) : (
            Object.keys(groupedWatchlist).map(group => (
              <div key={group} className="bg-dark-card border border-dark-border rounded-xl overflow-hidden shadow-lg hover:border-primary/30 transition-colors duration-300 h-fit">
                <div className="bg-gradient-to-r from-dark-bg to-dark-card px-5 py-4 border-b border-dark-border flex justify-between items-center">
                  <h3 className="text-lg font-bold text-white flex items-center gap-2.5">
                    <Folder size={18} className="text-primary" /> {group}
                  </h3>
                  <span className="px-3 py-1 rounded-full bg-dark-bg border border-dark-border text-xs font-semibold text-text-muted">
                    {groupedWatchlist[group].length} assets
                  </span>
                </div>
                
                <div className="p-3">
                  <div className="space-y-2">
                    {groupedWatchlist[group].map(w => {
                      const info = stockData.find(s => s.ticker === w.ticker) || {};
                      const price = info.price || 0;
                      const change = info.change_percent || 0;
                      const isPositive = change >= 0;
                      
                      return (
                      <div 
                        key={w.id} 
                        onClick={() => navigate(`/stock/${w.ticker}`)}
                        className="flex items-center justify-between p-3.5 bg-dark-bg rounded-lg border border-transparent hover:border-dark-border group transition-all duration-200 cursor-pointer hover:bg-dark-hover shadow-sm hover:shadow-md"
                      >
                        <div className="flex items-center gap-4 flex-1">
                          <div className="w-11 h-11 shrink-0 rounded-lg bg-gradient-to-br from-dark-card to-dark-bg border border-dark-border flex items-center justify-center text-white font-black text-lg shadow-inner group-hover:border-primary/50 transition-colors">
                            {w.ticker.charAt(0)}
                          </div>
                          <div className="min-w-0">
                            <div className="font-bold text-white text-base group-hover:text-primary transition-colors flex items-center gap-2">
                              {w.ticker}
                              {info.rating && (
                                <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold tracking-wider ${info.ai_score >= 80 ? 'bg-stock-green/20 text-stock-green' : info.ai_score >= 50 ? 'bg-yellow-400/20 text-yellow-400' : 'bg-stock-red/20 text-stock-red'}`}>
                                  {info.rating}
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-text-muted mt-0.5 truncate max-w-[120px] sm:max-w-[200px]">
                              {info.company || 'Unknown Asset'}
                            </div>
                          </div>
                        </div>

                        {/* Financial Info */}
                        <div className="flex items-center gap-5 mr-4 opacity-90 group-hover:opacity-100 transition-opacity">
                          {info.ai_score && (
                            <div className="hidden sm:flex flex-col items-end">
                              <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider mb-0.5">AI Score</span>
                              <span className={`text-sm font-bold ${info.ai_score >= 80 ? 'text-stock-green' : info.ai_score >= 50 ? 'text-yellow-400' : 'text-stock-red'}`}>
                                {info.ai_score}
                              </span>
                            </div>
                          )}
                          <div className="flex flex-col items-end min-w-[70px]">
                            <span className="text-sm font-bold text-white font-mono">${price ? price.toFixed(2) : '--'}</span>
                            <span className={`text-xs font-semibold flex items-center gap-0.5 ${isPositive ? 'text-stock-green' : 'text-stock-red'}`}>
                              {isPositive ? '+' : ''}{change ? change.toFixed(2) : '0.00'}%
                            </span>
                          </div>
                        </div>
                        
                        {/* Actions */}
                        <div className="flex items-center gap-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity shrink-0">
                          <button 
                            className="p-2 rounded-md bg-dark-card text-text-muted hover:text-white hover:bg-primary/20 border border-transparent hover:border-primary/30 transition-all" 
                            title="View details"
                          >
                            <TrendingUp size={16} />
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleRemoveTicker(w.id); }} 
                            className="p-2 rounded-md bg-dark-card text-text-muted hover:text-stock-red hover:bg-stock-red/10 border border-transparent hover:border-stock-red/20 transition-all" 
                            title="Remove"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      </div>
                    )})}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </PageLayout>
  );
}
