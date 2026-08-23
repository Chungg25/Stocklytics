import numpy as np
from app.ai.tools import tool

@tool(
    name="get_support_resistance_levels",
    description="Calculate automatic support and resistance price levels for a stock using historical data. Returns key price levels where the stock has historically bounced or been rejected.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol (e.g., AAPL)"
            },
            "period": {
                "type": "string",
                "description": "The lookback period for analysis (e.g., '6mo', '1y', '2y'). Default '1y'."
            }
        },
        "required": ["ticker"]
    }
)
def get_support_resistance_levels(ticker: str, period: str = "1y") -> dict:
    """Calculate support and resistance levels using local extrema detection."""
    try:
        import yfinance as yf
        from scipy.signal import argrelextrema
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            return {"error": f"No historical data found for {ticker}"}
        
        close = hist['Close'].values
        current_price = float(close[-1])
        
        # Find local maxima (resistance) and minima (support)
        order = max(5, len(close) // 20)  # Adaptive window
        
        local_max_idx = argrelextrema(close, np.greater_equal, order=order)[0]
        local_min_idx = argrelextrema(close, np.less_equal, order=order)[0]
        
        resistance_levels = sorted(set([round(float(close[i]), 2) for i in local_max_idx]))
        support_levels = sorted(set([round(float(close[i]), 2) for i in local_min_idx]))
        
        # Cluster nearby levels (within 2% of each other)
        def cluster_levels(levels, threshold=0.02):
            if not levels:
                return []
            clustered = [levels[0]]
            for level in levels[1:]:
                if abs(level - clustered[-1]) / clustered[-1] > threshold:
                    clustered.append(level)
                else:
                    clustered[-1] = round((clustered[-1] + level) / 2, 2)
            return clustered
        
        resistance_levels = cluster_levels(resistance_levels)
        support_levels = cluster_levels(support_levels)
        
        # Get nearest levels to current price
        nearest_support = [s for s in support_levels if s < current_price]
        nearest_resistance = [r for r in resistance_levels if r > current_price]
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "support_levels": nearest_support[-3:] if len(nearest_support) > 3 else nearest_support,
            "resistance_levels": nearest_resistance[:3] if len(nearest_resistance) > 3 else nearest_resistance,
            "all_support": support_levels,
            "all_resistance": resistance_levels,
            "period": period,
            "data_points": len(close)
        }
    except Exception as e:
        return {"error": f"Failed to calculate S/R levels: {str(e)}"}
