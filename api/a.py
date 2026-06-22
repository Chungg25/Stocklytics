import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt


def calculate_sentiment(hist):
    """
    Sentiment đơn giản:
    - Giá tăng + volume tăng => Bullish
    - Giá giảm + volume tăng => Bearish
    - Còn lại => Neutral
    """

    if len(hist) < 20:
        return "Neutral"

    recent_price_change = (
        hist["Close"].iloc[-1] - hist["Close"].iloc[-20]
    ) / hist["Close"].iloc[-20] * 100

    recent_volume = hist["Volume"].tail(20).mean()
    avg_volume = hist["Volume"].mean()

    if recent_price_change > 5 and recent_volume > avg_volume:
        return "Bullish 🟢"

    elif recent_price_change < -5 and recent_volume > avg_volume:
        return "Bearish 🔴"

    return "Neutral 🟡"


def get_stock_info(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)

    info = ticker.info

    # Lấy lịch sử 1 năm
    hist_1y = ticker.history(period="1y")

    if hist_1y.empty:
        raise ValueError(f"Không có dữ liệu cho {ticker_symbol}")

    current_price = hist_1y["Close"].iloc[-1]
    prev_close = info.get("previousClose")

    # % change
    if prev_close:
        change_pct = ((current_price - prev_close) / prev_close) * 100
    else:
        change_pct = None

    # Market Cap
    market_cap = info.get("marketCap")

    # ROI 1 năm
    start_price = hist_1y["Close"].iloc[0]
    roi_1y = ((current_price - start_price) / start_price) * 100

    sentiment = calculate_sentiment(hist_1y)

    return {
        "symbol": ticker_symbol,
        "price": round(current_price, 2),
        "change_pct": round(change_pct, 2) if change_pct else None,
        "market_cap": market_cap,
        "roi_1y": round(roi_1y, 2),
        "sentiment": sentiment,
        "hist": hist_1y
    }


def format_market_cap(value):
    if not value:
        return "N/A"

    if value >= 1e12:
        return f"${value/1e12:.2f}T"

    if value >= 1e9:
        return f"${value/1e9:.2f}B"

    if value >= 1e6:
        return f"${value/1e6:.2f}M"

    return f"${value:,.0f}"


def plot_last_30_days(hist, symbol):
    last_30 = hist.tail(30)

    plt.figure(figsize=(10, 4))
    plt.plot(last_30.index, last_30["Close"], linewidth=2)
    plt.title(f"{symbol} - Last 30 Days")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    symbol = "AAPL"

    data = get_stock_info(symbol)

    print("\n===== STOCK INFO =====")
    print(f"Symbol      : {data['symbol']}")
    print(f"Price       : ${data['price']}")
    print(f"Change      : {data['change_pct']}%")
    print(f"Market Cap  : {format_market_cap(data['market_cap'])}")
    print(f"Sentiment   : {data['sentiment']}")
    print(f"ROI% 1Y     : {data['roi_1y']}%")

    plot_last_30_days(data["hist"], symbol)