import yfinance as yf
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta

def get_compare_data(tickers, timeframe, indicators):
    if not tickers:
        return []
        
    # Determine start date based on timeframe for slicing later
    # But we always fetch 5y to ensure long-term indicators (like SMA200) have enough historical data
    end_date = datetime.now()
    if timeframe == '1M':
        slice_start = end_date - timedelta(days=30)
    elif timeframe == '3M':
        slice_start = end_date - timedelta(days=90)
    elif timeframe == '6M':
        slice_start = end_date - timedelta(days=180)
    elif timeframe == '1Y':
        slice_start = end_date - timedelta(days=365)
    elif timeframe == '3Y':
        slice_start = end_date - timedelta(days=365*3)
    elif timeframe == '5Y':
        slice_start = end_date - timedelta(days=365*5)
    else:
        slice_start = end_date - timedelta(days=90) # default 3M
        
    # Fetch data
    tickers_str = " ".join(tickers)
    df = yf.download(tickers_str, period="5y", interval="1d")
    
    if df.empty:
        return []

    # Format into a dictionary of DataFrames per ticker
    ticker_dfs = {}
    
    if len(tickers) == 1:
        # yfinance returns single index columns if only 1 ticker
        ticker = tickers[0]
        ticker_dfs[ticker] = df
    else:
        # Multi-index columns
        for ticker in tickers:
            try:
                # Extract data for this specific ticker
                ticker_df = pd.DataFrame()
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if (col, ticker) in df.columns:
                        ticker_df[col] = df[col][ticker]
                ticker_dfs[ticker] = ticker_df.dropna(subset=['Close'])
            except KeyError:
                continue
                
    # Prepare result data structure
    # We will build a unified list of dictionaries by date
    date_records = {}

    for ticker, t_df in ticker_dfs.items():
        if t_df.empty:
            continue
            
        close = t_df['Close']
        volume = t_df.get('Volume', pd.Series(np.zeros(len(close)), index=close.index))
        
        # Calculate Indicators on Absolute Prices BEFORE slicing
        t_df['SMA_20'] = ta.trend.sma_indicator(close, window=20)
        t_df['SMA_50'] = ta.trend.sma_indicator(close, window=50)
        t_df['SMA_200'] = ta.trend.sma_indicator(close, window=200)
        t_df['EMA_20'] = ta.trend.ema_indicator(close, window=20)
        t_df['EMA_50'] = ta.trend.ema_indicator(close, window=50)
        
        # Bollinger Bands
        indicator_bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        t_df['BB_High'] = indicator_bb.bollinger_hband()
        t_df['BB_Low'] = indicator_bb.bollinger_lband()
        
        # Oscillators & Volume (Absolute, not relative to start price)
        t_df['RSI'] = ta.momentum.rsi(close, window=14)
        t_df['MACD'] = ta.trend.macd(close)
        t_df['Volume_MA'] = ta.trend.sma_indicator(volume, window=20)
        t_df['OBV'] = ta.volume.on_balance_volume(close, volume)
        
        # Slice to Timeframe
        # Convert index to timezone naive for comparison if needed
        sliced_df = t_df.loc[t_df.index >= pd.to_datetime(slice_start).tz_localize(t_df.index.tz)]
        
        if sliced_df.empty:
            continue
            
        # Get start price for normalization
        start_price = float(sliced_df['Close'].iloc[0])
        if start_price == 0:
            continue
            
        # Iterate over sliced dataframe to populate date_records
        for date, row in sliced_df.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            if date_str not in date_records:
                date_records[date_str] = {"date": date_str}
                
            # Normalize Price and Overlays to Percentage %
            date_records[date_str][f"{ticker}_perf"] = round(((row['Close'] - start_price) / start_price) * 100, 2)
            
            # Normalize Overlays to Percentage (relative to the start price of the actual stock)
            # This allows SMA to be plotted on the same Y-axis as Performance %
            if not pd.isna(row['SMA_20']): date_records[date_str][f"{ticker}_SMA_20"] = round(((row['SMA_20'] - start_price) / start_price) * 100, 2)
            if not pd.isna(row['SMA_50']): date_records[date_str][f"{ticker}_SMA_50"] = round(((row['SMA_50'] - start_price) / start_price) * 100, 2)
            if not pd.isna(row['SMA_200']): date_records[date_str][f"{ticker}_SMA_200"] = round(((row['SMA_200'] - start_price) / start_price) * 100, 2)
            if not pd.isna(row['EMA_20']): date_records[date_str][f"{ticker}_EMA_20"] = round(((row['EMA_20'] - start_price) / start_price) * 100, 2)
            if not pd.isna(row['EMA_50']): date_records[date_str][f"{ticker}_EMA_50"] = round(((row['EMA_50'] - start_price) / start_price) * 100, 2)
            if not pd.isna(row['BB_High']): date_records[date_str][f"{ticker}_BB_High"] = round(((row['BB_High'] - start_price) / start_price) * 100, 2)
            if not pd.isna(row['BB_Low']): date_records[date_str][f"{ticker}_BB_Low"] = round(((row['BB_Low'] - start_price) / start_price) * 100, 2)
            
            # Oscillators & Volume (Keep absolute values)
            if not pd.isna(row['RSI']): date_records[date_str][f"{ticker}_RSI"] = round(row['RSI'], 2)
            if not pd.isna(row['MACD']): date_records[date_str][f"{ticker}_MACD"] = round(row['MACD'], 4)
            if not pd.isna(row['Volume']): date_records[date_str][f"{ticker}_Volume"] = int(row['Volume'])
            if not pd.isna(row['Volume_MA']): date_records[date_str][f"{ticker}_Volume_MA"] = int(row['Volume_MA'])
            if not pd.isna(row['OBV']): date_records[date_str][f"{ticker}_OBV"] = int(row['OBV'])

    # Convert dict to sorted list
    sorted_dates = sorted(list(date_records.keys()))
    final_data = [date_records[d] for d in sorted_dates]
    
    return final_data
