import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import quote

import requests
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="MarketEye Pro - Live Trailing SL & Demat Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SWING_UNIVERSE = [
    {"symbol": "ADANIENT", "yahoo": "ADANIENT.NS", "name": "Adani Enterprises Ltd", "fno": True},
    {"symbol": "ADANIPORTS", "yahoo": "ADANIPORTS.NS", "name": "Adani Ports & SEZ Ltd", "fno": True},
    {"symbol": "APOLLOHOSP", "yahoo": "APOLLOHOSP.NS", "name": "Apollo Hospitals Enterprise", "fno": True},
    {"symbol": "ASIANPAINT", "yahoo": "ASIANPAINT.NS", "name": "Asian Paints Ltd", "fno": True},
    {"symbol": "AXISBANK", "yahoo": "AXISBANK.NS", "name": "Axis Bank Ltd", "fno": True},
    {"symbol": "BAJAJ-AUTO", "yahoo": "BAJAJ-AUTO.NS", "name": "Bajaj Auto Ltd", "fno": True},
    {"symbol": "BAJAJFINSV", "yahoo": "BAJAJFINSV.NS", "name": "Bajaj Finserv Ltd", "fno": True},
    {"symbol": "BAJFINANCE", "yahoo": "BAJFINANCE.NS", "name": "Bajaj Finance Ltd", "fno": True},
    {"symbol": "BEL", "yahoo": "BEL.NS", "name": "Bharat Electronics Ltd", "fno": True},
    {"symbol": "BHARTIARTL", "yahoo": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "fno": True},
    {"symbol": "BPCL", "yahoo": "BPCL.NS", "name": "Bharat Petroleum Corp", "fno": True},
    {"symbol": "BRITANNIA", "yahoo": "BRITANNIA.NS", "name": "Britannia Industries Ltd", "fno": True},
    {"symbol": "CIPLA", "yahoo": "CIPLA.NS", "name": "Cipla Ltd", "fno": True},
    {"symbol": "COALINDIA", "yahoo": "COALINDIA.NS", "name": "Coal India Ltd", "fno": True},
    {"symbol": "DRREDDY", "yahoo": "DRREDDY.NS", "name": "Dr. Reddy's Laboratories", "fno": True},
    {"symbol": "EICHERMOT", "yahoo": "EICHERMOT.NS", "name": "Eicher Motors Ltd", "fno": True},
    {"symbol": "GRASIM", "yahoo": "GRASIM.NS", "name": "Grasim Industries Ltd", "fno": True},
    {"symbol": "HAL", "yahoo": "HAL.NS", "name": "Hindustan Aeronautics Ltd", "fno": True},
    {"symbol": "HCLTECH", "yahoo": "HCLTECH.NS", "name": "HCL Technologies Ltd", "fno": True},
    {"symbol": "HDFCBANK", "yahoo": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "fno": True},
    {"symbol": "HDFCLIFE", "yahoo": "HDFCLIFE.NS", "name": "HDFC Life Insurance", "fno": True},
    {"symbol": "HEROMOTOCO", "yahoo": "HEROMOTOCO.NS", "name": "Hero MotoCorp Ltd", "fno": True},
    {"symbol": "HINDALCO", "yahoo": "HINDALCO.NS", "name": "Hindalco Industries Ltd", "fno": True},
    {"symbol": "HINDUNILVR", "yahoo": "HINDUNILVR.NS", "name": "Hindustan Unilever Ltd", "fno": True},
    {"symbol": "ICICIBANK", "yahoo": "ICICIBANK.NS", "name": "ICICI Bank Ltd", "fno": True},
    {"symbol": "INDUSINDBK", "yahoo": "INDUSINDBK.NS", "name": "IndusInd Bank Ltd", "fno": True},
    {"symbol": "INFY", "yahoo": "INFY.NS", "name": "Infosys Ltd", "fno": True},
    {"symbol": "IRCTC", "yahoo": "IRCTC.NS", "name": "IRCTC Ltd", "fno": True},
    {"symbol": "ITC", "yahoo": "ITC.NS", "name": "ITC Ltd", "fno": True},
    {"symbol": "JSWSTEEL", "yahoo": "JSWSTEEL.NS", "name": "JSW Steel Ltd", "fno": True},
    {"symbol": "KOTAKBANK", "yahoo": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank Ltd", "fno": True},
    {"symbol": "LT", "yahoo": "LT.NS", "name": "Larsen & Toubro Ltd", "fno": True},
    {"symbol": "M&M", "yahoo": "M&M.NS", "name": "Mahindra & Mahindra Ltd", "fno": True},
    {"symbol": "MARUTI", "yahoo": "MARUTI.NS", "name": "Maruti Suzuki India Ltd", "fno": True},
    {"symbol": "NESTLEIND", "yahoo": "NESTLEIND.NS", "name": "Nestle India Ltd", "fno": True},
    {"symbol": "NTPC", "yahoo": "NTPC.NS", "name": "NTPC Ltd", "fno": True},
    {"symbol": "ONGC", "yahoo": "ONGC.NS", "name": "Oil & Natural Gas Corp", "fno": True},
    {"symbol": "POWERGRID", "yahoo": "POWERGRID.NS", "name": "Power Grid Corp of India", "fno": True},
    {"symbol": "RELIANCE", "yahoo": "RELIANCE.NS", "name": "Reliance Industries Ltd", "fno": True},
    {"symbol": "SBILIFE", "yahoo": "SBILIFE.NS", "name": "SBI Life Insurance Co", "fno": True},
    {"symbol": "SBIN", "yahoo": "SBIN.NS", "name": "State Bank of India", "fno": True},
    {"symbol": "SUNPHARMA", "yahoo": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Ind", "fno": True},
    {"symbol": "SUZLON", "yahoo": "SUZLON.NS", "name": "Suzlon Energy Ltd", "fno": False},
    {"symbol": "TATACONSUM", "yahoo": "TATACONSUM.NS", "name": "Tata Consumer Products", "fno": True},
    {"symbol": "TATAMOTORS", "yahoo": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "fno": True},
    {"symbol": "TATASTEEL", "yahoo": "TATASTEEL.NS", "name": "Tata Steel Ltd", "fno": True},
    {"symbol": "TCS", "yahoo": "TCS.NS", "name": "Tata Consultancy Services", "fno": True},
    {"symbol": "TECHM", "yahoo": "TECHM.NS", "name": "Tech Mahindra Ltd", "fno": True},
    {"symbol": "TITAN", "yahoo": "TITAN.NS", "name": "Titan Company Ltd", "fno": True},
    {"symbol": "TRENT", "yahoo": "TRENT.NS", "name": "Trent Ltd", "fno": True},
    {"symbol": "ULTRACEMCO", "yahoo": "ULTRACEMCO.NS", "name": "UltraTech Cement Ltd", "fno": True},
    {"symbol": "WIPRO", "yahoo": "WIPRO.NS", "name": "Wipro Ltd", "fno": True},
    {"symbol": "ZOMATO", "yahoo": "ZOMATO.NS", "name": "Zomato Ltd", "fno": True},
]

DEFAULT_SWING_SYMBOLS = {
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "BHARTIARTL", "SBIN", "ICICIBANK",
    "TATAMOTORS", "TATASTEEL", "ZOMATO", "HAL", "BEL", "ITC", "AXISBANK",
    "WIPRO", "LT", "SUNPHARMA", "MARUTI", "BAJFINANCE", "TITAN"
}

COMMODITY_UNIVERSE = [
    {"symbol": "GOLD", "yahoo": "GC=F", "name": "Gold Futures (COMEX)", "currency": "$"},
    {"symbol": "SILVER", "yahoo": "SI=F", "name": "Silver Futures (COMEX)", "currency": "$"},
    {"symbol": "CRUDEOIL", "yahoo": "CL=F", "name": "WTI Crude Oil Futures", "currency": "$"},
    {"symbol": "NATURALGAS", "yahoo": "NG=F", "name": "Natural Gas Futures", "currency": "$"},
    {"symbol": "COPPER", "yahoo": "HG=F", "name": "Copper Futures", "currency": "$"},
]

FOREX_UNIVERSE = [
    {"symbol": "USDINR", "yahoo": "USDINR=X", "name": "USD / INR (Spot)", "currency": "₹"},
    {"symbol": "EURINR", "yahoo": "EURINR=X", "name": "EUR / INR (Spot)", "currency": "₹"},
    {"symbol": "GBPINR", "yahoo": "GBPINR=X", "name": "GBP / INR (Spot)", "currency": "₹"},
    {"symbol": "EURUSD", "yahoo": "EURUSD=X", "name": "EUR / USD (Major)", "currency": "$"},
    {"symbol": "GBPUSD", "yahoo": "GBPUSD=X", "name": "GBP / USD (Major)", "currency": "$"},
    {"symbol": "USDJPY", "yahoo": "USDJPY=X", "name": "USD / JPY (Major)", "currency": "¥"},
]

ALL_ITEMS = {item["symbol"]: item for item in (SWING_UNIVERSE + COMMODITY_UNIVERSE + FOREX_UNIVERSE)}

SEGMENT_STORE: Dict[str, List[Dict[str, Any]]] = {"swing": [], "commodity": [], "forex": []}
LIVE_PRICES: Dict[str, Dict[str, Any]] = {}
INDICES_STORE: Dict[str, Any] = {}
HISTORY_CACHE: Dict[str, Any] = {}
ORDER_BOOK: List[Dict[str, Any]] = []

BROKER_CONFIG = {
    "default_broker": "UPSTOX",
    "upstox_access_token": "",
    "zerodha_api_key": "",
    "zerodha_access_token": "",
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
})


