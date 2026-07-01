import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SEMICONDUCTOR_STOCKS = [
    "POWI", "COHU", "JBL", "DQ", "QRVO", "PWR", "MTSI", "FORM", "Q", "SITM", 
    "ASML", "ONTO", "CDNS", "SMTC", "SNPS", "STX", "ALGM", "AMKR", "KEYS", 
    "GFS", "TER", "ARR", "LSCC", "SWKS", "NXPI", "ENTG", "COHR", "WDC", 
    "FLEX", "AMAT", "AXTI", "WOLF", "TXN", "LRCX", "SNDK", "ON", "ASX", 
    "TSM", "ADI", "MCHP", "STM", "UMC", "AVGO", "ARM", "QCOM", "MRVL", 
    "AMD", "MU", "INTC", "NVDA"
]

def get_9_sma_signals():
    buy_signals = []
    sell_signals = []
    
    # Download 20 days of data
    data = yf.download(SEMICONDUCTOR_STOCKS, period="20d", threads=True)
    
    is_multiindex = isinstance(data.columns, pd.MultiIndex)
    
    for ticker in SEMICONDUCTOR_STOCKS:
        try:
            if is_multiindex:
                # Handles MultiIndex format (Price, Ticker)
                if 'Close' in data.columns.levels[0]:
                    if ticker not in data['Close'].columns:
                        continue
                    close_prices = data['Close'][ticker].dropna()
                else:
                    if ticker not in data.columns.levels[0]:
                        continue
                    close_prices = data[ticker]['Close'].dropna()
            else:
                if len(SEMICONDUCTOR_STOCKS) == 1:
                    close_prices = data['Close'].dropna()
                else:
                    continue
                    
            if len(close_prices) < 10:
                continue
                
            df = pd.DataFrame({'Close': close_prices})
            df['SMA_9'] = df['Close'].rolling(window=9).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            if pd.isna(latest['SMA_9']) or pd.isna(prev['SMA_9']):
                continue
                
            # Signal: close under 9 day moving average -> sell
            # Signal: close above 9 day moving average -> buy
            if prev['Close'] <= prev['SMA_9'] and latest['Close'] > latest['SMA_9']:
                buy_signals.append(f"{ticker} (Close: {latest['Close']:.2f}, SMA9: {latest['SMA_9']:.2f})")
            elif prev['Close'] >= prev['SMA_9'] and latest['Close'] < latest['SMA_9']:
                sell_signals.append(f"{ticker} (Close: {latest['Close']:.2f}, SMA9: {latest['SMA_9']:.2f})")
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            
    return buy_signals, sell_signals

def send_email(buy_signals, sell_signals):
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("SENDER_PASSWORD")
    receiver = os.environ.get("RECEIVER_EMAIL")
    
    if not sender or not password or not receiver:
        print("Email credentials not configured properly in .env.")
        return
        
    if not buy_signals and not sell_signals:
        print("No signals today, skipping email.")
        return
        
    subject = "Daily Semiconductor 9-SMA Signals"
    
    body = "Hello,\n\nHere are the 9-day SMA crossover signals for your 50 semiconductor stocks after today's close:\n\n"
    if buy_signals:
        body += "=== BUY SIGNALS (Close crossed above 9-SMA) ===\n"
        body += "\n".join([f"- {s}" for s in buy_signals]) + "\n\n"
        
    if sell_signals:
        body += "=== SELL SIGNALS (Close crossed below 9-SMA) ===\n"
        body += "\n".join([f"- {s}" for s in sell_signals]) + "\n\n"
        
    body += "Regards,\nStocklytics System"
        
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        # Remove any quotes or extra spaces from password just in case
        clean_password = password.replace('"', '').replace("'", '').strip()
        server.login(sender, clean_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {receiver}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def run_daily_scan():
    print("Starting daily scan...")
    buy_signals, sell_signals = get_9_sma_signals()
    print(f"Found {len(buy_signals)} BUY and {len(sell_signals)} SELL signals.")
    
    if buy_signals or sell_signals:
        send_email(buy_signals, sell_signals)
    
    return {
        "status": "success",
        "buy_signals": buy_signals,
        "sell_signals": sell_signals
    }
