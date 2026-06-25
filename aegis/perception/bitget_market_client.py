"""Real Bitget market-data client, used as the live data source behind
AgentHubClient when BITGET_API_KEY/SECRET_KEY/PASSPHRASE are configured.

This does not call Bitget's own "Agent Hub" skill endpoints (those are a
CLI/MCP-wrapped layer, not a plain REST API) -- instead it pulls the same
underlying signal categories (trend, volatility, sentiment via funding
rate, liquidity) directly from Bitget's public/authenticated REST API and
maps them onto the same 5-skill schema the rest of the pipeline expects.
If Bitget is unreachable or credentials are missing, callers should fall
back to the deterministic mock -- this never raises past fetch_features().
"""

import base64
import hashlib
import hmac
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BITGET_BASE_URL = "https://api.bitget.com"
BITGET_API_KEY = os.getenv("BITGET_API_KEY", "")
BITGET_SECRET_KEY = os.getenv("BITGET_SECRET_KEY", "")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE", "")


def is_configured() -> bool:
    return bool(BITGET_API_KEY and BITGET_SECRET_KEY and BITGET_PASSPHRASE)


_session = requests.Session()
_session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=0, status_forcelist=[429, 500, 502, 503, 504])),
)


def _sign(timestamp: str, method: str, path: str, body: str = "") -> str:
    prehash = timestamp + method + path + body
    return base64.b64encode(
        hmac.new(BITGET_SECRET_KEY.encode(), prehash.encode(), hashlib.sha256).digest()
    ).decode()


def _signed_get(path: str, params: dict | None = None) -> dict:
    timestamp = str(int(time.time() * 1000))
    query = ""
    if params:
        query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    sign = _sign(timestamp, "GET", path + query)
    headers = {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json",
    }
    resp = _session.get(BITGET_BASE_URL + path, params=params, headers=headers, timeout=4)
    resp.raise_for_status()
    return resp.json()


def fetch_features(symbol: str) -> dict:
    """Returns the same 6 raw fields the mock produces, derived from real
    Bitget ticker + funding-rate data."""
    ticker = _signed_get("/api/v2/spot/market/tickers", {"symbol": symbol})["data"][0]
    funding = _signed_get(
        "/api/v2/mix/market/current-fund-rate", {"symbol": symbol, "productType": "USDT-FUTURES"}
    )["data"][0]

    last_price = float(ticker["lastPr"])
    high24h = float(ticker["high24h"])
    low24h = float(ticker["low24h"])
    change24h = float(ticker["change24h"])
    quote_volume = float(ticker["quoteVolume"])
    funding_rate = float(funding["fundingRate"])

    # trend_strength: 24h % change, clamped to [-1, 1] (a 10%+ move maxes it out)
    trend_strength = max(-1.0, min(1.0, change24h / 0.10))

    # volatility: 24h range as a fraction of price, scaled so a 5% range -> ~1.0
    volatility = max(0.0, min(1.0, (high24h - low24h) / last_price / 0.05))

    # sentiment_score: funding rate sign/magnitude (rates run roughly -0.3% to 0.3%)
    sentiment_score = max(-1.0, min(1.0, funding_rate / 0.003))

    # macro_risk_flag: extreme volatility or extreme funding as a crude macro-stress proxy
    macro_risk_flag = volatility > 0.8 or abs(sentiment_score) > 0.8

    # news_shock_flag: an outsized single-day move with no real news feed wired up yet
    news_shock_flag = abs(change24h) > 0.08

    # liquidity_score: normalize 24h quote volume against a reference scale (BTCUSDT-sized)
    liquidity_score = max(0.1, min(1.0, quote_volume / 500_000_000))

    return {
        "trend_strength": round(trend_strength, 3),
        "volatility": round(volatility, 3),
        "sentiment_score": round(sentiment_score, 3),
        "macro_risk_flag": macro_risk_flag,
        "news_shock_flag": news_shock_flag,
        "liquidity_score": round(liquidity_score, 3),
    }