def get_ist_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def is_ist_market_open() -> bool:
    now = get_ist_now()
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= mins <= (15 * 60 + 30)


def calc_ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    ema = [values[0]]
    for price in values[1:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def calc_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)


def fetch_yahoo_chart(ticker: str, range_str: str = "2mo", interval: str = "1d", min_points: int = 1):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}?range={range_str}&interval={interval}"
    try:
        resp = SESSION.get(url, timeout=4)
        if resp.status_code != 200:
            return None
        payload = resp.json()
        result = (payload.get("chart") or {}).get("result") or []
        if not result:
            return None
        r0 = result[0]
        meta = r0.get("meta") or {}
        q = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
        opens = q.get("open") or []
        highs = q.get("high") or []
        lows = q.get("low") or []
        closes = q.get("close") or []
        candles, valid_closes = [], []
        decimals = 4 if "=X" in ticker and "INR" not in ticker else 2
        for o, h, l, c in zip(opens, highs, lows, closes):
            if c is None or o is None or h is None or l is None:
                continue
            if any(math.isnan(x) for x in (o, h, l, c)):
                continue
            candles.append({
                "open": round(float(o), decimals),
                "high": round(float(h), decimals),
                "low": round(float(l), decimals),
                "close": round(float(c), decimals),
            })
            valid_closes.append(float(c))
        if len(valid_closes) < min_points:
            return None
        return {"candles": candles, "closes": valid_closes, "meta": meta}
    except Exception:
        return None


