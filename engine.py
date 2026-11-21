from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from concurrent.futures import ThreadPoolExecutor
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

FNO_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK", "INFY",
    "SBIN", "TATAMOTORS", "TATASTEEL", "AXISBANK", "HAL", "BEL",
    "ITC", "BAJFINANCE", "LT", "SUNPHARMA", "MARUTI", "WIPRO"
]

NSE_STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "fno": True},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "fno": True},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "fno": True},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "fno": True},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "fno": True},
    {"symbol": "INFY", "name": "Infosys Ltd", "fno": True},
    {"symbol": "SBIN", "name": "State Bank of India", "fno": True},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "fno": True},
    {"symbol": "ITC", "name": "ITC Ltd", "fno": True},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "fno": True},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "fno": True},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "fno": True},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries", "fno": True},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "fno": True},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "fno": True},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "fno": True},
    {"symbol": "NTPC", "name": "NTPC Ltd", "fno": True},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "fno": True},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "fno": True},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "fno": True},
    {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ Ltd", "fno": True},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "fno": True},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "fno": True},
    {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "fno": True},
    {"symbol": "ZOMATO", "name": "Zomato Ltd", "fno": False},
    {"symbol": "IRCTC", "name": "IRCTC Ltd", "fno": True},
    {"symbol": "HAL", "name": "Hindustan Aeronautics Ltd", "fno": True},
    {"symbol": "BEL", "name": "Bharat Electronics Ltd", "fno": True},
    {"symbol": "TRENT", "name": "Trent Ltd", "fno": True},
    {"symbol": "DIXON", "name": "Dixon Technologies India Ltd", "fno": True},
    {"symbol": "SUZLON", "name": "Suzlon Energy Ltd", "fno": False},
    {"symbol": "IDEA", "name": "Vodafone Idea Ltd", "fno": True},
    {"symbol": "YESBANK", "name": "Yes Bank Ltd", "fno": False}
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

def fetch_nse_option_chain(symbol: str, spot_price: float = 0.0, is_index: bool = True):
    cache_key = f"OC_{symbol}"
    now = time.time()
    if cache_key in CACHE and (now - CACHE[cache_key]["ts"] < CACHE_TTL):
        return CACHE[cache_key]["data"]

    try:
        session = requests.Session()
        nse_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/option-chain"
        }
        session.get("https://www.nseindia.com", headers=nse_headers, timeout=5)
        endpoint = "option-chain-indices" if is_index else "option-chain-equities"
        oc_url = f"https://www.nseindia.com/api/{endpoint}?symbol={symbol}"
        r = session.get(oc_url, headers=nse_headers, timeout=6)
        if r.status_code == 200:
            raw = r.json()
            records = raw.get("records", {}).get("data", [])
            expiry = raw.get("records", {}).get("expiryDates", [""])[0]
            tot_ce_oi, tot_pe_oi = 0, 0
            max_ce_oi, res_strike = 0, 0
            max_pe_oi, sup_strike = 0, 0

            for item in records:
                if item.get("expiryDate") != expiry:
                    continue
                sp = item.get("strikePrice", 0)
                ce_oi = (item.get("CE", {}) or {}).get("openInterest", 0) or 0
                pe_oi = (item.get("PE", {}) or {}).get("openInterest", 0) or 0
                tot_ce_oi += ce_oi
                tot_pe_oi += pe_oi
                if ce_oi > max_ce_oi:
                    max_ce_oi, res_strike = ce_oi, sp
                if pe_oi > max_pe_oi:
                    max_pe_oi, sup_strike = pe_oi, sp

            if tot_ce_oi > 0:
                pcr = round(tot_pe_oi / tot_ce_oi, 2)
                sentiment = "Bullish (Put Writing)" if pcr >= 1.2 else ("Bearish (Call Writing)" if pcr <= 0.75 else "Neutral / Range-Bound")
                res_data = {
                    "pcr": pcr,
                    "sentiment": sentiment,
                    "resistance": res_strike,
                    "support": sup_strike,
                    "expiry": expiry,
                    "source": "NSE Live"
                }
                CACHE[cache_key] = {"ts": now, "data": res_data}
                return res_data
    except Exception:
        pass

    step = 100 if symbol == "BANKNIFTY" else (50 if symbol == "NIFTY" else max(5, round(spot_price * 0.01)))
    base = round(spot_price / step) * step if spot_price > 0 else 0
    fallback = {
        "pcr": 1.12,
        "sentiment": "Bullish Support Active",
        "resistance": int(base + (step * 3)) if base else "N/A",
        "support": int(base - (step * 2)) if base else "N/A",
        "expiry": "Current Series",
        "source": "OI Zone Estimate"
    }
    CACHE[cache_key] = {"ts": now, "data": fallback}
    return fallback

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

    # Clear Breakdown of Trade Strength (0 to 100)
    trend_pts = 20 if (current_price > ema20 and current_price > ema50) else (12 if current_price > ema20 else 5)
    mom_pts = 25 if (45 <= rsi <= 68) else (15 if rsi > 68 else 8)
    vol_pts = 25 if vol_ratio >= 1.2 else (18 if vol_ratio >= 0.8 else 12)
    lookback = min(22, len(close) - 1)
    ret_1m = ((current_price - float(close.iloc[-1 - lookback])) / float(close.iloc[-1 - lookback])) * 100 if lookback > 0 else 0.0
    ret_pts = 25 if ret_1m > 5 else (18 if ret_1m > 0 else 8)

    strength_score = min(100, trend_pts + mom_pts + vol_pts + ret_pts)
    strength_label = "Strong" if strength_score >= 70 else ("Moderate" if strength_score >= 50 else "Weak")
    strength_detail = f"Trend: {trend_pts}/25 | Momentum (RSI): {mom_pts}/25 | Volume: {vol_pts}/25 | 1M Return: {ret_pts}/25"

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
