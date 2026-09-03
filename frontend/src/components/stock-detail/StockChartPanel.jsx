import React, { Suspense, lazy } from 'react';
import { Loader2 } from 'lucide-react';

const AdvancedRealTimeChart = lazy(() => 
  import('react-ts-tradingview-widgets').then(m => ({ default: m.AdvancedRealTimeChart }))
);

export default function StockChartPanel({ ticker }) {
  return (
    <div className="w-full h-full bg-dark-bg rounded-xl overflow-hidden border border-dark-border shadow-lg">
      <Suspense fallback={
        <div className="flex h-full items-center justify-center text-text-muted animate-pulse">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
          <p>Loading TradingView Widget...</p>
        </div>
      }>
        <AdvancedRealTimeChart 
          symbol={ticker} 
          theme="dark" 
          autosize={true}
          allow_symbol_change={true}
          hide_side_toolbar={false}
          studies={['MACD@tv-basicstudies', 'RSI@tv-basicstudies']}
        />
      </Suspense>
    </div>
  );
}
