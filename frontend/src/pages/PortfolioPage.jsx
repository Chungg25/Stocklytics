import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { Wallet, TrendingUp, History, Cpu, FileText, ChevronDown, ChevronUp, Eye } from 'lucide-react';

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [newTicker, setNewTicker] = useState("");
  const [loading, setLoading] = useState(true);
  const [expandedDecision, setExpandedDecision] = useState(null);

  useEffect(() => {
    fetchData();
    
    // Subscribe to realtime changes
    const channel = supabase
      .channel('schema-db-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public' },
        (payload) => {
          fetchData(); // Simplest approach: refetch all on any change
        }
      )
      .subscribe();
      
    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const fetchData = async () => {
    try {
      const { data: portData } = await supabase.from('paper_portfolio').select('*').single();
      if (portData) {
        setPortfolio(portData);
        
        const { data: posData } = await supabase.from('paper_positions').select('*').eq('portfolio_id', portData.id);
        setPositions(posData || []);
        
        const { data: tradeData } = await supabase.from('paper_trades').select('*').eq('portfolio_id', portData.id).order('executed_at', { ascending: false }).limit(10);
        setTrades(tradeData || []);
      }
      
      const { data: decData } = await supabase.from('ai_decisions').select('*').order('created_at', { ascending: false }).limit(10);
      setDecisions(decData || []);
      
      const { data: watchData, error: watchErr } = await supabase.from('ai_watchlist').select('*').order('created_at', { ascending: false });
      if (watchErr) console.error("Watchlist Fetch Error:", watchErr);
      setWatchlist(watchData || []);
      
    } catch (err) {
      console.error("Error fetching data", err);
    } finally {
      setLoading(false);
    }
  };

  const initPortfolio = async () => {
    try {
      const { data, error } = await supabase.from('paper_portfolio').insert({ cash_balance: 100000.0, total_equity: 100000.0 });
      if (error) {
        console.error("Lỗi Supabase:", error);
        alert("Lỗi khi cấp vốn: " + error.message);
      } else {
        fetchData();
      }
    } catch (err) {
      console.error("Lỗi Exception:", err);
      alert("Lỗi hệ thống: " + err.message);
    }
  };

  const handleAddTicker = async () => {
    if (!newTicker.trim()) return;
    const ticker = newTicker.trim().toUpperCase();
    try {
      const { error } = await supabase.from('ai_watchlist').insert({ ticker });
      if (error) alert("Lỗi khi thêm mã: " + error.message);
      setNewTicker("");
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveTicker = async (ticker) => {
    try {
      const { error } = await supabase.from('ai_watchlist').delete().eq('ticker', ticker);
      if (error) alert("Lỗi khi xóa mã: " + error.message);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="p-8 text-center text-text-secondary">Đang tải dữ liệu Quỹ...</div>;

  return (
    <div className="flex-1 overflow-auto bg-dark-bg p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Wallet className="text-stock-green" /> Bảng Điều Khiển Quỹ AI (Paper Trading)
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

        {portfolio ? (
          <>
            {/* Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-dark-card border border-dark-border rounded-lg p-5">
                <div className="text-text-secondary text-sm mb-1">Tiền Mặt (Cash Balance)</div>
                <div className="text-3xl font-bold text-text-primary">
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

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Positions Table */}
              <div className="bg-dark-card border border-dark-border rounded-lg p-5">
                <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                  <TrendingUp size={18} className="text-blue-400" /> Cổ Phiếu Đang Nắm Giữ
                </h2>
                {positions.length === 0 ? (
                  <div className="text-text-secondary text-sm italic">Chưa có cổ phiếu nào.</div>
                ) : (
                  <table className="w-full text-left">
                    <thead>
                      <tr className="text-text-secondary text-sm border-b border-dark-border">
                        <th className="pb-2">Mã</th>
                        <th className="pb-2">Số lượng</th>
                        <th className="pb-2">Giá Mua</th>
                        <th className="pb-2">Lãi/Lỗ</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm">
                      {positions.map(p => (
                        <tr key={p.id} className="border-b border-dark-border/50">
                          <td className="py-2 font-bold text-white">{p.ticker}</td>
                          <td className="py-2">{p.quantity}</td>
                          <td className="py-2">${p.average_entry_price}</td>
                          <td className={`py-2 font-bold ${p.unrealized_pnl >= 0 ? 'text-stock-green' : 'text-stock-red'}`}>
                            ${p.unrealized_pnl}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
                          <div className="text-text-primary">{t.quantity} x ${t.execution_price}</div>
                          <div className="text-text-secondary text-xs">{new Date(t.executed_at).toLocaleString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="bg-dark-card border border-dark-border rounded-lg p-10 text-center">
            <Cpu className="mx-auto text-text-secondary mb-4" size={48} />
            <h3 className="text-xl font-bold text-white mb-2">Chưa có Dữ Liệu Quỹ</h3>
            <p className="text-text-secondary mb-6">Hãy bấm "Cấp Vốn 100,000 USD" để bắt đầu cho AI giao dịch giả lập.</p>
          </div>
        )}

        {/* Watchlist Section */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-5 mt-6">
          <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
            <Eye size={18} className="text-pink-400" /> Danh Mục Theo Dõi (AI Watchlist)
          </h2>
          <div className="flex items-center gap-3 mb-4">
            <input 
              type="text" 
              placeholder="Nhập mã (VD: AAPL, BTC-USD)..." 
              value={newTicker}
              onChange={e => setNewTicker(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAddTicker()}
              className="px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-text-primary focus:outline-none focus:border-stock-green w-64"
            />
            <button onClick={handleAddTicker} className="px-4 py-2 bg-stock-green text-dark-bg rounded font-bold hover:opacity-90 transition-opacity">
              Thêm Mã
            </button>
          </div>
          <div className="flex flex-wrap gap-3">
            {watchlist.length === 0 ? (
              <div className="text-text-secondary text-sm italic">Danh sách trống. Nhập mã để AI bắt đầu quét.</div>
            ) : (
              watchlist.map(w => (
                <div key={w.id} className="flex items-center gap-2 px-3 py-1.5 bg-dark-bg border border-dark-border rounded-full">
                  <span className="font-bold text-white text-sm">{w.ticker}</span>
                  <button onClick={() => handleRemoveTicker(w.ticker)} className="text-text-secondary hover:text-stock-red transition-colors">
                    &times;
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* AI Decisions Log */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-5 mt-6">
          <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
            <Cpu size={18} className="text-purple-400" /> Nhật Ký Quyết Định Của Đội Ngũ AI (TradingAgents)
          </h2>
          {decisions.length === 0 ? (
            <div className="text-text-secondary text-sm italic">AI chưa đưa ra quyết định nào.</div>
          ) : (
            <div className="space-y-3">
              {decisions.map(d => (
                <div key={d.id} className="bg-dark-bg rounded border border-dark-border overflow-hidden">
                  <div 
                    className="flex justify-between items-center p-4 cursor-pointer hover:bg-white/5 transition-colors"
                    onClick={() => setExpandedDecision(expandedDecision === d.id ? null : d.id)}
                  >
                    <div className="flex items-center gap-4">
                      <span className={`px-3 py-1 text-sm font-bold rounded ${
                        d.decision === 'BUY' ? 'bg-stock-green/20 text-stock-green' : 
                        d.decision === 'SELL' ? 'bg-stock-red/20 text-stock-red' : 
                        'bg-gray-500/20 text-gray-300'
                      }`}>
                        {d.decision}
                      </span>
                      <span className="font-bold text-white text-lg">{d.ticker}</span>
                      <span className="text-text-secondary text-sm">{new Date(d.created_at).toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2 text-text-secondary">
                      <span className="text-sm flex items-center gap-1"><FileText size={14}/> Đọc Báo Cáo</span>
                      {expandedDecision === d.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>
                  </div>
                  
                  {expandedDecision === d.id && (
                    <div className="p-4 border-t border-dark-border bg-dark-card/50">
                      <div className="prose prose-invert prose-sm max-w-none">
                        <pre className="whitespace-pre-wrap font-sans text-text-primary text-sm leading-relaxed">
                          {d.rationale}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
