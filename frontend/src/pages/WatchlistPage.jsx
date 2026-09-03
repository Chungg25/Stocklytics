import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import { Eye, Loader2, Plus, X } from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';

export default function WatchlistPage() {
  const { user } = useAuth();
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Watchlist form
  const [newTicker, setNewTicker] = useState("");
  const [newGroup, setNewGroup] = useState("Default");

  useEffect(() => {
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
    if (!newTicker.trim()) return;
    try {
      const { error } = await supabase.from('ai_watchlist').insert({ 
        ticker: newTicker.trim().toUpperCase(),
        group_name: newGroup.trim() || 'Default',
        user_id: user.id
      });
      if (error) throw error;
      setNewTicker("");
      fetchData();
    } catch (err) {
      alert("Lỗi: " + err.message);
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
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Eye className="text-pink-400" /> Watchlist
          </h1>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-lg p-5">
          <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
            Thêm mã vào Watchlist
          </h2>
          
          <div className="space-y-2 mb-6 max-w-lg">
            <input 
              type="text" 
              placeholder="Mã cổ phiếu (VD: AAPL, NVDA)..." 
              value={newTicker}
              onChange={e => setNewTicker(e.target.value)}
              className="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
            />
            <div className="flex gap-2">
              <input 
                type="text" 
                placeholder="Nhóm (Mặc định: Default)..." 
                value={newGroup}
                onChange={e => setNewGroup(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleAddTicker()}
                className="flex-1 px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
              />
              <button onClick={handleAddTicker} className="px-4 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-hover text-sm flex items-center gap-1">
                <Plus size={16} /> Thêm
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.keys(groupedWatchlist).length === 0 ? (
              <div className="text-text-secondary text-sm italic col-span-full">Bạn chưa lưu mã cổ phiếu nào. Hãy thêm mã ở trên.</div>
            ) : (
              Object.keys(groupedWatchlist).map(group => (
                <div key={group} className="border border-dark-border rounded-lg overflow-hidden h-fit">
                  <div className="bg-dark-hover px-3 py-2 text-sm font-bold text-white border-b border-dark-border flex justify-between">
                    {group}
                    <span className="text-text-muted">{groupedWatchlist[group].length} mã</span>
                  </div>
                  <div className="p-2 space-y-2">
                    {groupedWatchlist[group].map(w => (
                      <div key={w.id} className="flex items-center justify-between p-3 bg-dark-bg rounded border border-transparent hover:border-dark-border group transition-colors">
                        <span className="font-bold text-white text-base">{w.ticker}</span>
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => handleRemoveTicker(w.id)} className="p-1 rounded bg-dark-hover text-text-muted hover:text-stock-red hover:bg-stock-red/10 transition-colors">
                            <X size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
