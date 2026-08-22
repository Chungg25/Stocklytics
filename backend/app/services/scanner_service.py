import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy.signal import find_peaks
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

def cluster_levels(levels, threshold_pct=0.03, min_touches=2):
    levels = sorted(levels)
    if not levels: return []
    zones = []
    current_zone = [levels[0]]
    for lvl in levels[1:]:
        if (lvl - current_zone[0]) / current_zone[0] <= threshold_pct:
            current_zone.append(lvl)
        else:
            if len(current_zone) >= min_touches:
                zones.append((min(current_zone), max(current_zone)))
            current_zone = [lvl]
    if len(current_zone) >= min_touches:
        zones.append((min(current_zone), max(current_zone)))
    return zones

def generate_chart(df, ticker, active_res, active_sup):
    plt.figure(figsize=(10, 6))
    
    # Plot last 60 days
    plot_df = df.tail(60)
    
    plt.plot(plot_df.index, plot_df['Close'], label='Close Price', color='blue')
    
    # Draw only the ACTIVE zones that are relevant to the current price
    if active_res:
        plt.axhspan(active_res[0], active_res[1], color='red', alpha=0.3, label='Active Resistance')
        
    if active_sup:
        plt.axhspan(active_sup[0], active_sup[1], color='green', alpha=0.3, label='Active Support')
    
    plt.title(f"{ticker} - Daily Chart & Active S/R Zones")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf.getvalue()

def get_signals():
    buy_signals = []
    sell_signals = []
    charts_data = {}
    
    # 1 year of data for sufficient pivot points
    data = yf.download(SEMICONDUCTOR_STOCKS, period="1y", interval="1d", threads=True)
    
    is_multiindex = isinstance(data.columns, pd.MultiIndex)
    
    for ticker in SEMICONDUCTOR_STOCKS:
        try:
            if is_multiindex:
                if 'Close' in data.columns.levels[0]:
                    if ticker not in data['Close'].columns:
                        continue
                    close_prices = data['Close'][ticker].dropna()
                    high_prices = data['High'][ticker].dropna()
                    low_prices = data['Low'][ticker].dropna()
                else:
                    if ticker not in data.columns.levels[0]:
                        continue
                    close_prices = data[ticker]['Close'].dropna()
                    high_prices = data[ticker]['High'].dropna()
                    low_prices = data[ticker]['Low'].dropna()
            else:
                if len(SEMICONDUCTOR_STOCKS) == 1:
                    close_prices = data['Close'].dropna()
                    high_prices = data['High'].dropna()
                    low_prices = data['Low'].dropna()
                else:
                    continue
                    
            if len(close_prices) < 100:
                continue
                
            df = pd.DataFrame({
                'Close': close_prices,
                'High': high_prices,
                'Low': low_prices
            })
            
            # Find local peaks (highs) and valleys (lows) with distance=5 days
            peaks, _ = find_peaks(df['High'].values, distance=5)
            valleys, _ = find_peaks(-df['Low'].values, distance=5)
            
            # Exclude the very last day from pivots to not peek ahead
            peaks = [p for p in peaks if p < len(df)-1]
            valleys = [v for v in valleys if v < len(df)-1]
            
            res_levels = df['High'].iloc[peaks].values
            sup_levels = df['Low'].iloc[valleys].values
            
            # Cluster into zones (3% threshold, minimum 2 touches)
            res_zones = cluster_levels(res_levels, threshold_pct=0.03, min_touches=2)
            sup_zones = cluster_levels(sup_levels, threshold_pct=0.03, min_touches=2)
            
            latest_close = df.iloc[-1]['Close']
            prev_close = df.iloc[-2]['Close']
            
            # Find active nearest Resistance above prev_close
            active_res = None
            for r_min, r_max in sorted(res_zones):
                if r_max > prev_close:
                    active_res = (r_min, r_max)
                    break
                    
            # Find active nearest Support below prev_close
            active_sup = None
            for s_min, s_max in sorted(sup_zones, reverse=True):
                if s_min < prev_close:
                    active_sup = (s_min, s_max)
                    break
            
            signal_triggered = False
            
            # Breakout BUY: crosses above the active Resistance zone top
            if active_res and prev_close <= active_res[1] and latest_close > active_res[1]:
                msg = f"{ticker} (Close: {latest_close:.2f}, Broke Resistance Zone: {active_res[0]:.2f}-{active_res[1]:.2f})"
                buy_signals.append(msg)
                signal_triggered = True
                
            # Breakdown SELL: crosses below the active Support zone bottom
            elif active_sup and prev_close >= active_sup[0] and latest_close < active_sup[0]:
                msg = f"{ticker} (Close: {latest_close:.2f}, Broke Support Zone: {active_sup[0]:.2f}-{active_sup[1]:.2f})"
                sell_signals.append(msg)
                signal_triggered = True
                
            if signal_triggered:
                charts_data[ticker] = generate_chart(df, ticker, active_res, active_sup)
                
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            
    return buy_signals, sell_signals, charts_data

def send_email(buy_signals, sell_signals, charts_data):
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("SENDER_PASSWORD")
    receiver = os.environ.get("RECEIVER_EMAIL")
    
    if not sender or not password or not receiver:
        print("Email credentials not configured properly in .env.")
        return
        
    if not buy_signals and not sell_signals:
        print("No signals today, skipping email.")
        return
        
    subject = "Daily Advanced S/R Breakout Signals"
    
    html_body = """
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #2c3e50;">Alphahubiq: Daily Breakout Signals</h2>
        <p>Hello,</p>
        <p>Here is your daily report for the <strong>Support/Resistance Breakout</strong> strategy.</p>
    """
    
    if buy_signals:
        html_body += """
        <div style="margin-bottom: 20px;">
            <h3 style="color: #27ae60; border-bottom: 2px solid #27ae60; padding-bottom: 5px;">✅ BUY SIGNALS (Breakout Above Resistance)</h3>
            <ul style="list-style-type: none; padding-left: 0;">
        """
        for s in buy_signals:
            html_body += f"<li style='margin-bottom: 5px; padding: 10px; background-color: #eafaf1; border-left: 4px solid #27ae60;'><strong>{s}</strong></li>"
        html_body += "</ul></div>"
        
    if sell_signals:
        html_body += """
        <div style="margin-bottom: 20px;">
            <h3 style="color: #c0392b; border-bottom: 2px solid #c0392b; padding-bottom: 5px;">❌ SELL SIGNALS (Breakdown Below Support)</h3>
            <ul style="list-style-type: none; padding-left: 0;">
        """
        for s in sell_signals:
            html_body += f"<li style='margin-bottom: 5px; padding: 10px; background-color: #fdedec; border-left: 4px solid #c0392b;'><strong>{s}</strong></li>"
        html_body += "</ul></div>"
        
    html_body += """
        <p><i>The corresponding charts are attached to this email.</i></p>
        <br>
        <p>Best Regards,<br><strong>Alphahubiq System</strong></p>
      </body>
    </html>
    """
        
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    
    for ticker, img_data in charts_data.items():
        image = MIMEImage(img_data, name=f"{ticker}_Daily_SR_Breakout.png")
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
    print("Starting Advanced S/R daily scan...")
    buy_signals, sell_signals, charts_data = get_signals()
    print(f"Found {len(buy_signals)} BUY and {len(sell_signals)} SELL signals.")
    
    if buy_signals or sell_signals:
        send_email(buy_signals, sell_signals, charts_data)
    
    return {
        "status": "success",
        "buy_signals": buy_signals,
        "sell_signals": sell_signals
    }