def analyze_instrument(symbol: str, segment: str = "swing", force_fresh: bool = False):
    sym = symbol.strip().upper()
    seg = segment.strip().lower()
    meta = ALL_ITEMS.get(sym)
    if meta:
        yahoo_ticker = meta["yahoo"]
        disp_name = meta["name"]
        currency = meta.get("currency", "₹")
        is_fno = meta.get("fno", False)
    else:
        yahoo_ticker = sym if ("=" in sym or "." in sym) else f"{sym}.NS"
        disp_name = sym
        currency = "$" if ("=F" in yahoo_ticker or "=X" in yahoo_ticker) else "₹"
        is_fno = False

    is_weekly = (seg == "swing")
    hist_key = f"hist_{seg}_{sym}"
    hist_entry = HISTORY_CACHE.get(hist_key)

    if not hist_entry or (time.time() - hist_entry["ts"]) > 60 or force_fresh:
        hist = fetch_yahoo_chart(
            yahoo_ticker,
            range_str=("1y" if is_weekly else "2mo"),
            interval=("1wk" if is_weekly else "1d"),
            min_points=20,
        )
        if hist:
            HISTORY_CACHE[hist_key] = {"ts": time.time(), "data": hist}
            hist_entry = HISTORY_CACHE[hist_key]

    if not hist_entry:
        return None

    hist = hist_entry["data"]
    y_meta = hist.get("meta") or {}
    closes = hist["closes"]
    candles = hist["candles"]
    decimals = 4 if ("=X" in yahoo_ticker and "INR" not in yahoo_ticker) else 2

    tick_hist = fetch_yahoo_chart(yahoo_ticker, range_str="1d", interval="1m", min_points=1)
    if tick_hist and tick_hist.get("meta", {}).get("regularMarketPrice") is not None:
        reg_price = tick_hist["meta"]["regularMarketPrice"]
        prev_close = tick_hist["meta"].get("chartPreviousClose") or (closes[-2] if len(closes) >= 2 else reg_price)
    else:
        reg_price = y_meta.get("regularMarketPrice") if y_meta.get("regularMarketPrice") is not None else closes[-1]
        prev_close = closes[-2] if len(closes) >= 2 else reg_price

    price = round(float(reg_price), decimals)
    prev_val = float(prev_close) if prev_close else price
    change_pct = round(((price - prev_val) / prev_val) * 100.0, 2) if prev_val else 0.0

    last_candle = candles[-1]
    fri_high = last_candle["high"]
    fri_low = last_candle["low"]

    ema20 = round(calc_ema(closes, 20)[-1], decimals)
    ema50 = round(calc_ema(closes, 50)[-1], decimals)
    rsi = calc_rsi(closes, 14)

    if is_weekly:
        buy_entry = round(max(price, fri_high * 0.998), decimals)
        sell_entry = round(min(price, fri_low * 1.002), decimals)
    else:
        buy_entry = price
        sell_entry = price

    if (price >= ema20 and rsi < 70) or rsi <= 36.0:
        side = "BUY"
        signal = "MONDAY BUY" if is_weekly else "DAILY BUY"
        entry_price = buy_entry
    else:
        side = "SELL"
        signal = "MONDAY SELL" if is_weekly else "DAILY SELL"
        entry_price = sell_entry

    LIVE_PRICES[sym] = {
        "price": price,
        "change_pct": change_pct,
        "entry_price": entry_price,
        "side": side,
        "signal": signal,
        "decimals": decimals,
    }

    return {
        "symbol": sym,
        "name": disp_name,
        "segment": seg,
        "currency": currency,
        "decimals": decimals,
        "price": price,
        "entry_price": entry_price,
        "change_pct": change_pct,
        "side": side,
        "signal": signal,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "is_fno": is_fno,
    }


