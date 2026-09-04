import React from 'react';
import { X, Sparkles, AlertTriangle, Target, TrendingUp, Crosshair, BarChart2 } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f43f5e'];

const AISuggestionModal = ({ isOpen, onClose, data }) => {
  if (!isOpen || !data) return null;

  // Prepare pie chart data
  const pieData = Object.entries(data.portfolio_allocation || {}).map(([ticker, pct]) => ({
    name: ticker,
    value: pct
  })).sort((a, b) => b.value - a.value);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-dark-bg border border-dark-border rounded-xl shadow-2xl w-[90vw] max-w-5xl h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-border bg-dark-card">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Sparkles className="text-primary" size={24} />
              {data.screen_label} AI Portfolio
            </h2>
            <p className="text-sm text-text-muted mt-1">{data.summary}</p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-dark-hover rounded-lg text-text-muted hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto no-scrollbar p-6 space-y-8">
          
          {/* Strategy & Allocation */}
          <section className="bg-dark-card border border-dark-border rounded-xl p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <BarChart2 size={20} className="text-primary" />
              Portfolio Strategy
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              
              {/* Pie Chart */}
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      label={({name, value}) => `${name} ${value}%`}
                      labelLine={false}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#131722', borderColor: '#2A2E39', color: '#fff' }}
                      itemStyle={{ color: '#fff' }}
                      formatter={(value) => [`${value}%`, 'Allocation']}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Text Insights */}
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">Allocation Rationale</h4>
                  <p className="text-sm text-text-secondary leading-relaxed">{data.allocation_rationale}</p>
                </div>
                
                {data.diversification?.insight && (
                  <div>
                    <h4 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">Diversification Insights</h4>
                    <p className="text-sm text-text-secondary leading-relaxed">{data.diversification.insight}</p>
                  </div>
                )}
                
                {data.theme_insight && (
                  <div className="bg-primary/10 border border-primary/20 rounded-lg p-3">
                    <p className="text-sm text-primary flex items-start gap-2">
                      <Sparkles size={16} className="mt-0.5 shrink-0" />
                      {data.theme_insight}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* AI Picks */}
          <section>
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Target size={20} className="text-stock-green" />
              Top AI Picks
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {data.picks?.map((pick) => (
                <div key={pick.ticker} className="bg-dark-card border border-dark-border rounded-xl p-5 hover:border-text-muted transition-colors flex flex-col">
                  {/* Card Header */}
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-xl font-bold text-white flex items-center gap-2">
                        {pick.ticker}
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-dark-bg border border-dark-border text-text-muted">
                          {pieData.find(p => p.name === pick.ticker)?.value || 0}% Weight
                        </span>
                      </h4>
                      <p className="text-sm text-text-muted">{pick.company_name}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${pick.action === 'BUY' || pick.action === 'Strong Buy' ? 'bg-stock-green/20 text-stock-green' : pick.action === 'HOLD' ? 'bg-text-muted/20 text-text-muted' : 'bg-stock-red/20 text-stock-red'}`}>
                        {pick.action || 'HOLD'}
                      </span>
                      <span className="text-xs text-text-muted capitalize">{pick.conviction} Conviction</span>
                    </div>
                  </div>
                  
                  {/* Deep Analysis */}
                  <div className="space-y-3 mb-6 flex-1">
                    {pick.catalyst && (
                      <div>
                        <h5 className="text-xs font-bold text-primary mb-1 uppercase tracking-wider flex items-center gap-1">
                          <TrendingUp size={14} /> Catalyst
                        </h5>
                        <p className="text-sm text-text-secondary">{pick.catalyst}</p>
                      </div>
                    )}
                    {pick.thesis && (
                      <div>
                        <h5 className="text-xs font-bold text-white mb-1 uppercase tracking-wider flex items-center gap-1">
                          <Crosshair size={14} /> Thesis
                        </h5>
                        <p className="text-sm text-text-secondary">{pick.thesis}</p>
                      </div>
                    )}
                    {pick.top_risk && (
                      <div>
                        <h5 className="text-xs font-bold text-stock-red mb-1 uppercase tracking-wider flex items-center gap-1">
                          <AlertTriangle size={14} /> Key Risk
                        </h5>
                        <p className="text-sm text-text-secondary">{pick.top_risk}</p>
                      </div>
                    )}
                  </div>

                  {/* Trading Setup */}
                  <div className="grid grid-cols-4 gap-2 bg-dark-bg p-3 rounded-lg border border-dark-border/50">
                    <div>
                      <p className="text-[10px] text-text-muted uppercase">
                        {pick.action === 'WATCH' ? 'Current' : 'Entry'}
                      </p>
                      <p className="text-sm font-mono text-white">${pick.entry_price || pick.price}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-text-muted uppercase">
                        {pick.action === 'WATCH' ? 'Fair Value' : 'Target'}
                      </p>
                      <p className={`text-sm font-mono ${pick.expected_return_pct > 0 ? 'text-stock-green' : pick.expected_return_pct < 0 ? 'text-stock-red' : 'text-white'}`}>
                        ${pick.target_price || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-text-muted uppercase">
                        {pick.action === 'WATCH' ? 'Support' : 'Stop'}
                      </p>
                      <p className="text-sm font-mono text-stock-red">${pick.stop_loss || 'N/A'}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-text-muted uppercase">Upside</p>
                      <p className={`text-sm font-bold ${pick.expected_return_pct > 0 ? 'text-stock-green' : pick.expected_return_pct < 0 ? 'text-stock-red' : 'text-text-muted'}`}>
                        {pick.expected_return_pct > 0 ? '+' : ''}{pick.expected_return_pct || 0}%
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

        </div>
      </div>
    </div>
  );
};

export default AISuggestionModal;
