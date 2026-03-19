"""
FX Research Report Generator - Chart Builder
Creates matplotlib charts for embedding into PDF reports.
"""

import io
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch

import config

# Apply style
try:
    plt.style.use(config.CHART_STYLE)
except Exception:
    plt.style.use("ggplot")

# Font config for clean rendering
plt.rcParams.update({
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.dpi": config.CHART_DPI,
    "savefig.dpi": config.CHART_DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
})


def _to_bytes(fig):
    """Save figure to bytes buffer."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════
#  Price Chart with MA + Bollinger Bands
# ═══════════════════════════════════════════════════════════════
def chart_price_with_indicators(df, pair, figsize=None):
    """Price line chart with MA5, MA20, Bollinger Bands."""
    figsize = figsize or config.CHART_FIGSIZE_FULL
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(figsize[0], figsize[1] + 1.2),
                                    gridspec_kw={"height_ratios": [3, 1]}, sharex=True)

    dates = df["date"]

    # Price + MAs
    ax1.plot(dates, df["close"], color=config.COLORS["primary"], linewidth=1.2, label="Close")
    if "ma5" in df:
        ax1.plot(dates, df["ma5"], color="#ff7043", linewidth=0.8, alpha=0.8, label="MA5")
    if "ma20" in df:
        ax1.plot(dates, df["ma20"], color="#42a5f5", linewidth=0.8, alpha=0.8, label="MA20")

    # Bollinger Bands
    if "bb_upper" in df and "bb_lower" in df:
        ax1.fill_between(dates, df["bb_lower"], df["bb_upper"],
                         alpha=0.08, color=config.COLORS["secondary"])
        ax1.plot(dates, df["bb_upper"], color=config.COLORS["border"], linewidth=0.5, linestyle="--")
        ax1.plot(dates, df["bb_lower"], color=config.COLORS["border"], linewidth=0.5, linestyle="--")

    ax1.set_title(f"{pair} — Price & Technical Indicators", fontweight="bold", pad=8)
    ax1.legend(loc="upper left", framealpha=0.8, edgecolor="none")
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Price")

    # RSI subplot
    if "rsi" in df:
        ax2.plot(dates, df["rsi"], color=config.COLORS["accent"], linewidth=1.0)
        ax2.axhline(70, color=config.COLORS["negative"], linewidth=0.6, linestyle="--", alpha=0.6)
        ax2.axhline(30, color=config.COLORS["positive"], linewidth=0.6, linestyle="--", alpha=0.6)
        ax2.fill_between(dates, 30, 70, alpha=0.05, color="gray")
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI")
    ax2.grid(True, alpha=0.3)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout(h_pad=0.5)

    return _to_bytes(fig)


# ═══════════════════════════════════════════════════════════════
#  Mini Sparkline Chart (for tables)
# ═══════════════════════════════════════════════════════════════
def chart_sparkline(df, pair, figsize=(2.0, 0.6)):
    """Tiny sparkline chart for embedding in tables."""
    fig, ax = plt.subplots(figsize=figsize)
    prices = df["close"].values
    color = config.COLORS["positive"] if prices[-1] >= prices[0] else config.COLORS["negative"]
    ax.plot(prices, color=color, linewidth=1.0)
    ax.fill_between(range(len(prices)), prices, alpha=0.1, color=color)
    ax.axis("off")
    fig.tight_layout(pad=0)
    return _to_bytes(fig)


# ═══════════════════════════════════════════════════════════════
#  Volatility Bar Chart
# ═══════════════════════════════════════════════════════════════
def chart_volatility_bars(vol_table, figsize=None):
    """Grouped bar chart of realized vols across pairs and windows."""
    figsize = figsize or config.CHART_FIGSIZE_FULL
    fig, ax = plt.subplots(figsize=figsize)

    pairs = vol_table.index.tolist()
    windows = [c for c in vol_table.columns if c in ["1W", "2W", "1M", "3M"]]
    x = np.arange(len(pairs))
    width = 0.8 / len(windows)
    colors_list = ["#1a237e", "#1976d2", "#42a5f5", "#90caf9"]

    for i, w in enumerate(windows):
        vals = vol_table[w].fillna(0).values
        ax.bar(x + i * width, vals, width, label=w, color=colors_list[i % len(colors_list)], alpha=0.85)

    ax.set_xticks(x + width * (len(windows) - 1) / 2)
    ax.set_xticklabels(pairs, rotation=45, ha="right")
    ax.set_ylabel("Annualized Vol (%)")
    ax.set_title("Realized Volatility by Currency Pair", fontweight="bold", pad=8)
    ax.legend(framealpha=0.8, edgecolor="none")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    return _to_bytes(fig)


# ═══════════════════════════════════════════════════════════════
#  Correlation Heatmap
# ═══════════════════════════════════════════════════════════════
def chart_correlation_heatmap(corr_matrix, figsize=None):
    """Correlation heatmap for currency pairs."""
    figsize = figsize or config.CHART_FIGSIZE_SQUARE
    fig, ax = plt.subplots(figsize=figsize)

    n = len(corr_matrix)
    im = ax.imshow(corr_matrix.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="equal")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    labels = [p.replace("USD", "") for p in corr_matrix.columns]
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=6)
    ax.set_yticklabels(labels, fontsize=6)

    # Annotate cells
    for i in range(n):
        for j in range(n):
            val = corr_matrix.values[i, j]
            color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=5, color=color)

    ax.set_title("Return Correlation Matrix (60D)", fontweight="bold", pad=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Correlation")
    fig.tight_layout()

    return _to_bytes(fig)


# ═══════════════════════════════════════════════════════════════
#  Performance Bar Chart (horizontal)
# ═══════════════════════════════════════════════════════════════
def chart_performance_bars(perf_data, period="1M", figsize=None):
    """Horizontal bar chart showing period performance across pairs."""
    figsize = figsize or (config.CHART_FIGSIZE_FULL[0], max(3.0, len(perf_data) * 0.35))
    fig, ax = plt.subplots(figsize=figsize)

    pairs = list(perf_data.keys())
    vals = [perf_data[p].get(period, 0) or 0 for p in pairs]

    colors = [config.COLORS["positive"] if v >= 0 else config.COLORS["negative"] for v in vals]

    y_pos = range(len(pairs))
    ax.barh(y_pos, vals, color=colors, alpha=0.8, height=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(pairs)
    ax.set_xlabel(f"{period} Change (%)")
    ax.set_title(f"Currency Pair Performance ({period})", fontweight="bold", pad=8)
    ax.axvline(0, color="gray", linewidth=0.5)
    ax.grid(axis="x", alpha=0.3)

    # Value labels
    for i, v in enumerate(vals):
        ax.text(v + (0.05 if v >= 0 else -0.05), i, f"{v:+.2f}%",
                va="center", ha="left" if v >= 0 else "right", fontsize=6)

    fig.tight_layout()
    return _to_bytes(fig)


# ═══════════════════════════════════════════════════════════════
#  Multi-pair Overview Chart
# ═══════════════════════════════════════════════════════════════
def chart_multi_pair_grid(hist_batch, pairs, cols=2, figsize=None):
    """Grid of small price charts for multiple pairs."""
    n = len(pairs)
    rows = math.ceil(n / cols)
    figsize = figsize or (7.5, rows * 2.0)
    fig, axes = plt.subplots(rows, cols, figsize=figsize)
    axes = np.array(axes).flatten()

    for i, pair in enumerate(pairs):
        ax = axes[i]
        if pair in hist_batch:
            df = hist_batch[pair]
            prices = df["close"].values
            dates = df["date"]
            color = config.COLORS["positive"] if prices[-1] >= prices[0] else config.COLORS["negative"]
            ax.plot(dates, prices, color=color, linewidth=1.0)
            ax.fill_between(dates, prices, alpha=0.08, color=color)

            chg = (prices[-1] / prices[0] - 1) * 100
            sign = "+" if chg >= 0 else ""
            ax.set_title(f"{pair}  ({sign}{chg:.2f}%)", fontsize=8, fontweight="bold",
                        color=config.COLORS["positive"] if chg >= 0 else config.COLORS["negative"])
        else:
            ax.set_title(pair, fontsize=8)
            ax.text(0.5, 0.5, "No Data", ha="center", va="center", transform=ax.transAxes)

        ax.tick_params(labelsize=6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.grid(True, alpha=0.2)

    # Hide unused axes
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Currency Pair Overview (90D)", fontsize=10, fontweight="bold", y=1.02)
    fig.tight_layout()
    return _to_bytes(fig)