def refresh_indices_store():
    tasks = [
        ("^NSEI", "NIFTY 50"),
        ("^NSEBANK", "BANK NIFTY"),
        ("DX-Y.NYB", "US DOLLAR (DXY)"),
        ("GC=F", "GOLD ($)"),
    ]
    def _one(t):
        hist = fetch_yahoo_chart(t[0], range_str="5d", interval="1d", min_points=1)
        if not hist:
            return {"label": t[1], "price": None, "change_pct": 0.0}
        meta = hist.get("meta") or {}
        closes = hist["closes"]
        reg = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        p = round(float(reg), 2) if reg is not None else round(closes[-1], 2)
        pr = float(prev) if (prev is not None and float(prev) > 0) else (closes[-2] if len(closes) >= 2 else p)
        chg = round(((p - pr) / pr) * 100.0, 2) if pr else 0.0
        return {"label": t[1], "price": p, "change_pct": chg}

    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(_one, tasks))
    INDICES_STORE["data"] = {"nifty": res[0], "banknifty": res[1], "dxy": res[2], "gold": res[3]}


def refresh_segment_data(seg: str):
    if seg == "commodity":
        universe = COMMODITY_UNIVERSE
    elif seg == "forex":
        universe = FOREX_UNIVERSE
    else:
        seg = "swing"
        universe = [x for x in SWING_UNIVERSE if x["symbol"] in DEFAULT_SWING_SYMBOLS]

    with ThreadPoolExecutor(max_workers=12) as ex:
        raw = list(ex.map(lambda item: analyze_instrument(item["symbol"], seg), universe))
    items = [r for r in raw if r is not None]
    if items:
        SEGMENT_STORE[seg] = items
    return SEGMENT_STORE[seg]


