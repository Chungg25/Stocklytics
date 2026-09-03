import React, { useState } from 'react';
import { X, BrainCircuit, Target, Scale, Zap, Star, ShieldCheck, CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function AiAnalysisReport({ data, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('synthesis');

  if (!isOpen || !data) return null;

  const { score, perspectives, synthesis, composite_stars } = data;

  const renderStars = (count) => {
    return Array.from({ length: 5 }).map((_, i) => (
      <Star key={i} size={16} className={i < (count || 0) ? "text-yellow-400 fill-yellow-400" : "text-dark-border"} />
    ));
  };

  const getDecisionColor = (decision) => {
    const d = (decision || '').toUpperCase();
    if (d.includes('STRONG BUY')) return 'bg-stock-green text-dark-bg';
    if (d.includes('BUY')) return 'bg-stock-green/20 text-stock-green border border-stock-green';
    if (d.includes('SELL')) return 'bg-stock-red text-white';
    return 'bg-gray-500 text-white';
  };

  const tabs = [
    { id: 'synthesis', label: 'Tổng kết (Synthesis)', icon: <BrainCircuit size={16} /> },
    { id: 'duan', label: 'Duan Yongping', icon: <Target size={16} /> },
    { id: 'buffett', label: 'Warren Buffett', icon: <ShieldCheck size={16} /> },
    { id: 'munger', label: 'Charlie Munger', icon: <Scale size={16} /> },
    { id: 'lilu', label: 'Li Lu', icon: <Zap size={16} /> },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 lg:p-8">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative w-full max-w-6xl h-full max-h-[90vh] bg-dark-bg border border-dark-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-border bg-gradient-to-r from-dark-card to-dark-bg">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-primary/20 rounded-xl flex items-center justify-center border border-primary/50 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
              <BrainCircuit className="text-primary" size={24} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                4 Masters AI Analysis
                <span className="px-2.5 py-0.5 rounded-full bg-dark-border text-xs text-text-muted font-medium uppercase tracking-wider">BETA</span>
              </h2>
              <p className="text-sm text-text-secondary mt-0.5">Phân tích đa chiều dựa trên triết lý của 4 huyền thoại đầu tư.</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-lg bg-dark-hover text-text-muted hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          
          {/* Sidebar Tabs */}
          <div className="w-full md:w-64 border-r border-dark-border bg-dark-card/50 flex flex-col overflow-y-auto no-scrollbar p-4 space-y-2">
            
            {/* Quick Score Card */}
            <div className="mb-4 p-4 bg-dark-bg rounded-xl border border-dark-border text-center">
              <div className="text-xs text-text-muted uppercase font-bold tracking-wider mb-2">AI Rating</div>
              <div className={`text-2xl font-black mb-1 ${
                score?.total_score >= 80 ? 'text-stock-green' : 
                score?.total_score >= 50 ? 'text-yellow-400' : 'text-stock-red'
              }`}>
                {score?.total_score || '--'}/100
              </div>
              <div className="flex justify-center gap-1 mb-2">
                {renderStars(composite_stars)}
              </div>
              <div className={`inline-block px-3 py-1 rounded-md text-xs font-bold ${getDecisionColor(synthesis?.decision)}`}>
                {synthesis?.decision || 'UNKNOWN'}
              </div>
            </div>

            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                  activeTab === tab.id 
                    ? 'bg-primary/15 text-primary border border-primary/30 shadow-sm' 
                    : 'text-text-secondary hover:bg-dark-hover hover:text-white border border-transparent'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Main Content Area */}
          <div className="flex-1 overflow-y-auto p-6 bg-dark-bg">
            
            {/* Synthesis Tab */}
            {activeTab === 'synthesis' && synthesis && (
              <div className="space-y-6 max-w-4xl mx-auto animate-fade-in">
                <div className="p-6 rounded-2xl bg-gradient-to-br from-primary/10 to-transparent border border-primary/20">
                  <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <CheckCircle2 className="text-primary" /> Kết luận cuối cùng
                  </h3>
                  <div className="prose prose-invert prose-p:text-text-secondary max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {synthesis.summary || "Đang tổng hợp..."}
                    </ReactMarkdown>
                  </div>
                </div>

                {synthesis.key_catalysts && (
                  <div className="p-6 rounded-2xl bg-dark-card border border-dark-border">
                    <h3 className="text-lg font-bold text-white mb-4">Các yếu tố xúc tác (Catalysts)</h3>
                    <ul className="space-y-3">
                      {synthesis.key_catalysts.map((cat, idx) => (
                        <li key={idx} className="flex items-start gap-3 text-text-secondary text-sm">
                          <Zap size={16} className="text-yellow-400 shrink-0 mt-0.5" />
                          <span>{cat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Individual Master Tabs */}
            {['duan', 'buffett', 'munger', 'lilu'].includes(activeTab) && perspectives?.[activeTab] && (
              <div className="space-y-6 max-w-4xl mx-auto animate-fade-in">
                <div className="flex items-center justify-between">
                  <h3 className="text-2xl font-bold text-white">{perspectives[activeTab].name}</h3>
                  <div className="flex gap-1">{renderStars(perspectives[activeTab].stars)}</div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Dynamic Fields based on Master */}
                  {Object.entries(perspectives[activeTab]).map(([key, value]) => {
                    if (['name', 'stars', 'analysis'].includes(key)) return null;
                    if (typeof value === 'object') return null; // Skip arrays for now
                    return (
                      <div key={key} className="p-4 rounded-xl bg-dark-card border border-dark-border">
                        <div className="text-xs text-text-muted uppercase tracking-wider mb-1 font-semibold">
                          {key.replace(/_/g, ' ')}
                        </div>
                        <div className="text-sm text-white font-medium">{value}</div>
                      </div>
                    );
                  })}
                </div>

                <div className="p-6 rounded-2xl bg-dark-hover border border-dark-border">
                  <h4 className="text-sm font-bold text-text-primary uppercase tracking-wider mb-3">Lập luận phân tích</h4>
                  <div className="prose prose-invert prose-p:text-text-secondary max-w-none text-sm leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {perspectives[activeTab].analysis || ""}
                    </ReactMarkdown>
                  </div>
                </div>
                
                {/* Render special arrays like failure_scenarios for Munger */}
                {perspectives[activeTab].failure_scenarios && (
                  <div className="p-6 rounded-2xl bg-stock-red/10 border border-stock-red/20">
                    <h4 className="text-sm font-bold text-stock-red uppercase tracking-wider mb-4 flex items-center gap-2">
                      <AlertTriangle size={16} /> Kịch bản rủi ro (Failure Scenarios)
                    </h4>
                    <div className="space-y-4">
                      {perspectives[activeTab].failure_scenarios.map((scen, idx) => (
                        <div key={idx} className="bg-dark-bg p-4 rounded-lg border border-dark-border">
                          <div className="flex justify-between items-start mb-2">
                            <span className="font-semibold text-white text-sm">{scen.scenario}</span>
                            <span className="px-2 py-1 rounded bg-stock-red/20 text-stock-red text-xs font-bold whitespace-nowrap">
                              {scen.probability}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
          </div>
        </div>
      </div>
    </div>
  );
}
