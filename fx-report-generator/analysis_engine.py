"""
FX Research Report Generator - Analysis Engine
Technical analysis, commentary generation, and statistical computations.
"""

import math
import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════
#  Technical Indicators
# ═══════════════════════════════════════════════════════════════
def add_technical_indicators(df):
    """Add MA, RSI, Bollinger Bands to a price DataFrame (must have 'close' column)."""
    df = df.copy()
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()

    # RSI (14-day)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # Bollinger Bands (20-day, 2σ)
    df["bb_mid"] = df["ma20"]
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]

    return df


# ═══════════════════════════════════════════════════════════════
#  Trend Assessment
# ═══════════════════════════════════════════════════════════════
def assess_trend(df):
    """
    Assess current trend based on MA crossover and RSI.
    Returns dict with trend info.
    """
    if len(df) < 20:
        return {"trend": "Insufficient Data", "strength": 0, "signal": "N/A"}

    current = df["close"].iloc[-1]
    ma5 = df["ma5"].iloc[-1] if "ma5" in df else current
    ma20 = df["ma20"].iloc[-1] if "ma20" in df else current
    rsi = df["rsi"].iloc[-1] if "rsi" in df else 50

    # Determine trend direction
    if current > ma20 and ma5 > ma20:
        trend = "Bullish"
    elif current < ma20 and ma5 < ma20:
        trend = "Bearish"
    else:
        trend = "Neutral"

    # Trend strength (0 to 100)
    deviation = abs(current / ma20 - 1) * 100
    strength = min(deviation * 10, 100)

    # RSI signal
    if rsi > 70:
        signal = "Overbought"
    elif rsi < 30:
        signal = "Oversold"
    else:
        signal = "Neutral"

    return {
        "trend": trend,
        "strength": round(strength, 1),
        "rsi": round(rsi, 1) if not math.isnan(rsi) else None,
        "signal": signal,
        "vs_ma20_pct": round((current / ma20 - 1) * 100, 2),
    }


# ═══════════════════════════════════════════════════════════════
#  Support / Resistance Levels
# ═══════════════════════════════════════════════════════════════
def compute_support_resistance(df, window=20):
    """Compute simple support and resistance levels."""
    recent = df["close"].tail(window)
    current = df["close"].iloc[-1]
    high = recent.max()
    low = recent.min()
    mid = (high + low) / 2

    return {
        "current": round(current, 5),
        "resistance_1": round(high, 5),
        "resistance_2": round(high + (high - mid) * 0.618, 5),
        "support_1": round(low, 5),
        "support_2": round(low - (mid - low) * 0.618, 5),
        "pivot": round(mid, 5),
    }


# ═══════════════════════════════════════════════════════════════
#  Period Performance Summary
# ═══════════════════════════════════════════════════════════════
def compute_performance(df):
    """Compute period returns for different timeframes."""
    if len(df) < 2:
        return {}

    current = df["close"].iloc[-1]
    result = {}

    periods = {"1D": 1, "1W": 5, "2W": 10, "1M": 21, "3M": 63}
    for label, lookback in periods.items():
        if len(df) > lookback:
            prev = df["close"].iloc[-(lookback + 1)]
            result[label] = round((current / prev - 1) * 100, 3)
        else:
            result[label] = None

    return result


# ═══════════════════════════════════════════════════════════════
#  Commentary Generator (template-based)
# ═══════════════════════════════════════════════════════════════
_TREND_TEMPLATES = {
    "Bullish": [
        "{pair} continues to trade on a bullish trajectory, currently at {current:.4f}, "
        "sitting {vs_ma20:.2f}% above the 20-day moving average.",
        "The pair has maintained upward momentum with RSI at {rsi:.1f}, "
        "suggesting {signal_text}.",
    ],
    "Bearish": [
        "{pair} remains under pressure, trading at {current:.4f}, "
        "{vs_ma20:.2f}% below the 20-day moving average.",
        "Downward momentum persists with RSI reading {rsi:.1f}, "
        "indicating {signal_text}.",
    ],
    "Neutral": [
        "{pair} is consolidating around {current:.4f}, hovering near the 20-day moving average "
        "({vs_ma20:.2f}% deviation).",
        "The RSI stands at {rsi:.1f}, reflecting a balanced market with {signal_text}.",
    ],
}

