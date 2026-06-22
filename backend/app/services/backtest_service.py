import yfinance as yf
import pandas as pd
import numpy as np
from openai import OpenAI
import ta

def run_backtest(ticker: str, start_date: str, end_date: str, strategy_prompt: str):
    # 1. Fetch Data
    df = yf.download(ticker, start=start_date, end=end_date)
    if df.empty:
        raise ValueError("No data found for the given ticker and date range.")
    
    # Flatten multi-index columns if present (yfinance latest versions)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    import os
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Please set it in your environment variables.")

    # 2. Call LLM Groq
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    system_prompt = """
You are an expert quantitative developer. You will be given a trading strategy in natural language.
You must output ONLY raw Python code (no markdown formatting, no explanations).
The code must define a function:
def generate_signals(df):
    import ta
    import pandas as pd
    import numpy as np
    # df is a pandas DataFrame with columns: Open, High, Low, Close, Volume
    # Add a column 'Signal' to df.
    # 'Signal' should be 1 for a Buy signal, -1 for a Sell signal, and 0 otherwise.
    # Example:
    # df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    # df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    # df['Signal'] = 0
    # df.loc[(df['SMA_20'] > df['SMA_50']) & (df['SMA_20'].shift(1) <= df['SMA_50'].shift(1)), 'Signal'] = 1
    # df.loc[(df['SMA_20'] < df['SMA_50']) & (df['SMA_20'].shift(1) >= df['SMA_50'].shift(1)), 'Signal'] = -1
    # Return the df
    return df
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": strategy_prompt}
        ],
        temperature=0.1
    )

    code = response.choices[0].message.content
    if "```python" in code:
        code = code.split("```python")[1]
    if "```" in code:
        code = code.split("```")[0]
    code = code.strip()

    # 3. Exec Code (Local environment)
    local_env = {}
    try:
        exec(code, globals(), local_env)
        generate_signals = local_env['generate_signals']
        df = generate_signals(df)
    except Exception as e:
        raise ValueError(f"Failed to execute generated code: {e}\n\nGenerated Code:\n{code}")

    if 'Signal' not in df.columns:
        raise ValueError("The generated code did not add a 'Signal' column.")

    # 4. Backtest Engine
    initial_capital = 10000.0
    cash = initial_capital
    shares = 0
    equity_curve = []
    trades = []
    
    # metrics tracking
    buy_price = 0
    
    for date, row in df.iterrows():
        close_price = float(row['Close'])
        signal = row['Signal']
        
        # Execute signals
        if signal == 1 and shares == 0: # Buy
            shares = cash / close_price
            buy_price = close_price
            cash = 0
        elif signal == -1 and shares > 0: # Sell
            cash = shares * close_price
            profit = cash - (shares * buy_price)
            trades.append(profit)
            shares = 0
            
        equity = cash + (shares * close_price)
        equity_curve.append({
            "date": date.strftime("%Y-%m-%d"),
            "equity": round(equity, 2),
            "close": round(close_price, 2),
            "signal": int(signal)
        })

    # Close out open position at the end to calculate final equity
    if shares > 0:
        final_cash = shares * float(df['Close'].iloc[-1])
        profit = final_cash - (shares * buy_price)
        trades.append(profit)
        equity = final_cash
        
    total_return = ((equity - initial_capital) / initial_capital) * 100
    winning_trades = [t for t in trades if t > 0]
    win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0

    # Max Drawdown
    equity_series = pd.Series([e['equity'] for e in equity_curve])
    roll_max = equity_series.cummax()
    drawdown = (equity_series - roll_max) / roll_max
    max_drawdown = drawdown.min() * 100

    # Base-and-Hold Return (for comparison)
    start_price = float(df['Close'].iloc[0])
    end_price = float(df['Close'].iloc[-1])
    buy_hold_return = ((end_price - start_price) / start_price) * 100

    return {
        "metrics": {
            "total_return": round(total_return, 2),
            "buy_hold_return": round(buy_hold_return, 2),
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_drawdown, 2),
            "total_trades": len(trades)
        },
        "equity_curve": equity_curve,
        "generated_code": code
    }
