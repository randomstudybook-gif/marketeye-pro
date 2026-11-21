from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import time

app = FastAPI()

SCAN_UNIVERSE = [
    "BHARTIARTL", "RELIANCE", "TCS", "HDFCBANK", "INFY", "SBIN",
    "TATAMOTORS", "TATASTEEL", "ZOMATO", "IRCTC", "HAL", "BEL",
    "ITC", "AXISBANK", "WIPRO", "IDEA", "YESBANK", "SUZLON"
]

NSE_STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd"},
    {"symbol": "INFY", "name": "Infosys Ltd"},
    {"symbol": "SBIN", "name": "State Bank of India"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd"},
    {"symbol": "ITC", "name": "ITC Ltd"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd"},
    {"symbol": "TITAN", "name": "Titan Company Ltd"},
    {"symbol": "NTPC", "name": "NTPC Ltd"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd"},
    {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ Ltd"},
    {"symbol": "WIPRO", "name": "Wipro Ltd"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd"},
    {"symbol": "TECHM", "name": "Tech Mahindra Ltd"},
    {"symbol": "ZOMATO", "name": "Zomato Ltd"},
    {"symbol": "IRCTC", "name": "IRCTC Ltd"},
    {"symbol": "HAL", "name": "Hindustan Aeronautics Ltd"},
    {"symbol": "BEL", "name": "Bharat Electronics Ltd"},
    {"symbol": "TRENT", "name": "Trent Ltd"},
    {"symbol": "DIXON", "name": "Dixon Technologies India Ltd"},
    {"symbol": "SUZLON", "name": "Suzlon Energy Ltd"},
    {"symbol": "IDEA", "name": "Vodafone Idea Ltd"},
    {"symbol": "YESBANK", "name": "Yes Bank Ltd"}
]

CACHE = {}
CACHE_TTL = 180

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_stock(symbol: str, include_chart: bool = False):
    clean_sym = symbol.upper().strip().replace(".NS", "")
    cache_key = f"{clean_sym}_{include_chart}"
    now = time.time()

    if cache_key in CACHE and (now - CACHE[cache_key]["ts"] < CACHE_TTL):
        return CACHE[cache_key]["data"]

    ticker_sym = f"{clean_sym}.NS"
    try:
        ticker = yf.Ticker(ticker_sym)
        df = ticker.history(period="6mo", interval="1d")
        if df.empty or len(df) < 30:
            return None

        close = df["Close"]
        volume = df["Volume"]
        current_price = round(float(close.iloc[-1]), 2)
        prev_price = round(float(close.iloc[-2]), 2)
        change_pct = round(((current_price - prev_price) / prev_price) * 100, 2)

        df["EMA20"] = close.ewm(span=20, adjust=False).mean()
        df["EMA50"] = close.ewm(span=50, adjust=False).mean()
        df["RSI"] = calculate_rsi(close, 14)

        ema20 = round(float(df["EMA20"].iloc[-1]), 2)
        ema50 = round(float(df["EMA50"].iloc[-1]), 2)
        rsi = round(float(df["RSI"].iloc[-1]), 1)

        avg_vol = float(volume.iloc[-20:-1].mean())
        curr_vol = float(volume.iloc[-1])
        vol_ratio = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        # 1. Technical Pillar (Max 30 pts)
        tech_score = 15
        if current_price > ema20:
            tech_score += 6
        else:
            tech_score -= 6
        if current_price > ema50:
            tech_score += 5
        else:
            tech_score -= 5
        if 45 <= rsi <= 68:
            tech_score += 4
        elif rsi > 75 or rsi < 35:
            tech_score -= 3
        tech_score = max(0, min(30, tech_score))

        tech_grade = "Bullish" if tech_score >= 21 else ("Neutral" if tech_score >= 13 else "Bearish")

        # Fast fundamentals (safe fallback so requests never stall)
        pe = pb = roe = de = rev_growth = None
        company_name = clean_sym
        if include_chart:
            try:
                info = ticker.info or {}
                pe = info.get("trailingPE")
                pb = info.get("priceToBook")
                roe = info.get("returnOnEquity")
                de = info.get("debtToEquity")
                rev_growth = info.get("revenueGrowth")
                company_name = info.get("shortName") or clean_sym
            except Exception:
                pass

        # 2. Valuation Pillar (Max 25 pts)
        val_score = 14
        if isinstance(pe, (int, float)) and pe > 0:
            val_score += 8 if pe < 22 else (3 if pe <= 40 else -6)
        if isinstance(pb, (int, float)) and pb > 0:
            val_score += 3 if pb < 4 else (-3 if pb > 10 else 0)
        val_score = max(0, min(25, val_score))
        val_grade = "Attractive" if val_score >= 18 else ("Fair" if val_score >= 11 else "Expensive")

        # 3. Quality Pillar (Max 25 pts)
        qual_score = 14
        if isinstance(roe, (int, float)):
            qual_score += 7 if roe >= 0.15 else (2 if roe >= 0.08 else -4)
        if isinstance(de, (int, float)):
            qual_score += 4 if de < 50 else (-5 if de > 150 else 0)
        qual_score = max(0, min(25, qual_score))
        qual_grade = "Strong" if qual_score >= 18 else ("Average" if qual_score >= 11 else "Weak")

        # 4. Trend Pillar (Max 20 pts)
        ret_1m = ((current_price - float(close.iloc[-22])) / float(close.iloc[-22])) * 100
        trend_score = 10 + (6 if ret_1m > 4 else (-6 if ret_1m < -4 else 0))
        if isinstance(rev_growth, (int, float)):
            trend_score += 4 if rev_growth > 0.10 else (-4 if rev_growth < 0 else 0)
        trend_score = max(0, min(20, trend_score))
        trend_grade = "Positive" if trend_score >= 14 else ("Flat" if trend_score >= 8 else "Negative")

        mojo_score = int(tech_score + val_score + qual_score + trend_score)

        # Swing Support & Resistance Levels
        swing_low = round(float(df["Low"].iloc[-12:].min()), 2)
        swing_high = round(float(df["High"].iloc[-12:].max()), 2)

        # Ideal Buy Entry Zone (Near 20-EMA / Support)
        buy_base = round(min(current_price, max(ema20, swing_low)), 2)
        buy_low = round(buy_base * 0.992, 2)
        buy_high = round(buy_base * 1.005, 2)
        buy_sl = round(min(swing_low * 0.985, buy_low * 0.97), 2)
        buy_risk = max(buy_high - buy_sl, current_price * 0.02)
        buy_target = round(buy_high + (buy_risk * 2.0), 2)

        # Ideal Sell / Short Entry Zone (Near 20-EMA / Resistance)
        sell_base = round(max(current_price, min(ema20, swing_high)), 2)
        sell_low = round(sell_base * 0.995, 2)
        sell_high = round(sell_base * 1.008, 2)
        sell_sl = round(max(swing_high * 1.015, sell_high * 1.03), 2)
        sell_risk = max(sell_sl - sell_low, current_price * 0.02)
        sell_target = round(max(1.0, sell_low - (sell_risk * 2.0)), 2)

        # Side Classification (BUY vs SELL)
        if current_price >= ema20 and tech_score >= 16:
            side = "BUY"
            signal = "STRONG BUY" if mojo_score >= 70 else "BUY"
            active_sl = buy_sl
            active_target = buy_target
        else:
            side = "SELL"
            signal = "STRONG SELL" if tech_score <= 10 else "SELL"
            active_sl = sell_sl
            active_target = sell_target

        logic = f"20-EMA: ₹{ema20} | 50-EMA: ₹{ema50} | Support: ₹{swing_low} | Resistance: ₹{swing_high} | 1M: {round(ret_1m, 1)}%"

        result = {
            "symbol": clean_sym,
            "name": company_name,
            "price": current_price,
            "change_pct": change_pct,
            "mojo_score": mojo_score,
            "side": side,
            "signal": signal,
            "pillars": {
                "technical": tech_grade,
                "valuation": val_grade,
                "quality": qual_grade,
                "trend": trend_grade
            },
            "trade_zones": {
                "buy_zone": f"₹{buy_low} - ₹{buy_high}",
                "buy_sl": buy_sl,
                "buy_target": buy_target,
                "sell_zone": f"₹{sell_low} - ₹{sell_high}",
                "sell_sl": sell_sl,
                "sell_target": sell_target
            },
            "rsi": rsi,
            "volume_spike": f"{vol_ratio}x",
            "stop_loss": active_sl,
            "target": active_target,
            "logic": logic
        }@app.get("/manifest.json")
def serve_manifest():
    with open("manifest.json", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="application/manifest+json")