_SIGNAL_TEXT = {
    "Overbought": "potential overbought conditions warranting caution",
    "Oversold": "potential oversold conditions that may present opportunities",
    "Neutral": "no extreme readings at current levels",
}


def generate_pair_commentary(pair, trend_info, perf, sr_levels):
    """Generate text commentary for a currency pair."""
    trend = trend_info.get("trend", "Neutral")
    templates = _TREND_TEMPLATES.get(trend, _TREND_TEMPLATES["Neutral"])

    signal_text = _SIGNAL_TEXT.get(trend_info.get("signal", "Neutral"), "mixed signals")
    rsi = trend_info.get("rsi") or 50
    vs_ma20 = trend_info.get("vs_ma20_pct", 0)
    current = sr_levels.get("current", 0)

    lines = []
    for tmpl in templates:
        lines.append(tmpl.format(
            pair=pair, current=current, vs_ma20=abs(vs_ma20),
            rsi=rsi, signal_text=signal_text,
        ))

    # Performance line
    perf_parts = []
    for period in ["1W", "1M", "3M"]:
        val = perf.get(period)
        if val is not None:
            direction = "up" if val > 0 else "down"
            perf_parts.append(f"{period}: {direction} {abs(val):.2f}%")
    if perf_parts:
        lines.append(f"Performance: {', '.join(perf_parts)}.")

    # Support/resistance line
    lines.append(
        f"Key levels — Support: {sr_levels['support_1']:.4f} / {sr_levels['support_2']:.4f}, "
        f"Resistance: {sr_levels['resistance_1']:.4f} / {sr_levels['resistance_2']:.4f}."
    )

    return " ".join(lines)


# ═══════════════════════════════════════════════════════════════
#  Executive Summary Generator
# ═══════════════════════════════════════════════════════════════
def generate_executive_summary(spot_df, hist_batch, vol_table):
    """Generate overall market executive summary text."""
    lines = []

    # USD broad strength indicator
    usd_pairs_up = 0
    usd_pairs_total = 0
    for pair in hist_batch:
        if pair.startswith("USD") and pair != "USDHKD":
            df = hist_batch[pair]
            if len(df) >= 21:
                chg = (df["close"].iloc[-1] / df["close"].iloc[-21] - 1) * 100
                if chg > 0:
                    usd_pairs_up += 1
                usd_pairs_total += 1

    if usd_pairs_total > 0:
        if usd_pairs_up > usd_pairs_total * 0.6:
            usd_tone = "The US dollar has broadly strengthened over the past month"
        elif usd_pairs_up < usd_pairs_total * 0.4:
            usd_tone = "The US dollar has weakened against most counterparts this month"
        else:
            usd_tone = "The US dollar has shown mixed performance across major pairs"
        lines.append(f"{usd_tone}, with the DXY reflecting prevailing rate expectations and macro data flow.")

    # Volatility environment
    avg_vol = vol_table["1M"].mean() if "1M" in vol_table else 5.0
    if avg_vol > 10:
        vol_text = "Volatility remains elevated across major pairs, driven by macro uncertainty."
    elif avg_vol > 6:
        vol_text = "Market volatility is at moderate levels, within seasonal norms."
    else:
        vol_text = "Low volatility environment persists, with realized vols compressed."
    lines.append(vol_text)

    # Top movers
    movers = []
    for pair in hist_batch:
        df = hist_batch[pair]
        if len(df) >= 21:
            chg = (df["close"].iloc[-1] / df["close"].iloc[-21] - 1) * 100
            movers.append((pair, chg))
    movers.sort(key=lambda x: abs(x[1]), reverse=True)

    if movers:
        top = movers[0]
        direction = "gained" if top[1] > 0 else "declined"
        lines.append(
            f"The biggest mover was {top[0]}, which {direction} {abs(top[1]):.2f}% over the past month."
        )

    lines.append(
        "Looking ahead, focus remains on central bank policy signals, inflation data, "
        "and geopolitical developments as key drivers of FX price action."
    )

    return " ".join(lines)