def background_live_worker():
    while True:
        try:
            refresh_indices_store()
            for seg in ("swing", "commodity", "forex"):
                refresh_segment_data(seg)
            open_syms = {(o["symbol"], o["segment"].lower()) for o in ORDER_BOOK if o["status"] == "OPEN"}
            for sym, seg in open_syms:
                analyze_instrument(sym, seg)
        except Exception:
            pass
        time.sleep(2.0)


@app.on_event("startup")
def start_background_tasks():
    t = threading.Thread(target=background_live_worker, daemon=True)
    t.start()


def send_demat_order(
    symbol: str,
    side: str,
    qty: int,
    segment: str,
    limit_price: Optional[float] = None,
    tsl_enabled: bool = False,
    tsl_pct: float = 1.0,
) -> Dict[str, Any]:
    broker = BROKER_CONFIG.get("default_broker", "UPSTOX").upper()
    is_limit = limit_price is not None and limit_price > 0

    if broker == "UPSTOX":
        token = BROKER_CONFIG.get("upstox_access_token", "").strip()
        if not token:
            return {"executed": False, "message": "Upstox Access Token सेट केलेला नाही! वर 'Demat Account Link' मध्ये Token टाका."}
        url = "https://api.upstox.com/v2/order/place"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
        payload = {
            "quantity": max(1, qty),
            "product": "D" if segment == "swing" else "I",
            "validity": "DAY",
            "price": round(limit_price, 2) if is_limit else 0,
            "tag": "MarketEyePro",
            "instrument_token": f"NSE_EQ|{symbol}",
            "order_type": "LIMIT" if is_limit else "MARKET",
            "transaction_type": side,
            "disclosed_quantity": 0,
            "trigger_price": 0,
            "is_amo": not is_ist_market_open(),
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=6)
            data = r.json()
            if r.status_code == 200 and data.get("status") == "success":
                oid = (data.get("data") or {}).get("order_id", "UPX-LIVE")
                tsl_note = f" (Trailing SL {tsl_pct}% Active)" if tsl_enabled else ""
                return {"executed": True, "broker": "UPSTOX DEMAT", "order_id": oid, "message": f"Upstox Demat वर Order लागली! ID: {oid}{tsl_note}"}
            return {"executed": False, "message": f"Upstox Error: {data.get('errors') or data}"}
        except Exception as e:
            return {"executed": False, "message": f"Upstox Network Error: {e}"}

    if broker == "ZERODHA":
        api_key = BROKER_CONFIG.get("zerodha_api_key", "").strip()
        token = BROKER_CONFIG.get("zerodha_access_token", "").strip()
        if not api_key or not token:
            return {"executed": False, "message": "Zerodha API Key किंवा Access Token सेट केलेला नाही!"}
        url = "https://api.kite.trade/orders/regular"
        headers = {"X-Kite-Version": "3", "Authorization": f"token {api_key}:{token}"}
        payload = {
            "tradingsymbol": symbol,
            "exchange": "NSE" if segment == "swing" else ("MCX" if segment == "commodity" else "CDS"),
            "transaction_type": side,
            "order_type": "LIMIT" if is_limit else "MARKET",
            "price": round(limit_price, 2) if is_limit else 0,
            "quantity": max(1, qty),
            "product": "CNC" if segment == "swing" else "MIS",
            "validity": "DAY",
            "tag": "MarketEyePro",
        }
        try:
            r = requests.post(url, data=payload, headers=headers, timeout=6)
            data = r.json()
            if r.status_code == 200 and data.get("status") == "success":
                oid = (data.get("data") or {}).get("order_id", "KITE-LIVE")
                tsl_note = f" (Trailing SL {tsl_pct}% Active)" if tsl_enabled else ""
                return {"executed": True, "broker": "ZERODHA DEMAT", "order_id": oid, "message": f"Zerodha Demat वर Order लागली! ID: {oid}{tsl_note}"}
            return {"executed": False, "message": f"Zerodha Error: {data.get('message') or data}"}
        except Exception as e:
            return {"executed": False, "message": f"Zerodha Network Error: {e}"}

    return {"executed": False, "message": "Demat Broker निवडलेला नाही."}


