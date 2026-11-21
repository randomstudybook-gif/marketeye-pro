from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import pandas as pd
import time

app = FastAPI()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

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
CACHE_TTL = 300

def fetch_yahoo_chart(yahoo_symbol: str, range_str: str = "6mo") -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?range={range_str}&interval=1d"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            url2 = f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?range={range_str}&interval=1d"
            resp = requests.get(url2, headers=HEADERS, timeout=8)
        data = resp.json()
        res = data["chart"]["result"][0]
        timestamps = res["timestamp"]
        quote = res["indicators"]["quote"][0]
        df = pd.DataFrame({
            "Open": quote["open"],
            "High": quote["high"],
            "Low": quote["low"],
            "Close": quote["close"],
            "Volume": quote["volume"]
        }, index=pd.to_datetime(timestamps, unit="s"))
        return df.dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def analyze_stock(clean_sym: str, include_chart: bool = False):
    clean_sym = clean_sym.upper().strip().replace(".NS", "")
    cache_key = f"{clean_sym}_{include_chart}"
    now = time.time()
    if cache_key in CACHE and (now - CACHE[cache_key]["ts"] < CACHE_TTL):
        return CACHE[cache_key]["data"]

    df = fetch_yahoo_chart(f"{clean_sym}.NS", "6mo")
    if df.empty or len(df) < 15:
        return None

    close = df["Close"]
    volume = df["Volume"].fillna(0)
    current_price = round(float(close.iloc[-1]), 2)
    prev_price = round(float(close.iloc[-2]), 2) if len(close) > 1 else current_price
    change_pct = round(((current_price - prev_price) / prev_price) * 100, 2) if prev_price else 0.0

    ema20_series = close.ewm(span=20, adjust=False).mean()
    ema50_series = close.ewm(span=50, adjust=False).mean()
    rsi_series = calculate_rsi(close, 14)

    ema20 = round(float(ema20_series.iloc[-1]), 2)
    ema50 = round(float(ema50_series.iloc[-1]), 2)
    rsi_val = rsi_series.iloc[-1]
    rsi = round(float(rsi_val), 1) if pd.notna(rsi_val) else 50.0

    avg_vol = float(volume.iloc[-20:-1].mean()) if len(volume) > 5 else float(volume.mean())
    curr_vol = float(volume.iloc[-1])
    vol_ratio = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

    tech_score = 15
    tech_score += 6 if current_price > ema20 else -6
    tech_score += 5 if current_price > ema50 else -5
    if 45 <= rsi <= 68:
        tech_score += 4
    elif rsi > 75 or rsi < 35:
        tech_score -= 3
    tech_score = max(0, min(30, tech_score))
    tech_grade = "Bullish" if tech_score >= 21 else ("Neutral" if tech_score >= 13 else "Bearish")

    lookback = min(22, len(close) - 1)
    ret_1m = ((current_price - float(close.iloc[-1 - lookback])) / float(close.iloc[-1 - lookback])) * 100 if lookback > 0 else 0.0
    trend_score = max(0, min(20, 10 + (6 if ret_1m > 4 else (-6 if ret_1m < -4 else 0))))
    trend_grade = "Positive" if trend_score >= 14 else ("Flat" if trend_score >= 8 else "Negative")

    mojo_score = int(tech_score + 15 + 16 + trend_score)

    swing_low = round(float(df["Low"].iloc[-12:].min()), 2)
    swing_high = round(float(df["High"].iloc[-12:].max()), 2)

    buy_base = round(min(current_price, max(ema20, swing_low)), 2)
    buy_low = round(buy_base * 0.992, 2)
    buy_high = round(buy_base * 1.005, 2)
    buy_sl = round(min(swing_low * 0.985, buy_low * 0.97), 2)
    buy_risk = max(buy_high - buy_sl, current_price * 0.02)
    buy_target = round(buy_high + (buy_risk * 2.0), 2)

    sell_base = round(max(current_price, min(ema20, swing_high)), 2)
    sell_low = round(sell_base * 0.995, 2)
    sell_high = round(sell_base * 1.008, 2)
    sell_sl = round(max(swing_high * 1.015, sell_high * 1.03), 2)
    sell_risk = max(sell_sl - sell_low, current_price * 0.02)
    sell_target = round(max(1.0, sell_low - (sell_risk * 2.0)), 2)

    if current_price >= ema20 and tech_score >= 16:
        side = "BUY"
        signal = "STRONG BUY" if mojo_score >= 70 else "BUY"
        active_sl, active_target = buy_sl, buy_target
    else:
        side = "SELL"
        signal = "STRONG SELL" if tech_score <= 10 else "SELL"
        active_sl, active_target = sell_sl, sell_target

    name_map = {s["symbol"]: s["name"] for s in NSE_STOCKS}
    result = {
        "symbol": clean_sym,
        "name": name_map.get(clean_sym, clean_sym),
        "price": current_price,
        "change_pct": change_pct,
        "mojo_score": mojo_score,
        "side": side,
        "signal": signal,
        "pillars": {
            "technical": tech_grade,
            "valuation": "Fair",
            "quality": "Strong" if current_price > ema50 else "Average",
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
        "logic": f"20-EMA: ₹{ema20} | 50-EMA: ₹{ema50} | Support: ₹{swing_low} | Resistance: ₹{swing_high} | 1M: {round(ret_1m, 1)}%"
    }

    if include_chart:
        sub = df.tail(60)
        candles, ema20_list, volumes = [], [], []
        for idx, row in sub.iterrows():
            dt = idx.strftime("%Y-%m-%d")
            candles.append({
                "time": dt,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2)
            })
            ema20_list.append({"time": dt, "value": round(float(ema20_series.loc[idx]), 2)})
            volumes.append({"time": dt, "value": int(row["Volume"])})
        result["chart"] = {"candles": candles, "ema20": ema20_list, "volumes": volumes}

    CACHE[cache_key] = {"ts": now, "data": result}
    return result

