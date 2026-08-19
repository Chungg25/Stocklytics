from ddgs import DDGS
from datetime import datetime
import yfinance as yf

import trafilatura

def get_latest_news(ticker: str, max_results: int = 3) -> str:
    """
    Sử dụng DuckDuckGo Search để cào link, sau đó dùng Trafilatura đọc TOÀN BỘ bài báo.
    """
    try:
        results = DDGS().news(f"{ticker} stock news OR economy", max_results=max_results)
        if not results:
            return "Không tìm thấy tin tức nào đáng chú ý trong 24h qua."
            
        news_text = f"--- CẬP NHẬT TIN TỨC THỜI GIAN THỰC (Lấy lúc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n\n"
        for i, article in enumerate(results):
            title = article.get('title', '')
            url = article.get('url', '')
            
            full_content = ""
            if url:
                try:
                    downloaded = trafilatura.fetch_url(url)
                    if downloaded:
                        text = trafilatura.extract(downloaded)
                        if text:
                            full_content = text[:2000] + "..." # Lay 2000 ky tu dau cua bai bao
                except Exception:
                    pass
                    
            if not full_content:
                full_content = article.get('body', '')
                
            news_text += f"Tin {i+1}:\n"
            news_text += f"- Tiêu đề: {title}\n"
            news_text += f"- Nội dung CHI TIẾT bài báo:\n{full_content}\n"
            news_text += f"- Nguồn: {article.get('source', '')}\n\n"
            
        return news_text
    except Exception as e:
        return f"Không thể lấy được tin tức do lỗi mạng hoặc API: {str(e)}"

def get_fundamental_data(ticker: str) -> str:
    """Sử dụng yfinance để lấy báo cáo tài chính và dữ liệu cơ bản."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Trích xuất các chỉ số cốt lõi
        summary = info.get("longBusinessSummary", "Không có thông tin mô hình kinh doanh")
        industry = info.get("industry", "Không rõ")
        sector = info.get("sector", "Không rõ")
        
        trailing_pe = info.get("trailingPE", "N/A")
        forward_pe = info.get("forwardPE", "N/A")
        pb_ratio = info.get("priceToBook", "N/A")
        
        roe = info.get("returnOnEquity", "N/A")
        roa = info.get("returnOnAssets", "N/A")
        operating_margin = info.get("operatingMargins", "N/A")
        gross_margin = info.get("grossMargins", "N/A")
        
        total_cash = info.get("totalCash", "N/A")
        total_debt = info.get("totalDebt", "N/A")
        debt_to_equity = info.get("debtToEquity", "N/A")
        
        revenue_growth = info.get("revenueGrowth", "N/A")
        earnings_growth = info.get("earningsGrowth", "N/A")
        
        # Định dạng thành chuỗi đọc được cho AI
        result = (
            f"Ngành (Industry/Sector): {industry} / {sector}\n"
            f"Tóm tắt Mô hình Kinh doanh: {summary[:500]}...\n\n"
            f"--- ĐỊNH GIÁ (VALUATION) ---\n"
            f"Trailing P/E: {trailing_pe}\n"
            f"Forward P/E: {forward_pe}\n"
            f"P/B Ratio: {pb_ratio}\n\n"
            f"--- HIỆU QUẢ SINH LỜI (PROFITABILITY) ---\n"
            f"ROE: {roe}\n"
            f"ROA: {roa}\n"
            f"Biên lợi nhuận gộp (Gross Margin): {gross_margin}\n"
            f"Biên lợi nhuận hoạt động (Op Margin): {operating_margin}\n\n"
            f"--- SỨC KHỎE TÀI CHÍNH (BALANCE SHEET) ---\n"
            f"Tổng tiền mặt (Total Cash): {total_cash}\n"
            f"Tổng nợ (Total Debt): {total_debt}\n"
            f"Tỷ lệ Nợ/Vốn chủ sở hữu (Debt to Equity): {debt_to_equity}\n\n"
            f"--- TĂNG TRƯỞNG (GROWTH) ---\n"
            f"Tăng trưởng Doanh thu: {revenue_growth}\n"
            f"Tăng trưởng Lợi nhuận: {earnings_growth}\n"
        )
        return result
    except Exception as e:
        return f"Lỗi khi lấy dữ liệu cơ bản: {e}"

def get_technical_indicators(ticker: str) -> str:
    """
    Sử dụng yfinance và pandas để tính toán chính xác các chỉ báo kỹ thuật thời gian thực.
    """
    import pandas as pd
    try:
        # Lấy dữ liệu 1 năm
        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty:
            return "Không có dữ liệu lịch sử để tính toán chỉ báo."
            
        current_price = hist['Close'].iloc[-1]
        
        # Đường trung bình
        sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # Đỉnh / Đáy 52 tuần (Đóng vai trò Kháng cự / Hỗ trợ cứng)
        high_52w = hist['High'].max()
        low_52w = hist['Low'].min()
        
        # Tính RSI (14) theo công thức chuẩn Wilder's Smoothing
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        ema_gain = gain.ewm(com=13, adjust=False).mean()
        ema_loss = loss.ewm(com=13, adjust=False).mean()
        rs = ema_gain / ema_loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        ta_text = (
            f"--- DỮ LIỆU PHÂN TÍCH KỸ THUẬT (THỰC TẾ CỦA PYTHON) ---\n"
            f"- Current Price (Giá hiện tại): ${current_price:.2f}\n"
            f"- SMA 50 (Trung bình 50 ngày): ${sma50:.2f}\n"
            f"- SMA 200 (Trung bình 200 ngày): ${sma200:.2f}\n"
            f"- RSI 14 (Chỉ số Sức mạnh): {rsi:.2f}\n"
            f"- 52-Week High (Đỉnh 1 năm - Kháng cự): ${high_52w:.2f}\n"
            f"- 52-Week Low (Đáy 1 năm - Hỗ trợ): ${low_52w:.2f}\n"
        )
        return ta_text
    except Exception as e:
        return f"Lỗi tính toán TA: {str(e)}"