def compute_live_orders() -> List[Dict[str, Any]]:
    """Updates real-time MTM P&L, optional Trailing Stop-Loss, and SL/Target hit status."""
    enriched = []
    for o in ORDER_BOOK:
        sym = o["symbol"]
        tick = LIVE_PRICES.get(sym)
        ltp = tick["price"] if tick else o["entry"]
        dec = o.get("decimals", 2)
        qty = o["qty"]
        entry = o["entry"]
        tsl_enabled = bool(o.get("tsl_enabled", False))
        tsl_pct = float(o.get("tsl_pct", 1.0))

        if o["side"] == "BUY":
            if o["status"] == "OPEN" and tsl_enabled:
                peak = max(float(o.get("peak_price", entry)), ltp)
                o["peak_price"] = peak
                trailed_sl = round(peak * (1.0 - tsl_pct / 100.0), dec)
                if trailed_sl > o["stop_loss"]:
                    o["stop_loss"] = trailed_sl
                    o["tsl_moved"] = True

            pnl = round((ltp - entry) * qty, 2)
            if o["status"] == "OPEN":
                if ltp <= o["stop_loss"]:
                    o["status"] = "TSL HIT" if o.get("tsl_moved") else "SL HIT"
                elif ltp >= o["target"]:
                    o["status"] = "TARGET HIT"
        else:
            if o["status"] == "OPEN" and tsl_enabled:
                trough = min(float(o.get("peak_price", entry)), ltp)
                o["peak_price"] = trough
                trailed_sl = round(trough * (1.0 + tsl_pct / 100.0), dec)
                if trailed_sl < o["stop_loss"]:
                    o["stop_loss"] = trailed_sl
                    o["tsl_moved"] = True

            pnl = round((entry - ltp) * qty, 2)
            if o["status"] == "OPEN":
                if ltp >= o["stop_loss"]:
                    o["status"] = "TSL HIT" if o.get("tsl_moved") else "SL HIT"
                elif ltp <= o["target"]:
                    o["status"] = "TARGET HIT"

        pnl_pct = round(((ltp - entry) / entry) * 100.0 * (1 if o["side"] == "BUY" else -1), 2) if entry else 0.0
        item_copy = dict(o)
        item_copy["ltp"] = round(ltp, dec)
        item_copy["pnl"] = pnl
        item_copy["pnl_pct"] = pnl_pct
        enriched.append(item_copy)
    return enriched


@app.get("/")
def serve_home():
    return FileResponse("index.html")


@app.get("/symbols")
def get_all_symbols():
    return {
        "swing": sorted([{"symbol": x["symbol"], "name": x["name"]} for x in SWING_UNIVERSE], key=lambda k: k["symbol"]),
        "commodity": sorted([{"symbol": x["symbol"], "name": x["name"]} for x in COMMODITY_UNIVERSE], key=lambda k: k["symbol"]),
        "forex": sorted([{"symbol": x["symbol"], "name": x["name"]} for x in FOREX_UNIVERSE], key=lambda k: k["symbol"]),
    }


@app.get("/indices")
def get_indices():
    if not INDICES_STORE.get("data"):
        refresh_indices_store()
    return INDICES_STORE.get("data", {})


@app.get("/signals")
def get_signals(segment: str = Query(default="swing")):
    seg = segment.strip().lower()
    if seg not in ("swing", "commodity", "forex"):
        seg = "swing"
    if SEGMENT_STORE[seg]:
        return {"segment": seg, "items": SEGMENT_STORE[seg], "count": len(SEGMENT_STORE[seg])}
    items = refresh_segment_data(seg)
    return {"segment": seg, "items": items, "count": len(items)}


@app.get("/live-ticks")
def get_live_ticks():
    return {
        "ticks": LIVE_PRICES,
        "indices": INDICES_STORE.get("data", {}),
        "orders": compute_live_orders(),
        "server_time": get_ist_now().strftime("%H:%M:%S.%f")[:-4],
    }


@app.get("/search/{symbol}")
def search_instrument(symbol: str, segment: str = Query(default="swing")):
    item = analyze_instrument(symbol, segment=segment, force_fresh=True)
    if not item:
        return JSONResponse(status_code=404, content={"error": f"Symbol '{symbol}' सापडले नाही."})
    return {"item": item}


@app.get("/orders")
def get_orders():
    return {"orders": compute_live_orders()}


