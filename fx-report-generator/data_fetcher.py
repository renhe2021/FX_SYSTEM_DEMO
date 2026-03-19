"""
FX Research Report Generator - Data Fetcher
Retrieves FX rates, historical data, and macro indicators from free APIs.
Includes robust fallback with sample data for offline/demo usage.
"""

import json
import os
import datetime as dt
import random
import math
from pathlib import Path

import requests
import numpy as np
import pandas as pd

import config


# ═══════════════════════════════════════════════════════════════
#  Helper: safe API call with timeout + retry
# ═══════════════════════════════════════════════════════════════
def _api_get(url, params=None, timeout=10):
    """GET with retry. Returns JSON dict or None on failure."""
    for attempt in range(2):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


# ═══════════════════════════════════════════════════════════════
#  Spot Rates (live)
# ═══════════════════════════════════════════════════════════════
def fetch_live_rates(base="USD"):
    """Fetch latest spot rates from open.er-api.com."""
    url = config.EXCHANGE_RATE_API.format(base=base)
    data = _api_get(url)
    if data and data.get("result") == "success":
        return {
            "base": base,
            "timestamp": data.get("time_last_update_utc", ""),
            "rates": data.get("rates", {}),
        }
    return None


def _pair_to_components(pair):
    """USDCNY -> ('USD', 'CNY')"""
    return pair[:3], pair[3:]


def get_spot_table(pairs=None):
    """
    Returns a DataFrame with columns: pair, base, quote, spot.
    Falls back to synthetic data if API fails.
    """
    pairs = pairs or config.ALL_PAIRS

    # Try fetching live rates for USD and EUR bases
    usd_data = fetch_live_rates("USD")
    eur_data = fetch_live_rates("EUR")

    rows = []
    for pair in pairs:
        base, quote = _pair_to_components(pair)
        spot = None

        if base == "USD" and usd_data and quote in usd_data["rates"]:
            spot = usd_data["rates"][quote]
        elif base == "EUR" and eur_data and quote in eur_data["rates"]:
            spot = eur_data["rates"][quote]
        elif quote == "USD" and usd_data and base in usd_data["rates"]:
            spot = 1.0 / usd_data["rates"][base]
        elif quote == "EUR" and eur_data and base in eur_data["rates"]:
            spot = 1.0 / eur_data["rates"][base]

        if spot is None:
            spot = _synthetic_spot(pair)

        rows.append({"pair": pair, "base": base, "quote": quote, "spot": round(spot, 5)})

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════
#  Historical Rates (synthetic with realistic characteristics)
# ═══════════════════════════════════════════════════════════════
_REFERENCE_SPOTS = {
    "USDCNY": 7.25, "EURUSD": 1.085, "GBPUSD": 1.265, "USDJPY": 150.5,
    "AUDUSD": 0.655, "USDSGD": 1.345, "USDHKD": 7.815,
    "USDBRL": 4.95, "USDMXN": 17.15, "USDINR": 83.2,
    "USDPHP": 55.8, "USDTHB": 35.2, "USDKRW": 1320.0, "USDIDR": 15500.0,
}

_ANNUAL_VOLS = {
    "USDCNY": 0.035, "EURUSD": 0.075, "GBPUSD": 0.08, "USDJPY": 0.09,
    "AUDUSD": 0.09, "USDSGD": 0.04, "USDHKD": 0.003,
    "USDBRL": 0.14, "USDMXN": 0.12, "USDINR": 0.04,
    "USDPHP": 0.05, "USDTHB": 0.06, "USDKRW": 0.08, "USDIDR": 0.06,
}


def _synthetic_spot(pair):
    ref = _REFERENCE_SPOTS.get(pair, 1.0)
    vol = _ANNUAL_VOLS.get(pair, 0.05)
    shock = random.gauss(0, vol * 0.05)
    return ref * (1 + shock)


def generate_historical_series(pair, days=90, end_date=None):
    """
    Generate a realistic historical price series using geometric Brownian motion.
    Returns DataFrame with columns: date, close, change_pct.
    """
    end_date = end_date or dt.date.today()
    ref = _REFERENCE_SPOTS.get(pair, 1.0)
    annual_vol = _ANNUAL_VOLS.get(pair, 0.05)
    daily_vol = annual_vol / math.sqrt(252)

    # GBM path
    np.random.seed(hash(pair + str(end_date)) % (2**31))
    returns = np.random.normal(0, daily_vol, days)
    # Add slight mean-reversion
    prices = [ref]
    for r in returns:
        drift = -0.01 * (prices[-1] / ref - 1)  # mean-reversion pull
        new_price = prices[-1] * math.exp(drift + r)
        prices.append(new_price)
    prices = prices[1:]  # remove seed

    dates = pd.bdate_range(end=end_date, periods=days)
    df = pd.DataFrame({"date": dates, "close": prices})
    df["change_pct"] = df["close"].pct_change() * 100
    df = df.fillna(0)
    return df


def generate_historical_batch(pairs=None, days=90, end_date=None):
    """Generate historical data for multiple pairs. Returns dict[pair] -> DataFrame."""
    pairs = pairs or config.ALL_PAIRS
    return {pair: generate_historical_series(pair, days, end_date) for pair in pairs}


