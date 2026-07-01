import os
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

load_dotenv()

SEMICONDUCTOR_STOCKS = [
    "POWI", "COHU", "JBL", "DQ", "QRVO", "PWR", "MTSI", "FORM", "Q", "SITM", 
    "ASML", "ONTO", "CDNS", "SMTC", "SNPS", "STX", "ALGM", "AMKR", "KEYS", 
    "GFS", "TER", "ARR", "LSCC", "SWKS", "NXPI", "ENTG", "COHR", "WDC", 
    "FLEX", "AMAT", "AXTI", "WOLF", "TXN", "LRCX", "SNDK", "ON", "ASX", 
    "TSM", "ADI", "MCHP", "STM", "UMC", "AVGO", "ARM", "QCOM", "MRVL", 
    "AMD", "MU", "INTC", "NVDA"
]

def generate_chart(df, ticker, signal_type):
    plt.figure(figsize=(8, 4))
    
    # Plot last 30 days if available
    plot_df = df.tail(30)
    
    plt.plot(plot_df.index, plot_df['Close'], label='Close Price', color='blue', linewidth=2)
    plt.plot(plot_df.index, plot_df['SMA_9'], label='9-Day SMA', color='orange', linestyle='--')
    
    # Mark the last point
    last_date = plot_df.index[-1]
    last_close = plot_df['Close'].iloc[-1]
    marker_color = 'green' if signal_type == 'BUY' else 'red'
    plt.scatter(last_date, last_close, color=marker_color, s=100, zorder=5)
    
    plt.title(f"{ticker} - Daily Chart - {signal_type} Signal")
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf.read()

def get_9_sma_signals():
    buy_signals = []
    sell_signals = []
    
    # Download 40 days to safely calculate 9-SMA and have 30 days for plot
    data = yf.download(SEMICONDUCTOR_STOCKS, period="40d", threads=True)
    
    is_multiindex = isinstance(data.columns, pd.MultiIndex)
    
    for ticker in SEMICONDUCTOR_STOCKS:
        try:
            if is_multiindex:
                if 'Close' in data.columns.levels[0]:
                    if ticker not in data['Close'].columns: continue
                    close_prices = data['Close'][ticker].dropna()
                else:
                    if ticker not in data.columns.levels[0]: continue
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
                
            signal_type = None
            if prev['Close'] <= prev['SMA_9'] and latest['Close'] > latest['SMA_9']:
                signal_type = 'BUY'
            elif prev['Close'] >= prev['SMA_9'] and latest['Close'] < latest['SMA_9']:
                signal_type = 'SELL'
                
            if signal_type:
                chart_image = generate_chart(df, ticker, signal_type)
                signal_data = {
                    'ticker': ticker,
                    'close': latest['Close'],
                    'sma9': latest['SMA_9'],
                    'image': chart_image
                }
                
                if signal_type == 'BUY':
                    buy_signals.append(signal_data)
                else:
                    sell_signals.append(signal_data)
                    
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
        
    subject = "Daily Semiconductor 9-SMA Signals with Charts"
    msg = MIMEMultipart('related')
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    
    html = """
    <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; }
          .signal-box { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 8px; }
          .buy { color: #28a745; }
          .sell { color: #dc3545; }
          img { max-width: 100%; height: auto; border: 1px solid #eee; margin-top: 10px; }
        </style>
      </head>
      <body>
        <h2>Daily Semiconductor 9-SMA Signals</h2>
        <p>Here are the 9-day SMA crossover signals for your 50 semiconductor stocks after today's close:</p>
    """
    
    image_attachments = []
    
    if buy_signals:
        html += "<h3 class='buy'>=== BUY SIGNALS (Close crossed above 9-SMA) ===</h3>"
        for idx, s in enumerate(buy_signals):
            cid = f"buy_{idx}"
            html += f"""
            <div class='signal-box'>
                <strong>{s['ticker']}</strong> - Close: ${s['close']:.2f} | SMA9: ${s['sma9']:.2f}<br>
                <img src="cid:{cid}">
            </div>
            """
            image_attachments.append((cid, s['image']))
            
    if sell_signals:
        html += "<h3 class='sell'>=== SELL SIGNALS (Close crossed below 9-SMA) ===</h3>"
        for idx, s in enumerate(sell_signals):
            cid = f"sell_{idx}"
            html += f"""
            <div class='signal-box'>
                <strong>{s['ticker']}</strong> - Close: ${s['close']:.2f} | SMA9: ${s['sma9']:.2f}<br>
                <img src="cid:{cid}">
            </div>
            """
            image_attachments.append((cid, s['image']))
            
    html += "<p>Regards,<br>Stocklytics System</p></body></html>"
    
    msg_alternative.attach(MIMEText("Please enable HTML to view this email properly.", 'plain'))
    msg_alternative.attach(MIMEText(html, 'html'))
    
    # Attach images
    for cid, img_data in image_attachments:
        image = MIMEImage(img_data)
        image.add_header('Content-ID', f'<{cid}>')
        image.add_header('Content-Disposition', 'inline')
        msg.attach(image)
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
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
        "buy_signals": len(buy_signals),
        "sell_signals": len(sell_signals)
    }