@app.post("/order/place")
def place_custom_order(payload: Dict[str, Any] = Body(...)):
    sym = str(payload.get("symbol", "")).upper()
    seg = str(payload.get("segment", "swing")).lower()
    trade_mode = str(payload.get("trade_mode", "PAPER")).upper()
    budget = float(payload.get("budget", 10000.0))
    sl_pct = float(payload.get("sl_pct", 2.0))
    tgt_pct = float(payload.get("target_pct", 5.0))
    tsl_enabled = bool(payload.get("tsl_enabled", False))
    tsl_pct = float(payload.get("tsl_pct", 1.0))
    manual_entry = payload.get("manual_entry")

    item = analyze_instrument(sym, segment=seg)
    if not item:
        return JSONResponse(status_code=404, content={"error": "Stock सापडले नाही."})

    custom_px = float(manual_entry) if (manual_entry and float(manual_entry) > 0) else None
    entry = custom_px if custom_px else item["entry_price"]
    decimals = item["decimals"]
    side = item["side"]
    qty = max(1, int(math.floor(budget / entry))) if entry > 0 else 1
    invested = round(qty * entry, 2)

    if side == "BUY":
        stop_loss = round(entry * (1.0 - sl_pct / 100.0), decimals)
        target = round(entry * (1.0 + tgt_pct / 100.0), decimals)
    else:
        stop_loss = round(entry * (1.0 + sl_pct / 100.0), decimals)
        target = round(max(0.0001, entry * (1.0 - tgt_pct / 100.0)), decimals)

    if trade_mode == "ALGO_DEMAT":
        res = send_demat_order(sym, side, qty, seg, limit_price=None, tsl_enabled=tsl_enabled, tsl_pct=tsl_pct)
        if not res.get("executed"):
            return JSONResponse(status_code=400, content={"error": res.get("message", "Algo Demat order failed")})
        oid = res["order_id"]
        mode_label = f"ALGO ({res['broker']})"
        msg = res["message"]
    elif trade_mode == "MANUAL_DEMAT":
        res = send_demat_order(sym, side, qty, seg, limit_price=custom_px, tsl_enabled=tsl_enabled, tsl_pct=tsl_pct)
        if not res.get("executed"):
            return JSONResponse(status_code=400, content={"error": res.get("message", "Manual Demat order failed")})
        oid = res["order_id"]
        mode_label = f"MANUAL ({res['broker']})"
        msg = res["message"]
    else:
        oid = f"PPR-{int(time.time() * 1000) % 1000000}"
        mode_label = "PAPER TRADE"
        tsl_txt = f" | Trailing SL: {tsl_pct}%" if tsl_enabled else ""
        msg = f"Paper Trade {sym} ({qty} Qty @ {item['currency']}{entry}){tsl_txt} सुरू झाला!"

    order = {
        "id": oid,
        "mode": mode_label,
        "segment": seg.upper(),
        "symbol": sym,
        "side": side,
        "qty": qty,
        "invested": invested,
        "entry": round(entry, decimals),
        "peak_price": round(entry, decimals),
        "stop_loss": stop_loss,
        "sl_pct": sl_pct,
        "tsl_enabled": tsl_enabled,
        "tsl_pct": tsl_pct,
        "tsl_moved": False,
        "target": target,
        "tgt_pct": tgt_pct,
        "currency": item["currency"],
        "decimals": decimals,
        "status": "OPEN",
        "time": get_ist_now().strftime("%d %b, %H:%M:%S"),
    }
    ORDER_BOOK.insert(0, order)
    return {"status": "ok", "message": msg, "orders": compute_live_orders()}


@app.post("/broker-config")
def save_broker_config(payload: Dict[str, Any] = Body(...)):
    for k in ("default_broker", "upstox_access_token", "zerodha_api_key", "zerodha_access_token"):
        if k in payload:
            BROKER_CONFIG[k] = str(payload[k]).strip()
    return {
        "status": "ok",
        "upstox_connected": bool(BROKER_CONFIG["upstox_access_token"]),
        "zerodha_connected": bool(BROKER_CONFIG["zerodha_api_key"] and BROKER_CONFIG["zerodha_access_token"]),
    }


@app.delete("/orders/{order_id}")
def close_order(order_id: str):
    for o in ORDER_BOOK:
        if o["id"] == order_id:
            o["status"] = "CLOSED"
    return {"status": "ok", "orders": compute_live_orders()}