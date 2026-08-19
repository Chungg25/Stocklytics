import yfinance as yf
import ta
from app.ai.tools import tool

@tool(
    name="add_technical_indicator",
    description="Calculate technical indicators (e.g., RSI, MACD, Bollinger Bands) for a stock.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol"
            },
            "indicator_name": {
                "type": "string",
                "description": "The name of the indicator, e.g., 'RSI', 'MACD'"
            }
        },
        "required": ["ticker", "indicator_name"]
    }
)
def add_technical_indicator(ticker: str, indicator_name: str) -> dict:
    try:
        # Fetch 6 months of daily data
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty:
            return {"error": "No data found for ticker"}

        close_series = df['Close']
        if isinstance(close_series, type(df)): # Handle MultiIndex edge cases in yfinance
            close_series = close_series[ticker]

        result = {}
        ind = indicator_name.upper()

        if "RSI" in ind:
            rsi = ta.momentum.RSIIndicator(close_series, window=14).rsi().iloc[-1]
            signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            result["RSI"] = {"value": round(rsi, 2), "signal": signal}
            
        elif "MACD" in ind:
            macd_obj = ta.trend.MACD(close_series)
            macd = macd_obj.macd().iloc[-1]
            signal_line = macd_obj.macd_signal().iloc[-1]
            hist = macd_obj.macd_diff().iloc[-1]
            signal = "Bullish" if hist > 0 else "Bearish"
            result["MACD"] = {
                "macd": round(macd, 4), 
                "signal_line": round(signal_line, 4), 
                "histogram": round(hist, 4),
                "signal": signal
            }
            
        else:
            return {"error": f"Indicator {indicator_name} not yet supported in this tool."}

        result["source"] = "yfinance + ta library"
        return result

    except Exception as e:
        return {"error": f"Failed to calculate {indicator_name}: {str(e)}"}
