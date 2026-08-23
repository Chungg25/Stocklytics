import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import { Wallet, TrendingUp, History, Cpu, Eye, ArrowRight, Loader2, DollarSign, X } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function PortfolioPage() {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Watchlist form
  const [newTicker, setNewTicker] = useState("");
  const [newGroup, setNewGroup] = useState("Default");

  // Trade Modal
  const [isTradeModalOpen, setIsTradeModalOpen] = useState(false);
  const [tradeTarget, setTradeTarget] = useState(null);
  const [tradeQuantity, setTradeQuantity] = useState(1);
  const [tradeType, setTradeType] = useState('BUY');
  const [isTrading, setIsTrading] = useState(false);

  useEffect(() => {
    if (!user) return;
    syncAndFetch();
    
    // Subscribe to realtime changes
    const channel = supabase
      .channel('schema-db-changes')
      .on('postgres_changes', { event: '*', schema: 'public' }, () => {
        fetchData();
      })
      .subscribe();
      
    return () => supabase.removeChannel(channel);
  }, [user]);

  const syncAndFetch = async () => {
    setLoading(true);
    // Sync prices
    try {
      await fetch(`${API_URL}/api/trading/portfolio/sync/${user.id}`);
    } catch(e) {
      console.error('Sync failed', e);
    }
    await fetchData();
    setLoading(false);
  };

  const fetchData = async () => {
    if (!user) return;
    try {
      const { data: portData } = await supabase.from('paper_portfolio').select('*').eq('user_id', user.id).single();
      if (portData) {
        setPortfolio(portData);
        const { data: posData } = await supabase.from('paper_positions').select('*').eq('portfolio_id', portData.id);
        setPositions(posData || []);
        const { data: tradeData } = await supabase.from('paper_trades').select('*').eq('portfolio_id', portData.id).order('executed_at', { ascending: false }).limit(10);
        setTrades(tradeData || []);
      }
      
      const { data: decData } = await supabase.from('ai_decisions').select('*').eq('user_id', user.id).order('created_at', { ascending: false }).limit(10);
      setDecisions(decData || []);
      
      const { data: watchData } = await supabase.from('ai_watchlist').select('*').eq('user_id', user.id).order('created_at', { ascending: false });
      setWatchlist(watchData || []);
      
    } catch (err) {
      console.error("Error fetching data", err);
    }
  };

  const initPortfolio = async () => {
    try {
      const { data, error } = await supabase.from('paper_portfolio').insert({ 
        cash_balance: 100000.0, 
        total_equity: 100000.0,
        user_id: user.id
      });
      if (error) throw error;
      fetchData();
    } catch (err) {
      alert("Lỗi cấp vốn: " + err.message);
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

  const executeTrade = async () => {
    if (tradeQuantity <= 0) return alert("Số lượng phải > 0");
    setIsTrading(true);
    try {
      const res = await fetch(`${API_URL}/api/trading/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          ticker: tradeTarget,
          quantity: parseInt(tradeQuantity),
          trade_type: tradeType
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setIsTradeModalOpen(false);
        fetchData();
      } else {
        alert(data.message);
      }
    } catch (err) {
      alert("Lỗi giao dịch: " + err.message);
    } finally {
      setIsTrading(false);
    }
  };

  const openTradeModal = (ticker, type) => {
    if (!portfolio) return alert("Vui lòng cấp vốn trước khi giao dịch.");
    setTradeTarget(ticker);
    setTradeType(type);
    setTradeQuantity(1);
    setIsTradeModalOpen(true);
  };

  // Group watchlist by group_name
  const groupedWatchlist = watchlist.reduce((acc, curr) => {
    const g = curr.group_name || 'Default';
    if (!acc[g]) acc[g] = [];
    acc[g].push(curr);
    return acc;
  }, {});

  if (loading) return <div className="p-8 text-center text-text-secondary">Đang tải dữ liệu Quỹ...</div>;

  return (
    <div className="flex-1 overflow-auto bg-dark-bg p-6 relative">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Wallet className="text-stock-green" /> Paper Trading & Watchlist
          </h1>
          {!portfolio && (
            <button 
              onClick={initPortfolio}
              className="px-4 py-2 bg-stock-green text-dark-bg rounded font-bold hover:opacity-90 transition-opacity"
            >
              Cấp Vốn 100,000 USD
            </button>
          )}
        </div>

        {portfolio && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-dark-card border border-dark-border rounded-lg p-5">
              <div className="text-text-secondary text-sm mb-1">Tiền Mặt (Cash Balance)</div>
              <div className="text-3xl font-bold text-white">
                ${Number(portfolio.cash_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="bg-dark-card border border-dark-border rounded-lg p-5">
              <div className="text-text-secondary text-sm mb-1">Tổng Tài Sản (Total Equity)</div>
              <div className="text-3xl font-bold text-stock-green flex items-center gap-2">
                ${Number(portfolio.total_equity).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                <TrendingUp size={20} />
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Watchlist & Groups */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-dark-card border border-dark-border rounded-lg p-5">
              <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <Eye size={18} className="text-pink-400" /> Watchlist Groups
              </h2>
              
              <div className="space-y-2 mb-6">
                <input 
                  type="text" 
                  placeholder="Mã (VD: AAPL)..." 
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
                  <button onClick={handleAddTicker} className="px-3 py-2 bg-primary text-white rounded-lg font-bold hover:bg-primary-hover text-sm">
                    Thêm
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                {Object.keys(groupedWatchlist).length === 0 ? (
                  <div className="text-text-secondary text-sm italic">Chưa có mã theo dõi.</div>
                ) : (
                  Object.keys(groupedWatchlist).map(group => (
                    <div key={group} className="border border-dark-border rounded-lg overflow-hidden">
                      <div className="bg-dark-hover px-3 py-2 text-sm font-bold text-white border-b border-dark-border flex justify-between">
                        {group}
                        <span className="text-text-muted">{groupedWatchlist[group].length} mã</span>
                      </div>
                      <div className="p-2 space-y-2">
                        {groupedWatchlist[group].map(w => (
                          <div key={w.id} className="flex items-center justify-between p-2 bg-dark-bg rounded border border-transparent hover:border-dark-border group">
                            <span className="font-bold text-white text-sm">{w.ticker}</span>
                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button onClick={() => openTradeModal(w.ticker, 'BUY')} className="text-xs px-2 py-1 bg-stock-green/20 text-stock-green rounded hover:bg-stock-green hover:text-dark-bg">Mua</button>
                              <button onClick={() => handleRemoveTicker(w.id)} className="text-text-muted hover:text-stock-red">&times;</button>
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

          {/* Right Column: Portfolio & Trades */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Positions */}
            <div className="bg-dark-card border border-dark-border rounded-lg p-5">
              <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <DollarSign size={18} className="text-stock-green" /> Danh Mục Đầu Tư (Positions)
              </h2>
              {!portfolio || positions.length === 0 ? (
                <div className="text-text-secondary text-sm italic">Chưa có cổ phiếu nào.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="text-text-secondary text-sm border-b border-dark-border">
                        <th className="pb-2">Mã</th>
                        <th className="pb-2">Số lượng</th>
                        <th className="pb-2">Giá TB</th>
                        <th className="pb-2">Lãi/Lỗ</th>
                        <th className="pb-2 text-right">Hành động</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm">
                      {positions.map(p => (
                        <tr key={p.id} className="border-b border-dark-border/50">
                          <td className="py-3 font-bold text-white">{p.ticker}</td>
                          <td className="py-3">{p.quantity}</td>
                          <td className="py-3">${Number(p.average_entry_price).toFixed(2)}</td>
                          <td className={`py-3 font-bold ${p.unrealized_pnl >= 0 ? 'text-stock-green' : 'text-stock-red'}`}>
                            {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl}
                          </td>
                          <td className="py-3 text-right space-x-2">
                            <button onClick={() => openTradeModal(p.ticker, 'BUY')} className="text-xs px-2 py-1 bg-stock-green/20 text-stock-green rounded hover:bg-stock-green hover:text-dark-bg">Thêm</button>
                            <button onClick={() => openTradeModal(p.ticker, 'SELL')} className="text-xs px-2 py-1 bg-stock-red/20 text-stock-red rounded hover:bg-stock-red hover:text-white">Bán</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Trade Ledger */}
            <div className="bg-dark-card border border-dark-border rounded-lg p-5">
              <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <History size={18} className="text-orange-400" /> Lịch Sử Khớp Lệnh
              </h2>
              {trades.length === 0 ? (
                <div className="text-text-secondary text-sm italic">Chưa có giao dịch nào.</div>
              ) : (
                <div className="space-y-3">
                  {trades.map(t => (
                    <div key={t.id} className="flex justify-between items-center text-sm p-3 bg-dark-bg rounded border border-dark-border">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 text-xs font-bold rounded ${t.trade_type === 'BUY' ? 'bg-stock-green/20 text-stock-green' : 'bg-stock-red/20 text-stock-red'}`}>
                          {t.trade_type}
                        </span>
                        <span className="font-bold text-white">{t.ticker}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-text-primary">{t.quantity} x ${Number(t.execution_price).toFixed(2)}</div>
                        <div className="text-text-secondary text-xs">{new Date(t.executed_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* AI Decisions */}
            <div className="bg-dark-card border border-dark-border rounded-lg p-5">
              <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <Cpu size={18} className="text-purple-400" /> Cố Vấn Đầu Tư AI (TradingAgents)
              </h2>
              {decisions.length === 0 ? (
                <div className="text-text-secondary text-sm italic">AI chưa có lời khuyên nào.</div>
              ) : (
                <div className="space-y-3">
                  {decisions.map(d => (
                    <div key={d.id} className="p-4 bg-dark-bg border border-dark-border rounded-lg">
                      <div className="flex justify-between mb-2">
                        <span className="font-bold text-white text-sm">{d.ticker} - {d.action}</span>
                        <span className="text-xs text-text-muted">{new Date(d.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-sm text-text-secondary">{d.reasoning}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        </div>
      </div>

      {/* Trade Modal */}
      {isTradeModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-dark-card border border-dark-border rounded-xl w-full max-w-sm overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-4 border-b border-dark-border bg-dark-bg">
              <h3 className="font-bold text-white">Giao Dịch {tradeTarget}</h3>
              <button onClick={() => setIsTradeModalOpen(false)} className="text-text-muted hover:text-white">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">Loại Lệnh</label>
                <div className="flex gap-2">
                  <button 
                    onClick={() => setTradeType('BUY')}
                    className={`flex-1 py-2 text-sm font-bold rounded-lg border transition-colors ${tradeType === 'BUY' ? 'bg-stock-green/20 border-stock-green text-stock-green' : 'bg-dark-bg border-dark-border text-text-muted'}`}
                  >Mua (Buy)</button>
                  <button 
                    onClick={() => setTradeType('SELL')}
                    className={`flex-1 py-2 text-sm font-bold rounded-lg border transition-colors ${tradeType === 'SELL' ? 'bg-stock-red/20 border-stock-red text-stock-red' : 'bg-dark-bg border-dark-border text-text-muted'}`}
                  >Bán (Sell)</button>
                </div>
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Số Lượng Cổ Phiếu</label>
                <input 
                  type="number" 
                  min="1"
                  value={tradeQuantity}
                  onChange={e => setTradeQuantity(e.target.value)}
                  className="w-full px-4 py-3 bg-dark-bg border border-dark-border rounded-lg text-white font-bold focus:outline-none focus:border-primary text-center text-lg"
                />
              </div>
              <button 
                onClick={executeTrade}
                disabled={isTrading}
                className={`w-full py-3 rounded-lg font-bold text-white flex justify-center items-center gap-2 transition-all ${
                  tradeType === 'BUY' ? 'bg-stock-green hover:bg-stock-green/90' : 'bg-stock-red hover:bg-stock-red/90'
                } ${isTrading ? 'opacity-50' : ''}`}
              >
                {isTrading ? <Loader2 className="animate-spin" size={18} /> : (tradeType === 'BUY' ? 'Khớp Lệnh MUA' : 'Khớp Lệnh BÁN')}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