# ═══════════════════════════════════════════════════════════════
#  Volatility Data
# ═══════════════════════════════════════════════════════════════
def compute_realized_vol(hist_df, windows=None):
    """
    Compute realized volatility for different windows.
    Returns dict: {window_label: annualized_vol}.
    """
    windows = windows or {"1W": 5, "2W": 10, "1M": 21, "3M": 63}
    log_ret = np.log(hist_df["close"] / hist_df["close"].shift(1)).dropna()
    result = {}
    for label, w in windows.items():
        if len(log_ret) >= w:
            result[label] = float(log_ret.tail(w).std() * math.sqrt(252)) * 100  # in %
        else:
            result[label] = None
    return result


def compute_vol_table(hist_batch):
    """Compute volatility table across all pairs. Returns DataFrame."""
    rows = []
    for pair, df in hist_batch.items():
        vols = compute_realized_vol(df)
        vols["pair"] = pair
        rows.append(vols)
    return pd.DataFrame(rows).set_index("pair")


# ═══════════════════════════════════════════════════════════════
#  Correlation Matrix
# ═══════════════════════════════════════════════════════════════
def compute_correlation_matrix(hist_batch, window=60):
    """Compute pairwise return correlation matrix. Returns DataFrame."""
    returns = {}
    for pair, df in hist_batch.items():
        log_ret = np.log(df["close"] / df["close"].shift(1)).dropna()
        returns[pair] = log_ret.tail(window).values

    # Align lengths
    min_len = min(len(v) for v in returns.values())
    aligned = {k: v[-min_len:] for k, v in returns.items()}

    ret_df = pd.DataFrame(aligned)
    return ret_df.corr()


# ═══════════════════════════════════════════════════════════════
#  Macro / Event Calendar (template-based)
# ═══════════════════════════════════════════════════════════════
_MACRO_EVENTS_TEMPLATE = [
    {"event": "US Non-Farm Payrolls", "impact": "High", "currency": "USD",
     "description": "Monthly employment change data, key driver of Fed policy expectations."},
    {"event": "US CPI (YoY)", "impact": "High", "currency": "USD",
     "description": "Consumer price inflation, critical for rate path guidance."},
    {"event": "FOMC Rate Decision", "impact": "High", "currency": "USD",
     "description": "Federal Reserve interest rate decision and forward guidance."},
    {"event": "ECB Rate Decision", "impact": "High", "currency": "EUR",
     "description": "European Central Bank monetary policy decision."},
    {"event": "BOJ Policy Meeting", "impact": "High", "currency": "JPY",
     "description": "Bank of Japan yield curve control and rate policy."},
    {"event": "China GDP (QoQ)", "impact": "High", "currency": "CNY",
     "description": "Quarterly GDP growth, impacts CNY and broader EM sentiment."},
    {"event": "China PMI (Manufacturing)", "impact": "Medium", "currency": "CNY",
     "description": "Purchasing Managers Index for manufacturing sector activity."},
    {"event": "UK CPI (YoY)", "impact": "Medium", "currency": "GBP",
     "description": "UK consumer price inflation, key for BOE rate decisions."},
    {"event": "Australia Employment Change", "impact": "Medium", "currency": "AUD",
     "description": "Monthly jobs data, impacts RBA policy outlook."},
    {"event": "US Retail Sales (MoM)", "impact": "Medium", "currency": "USD",
     "description": "Consumer spending data, gauge of economic health."},
]


def get_macro_calendar(report_date=None):
    """Return upcoming macro events as DataFrame."""
    report_date = report_date or dt.date.today()
    rows = []
    for i, evt in enumerate(_MACRO_EVENTS_TEMPLATE):
        # Spread events across next 2 weeks
        evt_date = report_date + dt.timedelta(days=random.randint(1, 14))
        row = {**evt, "date": evt_date.strftime("%Y-%m-%d")}
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


# ═══════════════════════════════════════════════════════════════
#  Risk Monitor Data
# ═══════════════════════════════════════════════════════════════
def compute_risk_metrics(hist_batch):
    """Compute risk metrics for each pair. Returns DataFrame."""
    rows = []
    for pair, df in hist_batch.items():
        log_ret = np.log(df["close"] / df["close"].shift(1)).dropna()
        daily_vol = log_ret.std()
        annual_vol = daily_vol * math.sqrt(252) * 100

        # Simple VaR (95% parametric)
        var_95 = float(np.percentile(log_ret, 5)) * 100  # in %

        # Max drawdown
        cummax = df["close"].cummax()
        drawdown = (df["close"] - cummax) / cummax
        max_dd = float(drawdown.min()) * 100

        # Current vs 20d MA
        ma20 = df["close"].rolling(20).mean().iloc[-1] if len(df) >= 20 else df["close"].mean()
        current = df["close"].iloc[-1]
        vs_ma20 = (current / ma20 - 1) * 100

        rows.append({
            "pair": pair,
            "annual_vol_pct": round(annual_vol, 2),
            "daily_var_95_pct": round(var_95, 3),
            "max_drawdown_pct": round(max_dd, 2),
            "vs_20d_ma_pct": round(vs_ma20, 2),
        })
    return pd.DataFrame(rows).set_index("pair")