@app.get("/", response_class=HTMLResponse)
def serve_home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/manifest.json")
def serve_manifest():
    with open("manifest.json", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="application/manifest+json")

@app.get("/indices")
def get_indices():
    now = time.time()
    if "INDICES" in CACHE and (now - CACHE["INDICES"]["ts"] < CACHE_TTL):
        return CACHE["INDICES"]["data"]

    out = {"nifty": {"price": 0, "change_pct": 0}, "banknifty": {"price": 0, "change_pct": 0}}
    for key, sym in [("nifty", "%5ENSEI"), ("banknifty", "%5ENSEBANK")]:
        df_i = fetch_yahoo_chart(sym, "5d")
        if len(df_i) >= 2:
            c1 = float(df_i["Close"].iloc[-1])
            c0 = float(df_i["Close"].iloc[-2])
            out[key] = {"price": round(c1, 2), "change_pct": round(((c1 - c0) / c0) * 100, 2)}

    CACHE["INDICES"] = {"ts": now, "data": out}
    return out

@app.get("/suggest/{query}")
def suggest_stocks(query: str):
    q = query.upper().strip()
    matches = [s for s in NSE_STOCKS if s["symbol"].startswith(q) or q in s["name"].upper()][:6]
    return {"suggestions": matches}

@app.get("/search/{symbol}")
def search_stock(symbol: str):
    res = analyze_stock(symbol, include_chart=True)
    if not res:
        return {"error": f"'{symbol.upper()}' साठी डेटा उपलब्ध नाही. कृपया योग्य NSE सिम्बॉल तपासा."}
    return {"stock": res}

@app.get("/signals")
def get_signals(symbols: str = None):
    sym_list = [s.upper().strip().replace(".NS", "") for s in symbols.split(",") if s.strip()] if symbols else SCAN_UNIVERSE
    stocks = []
    for sym in sym_list:
        res = analyze_stock(sym, include_chart=False)
        if res:
            stocks.append(res)
    return {"stocks": stocks}
