# -*- coding: utf-8 -*-
"""
Chart Builder — generates static chart images (PNG/SVG) using Plotly + Kaleido.
All charts follow Tenpay Global brand styling — Tencent Blue palette.
Enhanced with corridor-specific visualizations, sparklines, gauges, and traffic light panels.
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import base64
import io
import math

# ═══════════════════════════════════════════════════════
# Tenpay Global Brand Colors — Tencent Blue Palette
# Based on official Tencent Blue (#3458B0) and
# Tenpay Global website color scheme
# ═══════════════════════════════════════════════════════
COLORS = {
    "primary":     "#0052D9",   # Tenpay Global Primary Blue
    "secondary":   "#5F6A7A",   # Cool Gray
    "accent":      "#3458B0",   # Tencent Blue
    "light_blue":  "#E8F0FE",   # Soft Blue BG
    "danger":      "#D54941",   # Risk/Negative Red
    "warning":     "#E37318",   # Amber Warning
    "bg":          "#F7F8FA",   # Light Gray Background
    "grid":        "#E7E8EB",   # Grid Lines
    "text":        "#181B22",   # Near Black Text
    "positive":    "#00A870",   # Green Positive
    "negative":    "#D54941",   # Red Negative
    "brand_dark":  "#0A1F44",   # Deep Navy
    "brand_gold":  "#D4A843",   # Gold Accent
    "tencent_blue":"#3458B0",   # Official Tencent Blue
}

# Tenpay Global Palette — vibrant, professional, fintech
PALETTE = [
    "#0052D9",  # Primary Blue
    "#00A870",  # Green
    "#E37318",  # Amber
    "#D54941",  # Red
    "#7C3AED",  # Purple
    "#0594FA",  # Bright Blue
    "#3458B0",  # Tencent Blue
    "#00B5D9",  # Cyan
    "#F5A623",  # Gold
    "#6B7280",  # Gray
]

LAYOUT_DEFAULTS = dict(
    font=dict(family="'TencentSans', 'Noto Sans SC', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif", size=11, color=COLORS["text"]),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=50, r=30, t=40, b=40),
    xaxis=dict(gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
    yaxis=dict(gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
)


def _fig_to_base64(fig, width=700, height=380) -> str:
    img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
    return base64.b64encode(img_bytes).decode("utf-8")


def spot_rate_heatmap(spot_data: dict) -> str:
    ccys = list(spot_data.keys())
    horizons = ["chg_1d", "chg_1w", "chg_1m", "chg_ytd"]
    labels = ["1D %", "1W %", "1M %", "YTD %"]
    z = [[spot_data[c].get(h, 0) for h in horizons] for c in ccys]
    fig = go.Figure(data=go.Heatmap(
        z=z, x=labels, y=ccys,
        colorscale=[[0, COLORS["negative"]], [0.5, "white"], [1, COLORS["positive"]]],
        zmid=0, text=[[f"{v:+.2f}%" for v in row] for row in z],
        texttemplate="%{text}", textfont=dict(size=10),
        hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
        colorbar=dict(title="% Chg", thickness=12, len=0.8),
    ))
    fig.update_layout(**LAYOUT_DEFAULTS, title="FX Spot Rate Changes", height=max(350, len(ccys) * 28 + 80))
    return _fig_to_base64(fig, width=600, height=max(350, len(ccys) * 28 + 80))


def vol_term_structure(vol_data: dict, ccys: list = None) -> str:
    if ccys is None:
        ccys = list(vol_data.keys())[:6]
    tenors = ["vol_1w", "vol_1m", "vol_3m", "vol_6m", "vol_1y"]
    tenor_labels = ["1W", "1M", "3M", "6M", "1Y"]
    fig = go.Figure()
    for i, ccy in enumerate(ccys):
        if ccy not in vol_data:
            continue
        vols = [vol_data[ccy].get(t, 0) for t in tenors]
        fig.add_trace(go.Scatter(
            x=tenor_labels, y=vols, name=ccy, mode="lines+markers",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            marker=dict(size=6),
        ))
    fig.update_layout(**LAYOUT_DEFAULTS, title="Implied Volatility Term Structure",
                      yaxis_title="Implied Vol (%)", legend=dict(orientation="h", y=-0.15))
    return _fig_to_base64(fig)


def vol_bar_comparison(vol_data: dict) -> str:
    ccys = list(vol_data.keys())
    vol_1m = [vol_data[c].get("vol_1m", 0) for c in ccys]
    vol_3m = [vol_data[c].get("vol_3m", 0) for c in ccys]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ccys, y=vol_1m, name="1M Vol", marker_color=COLORS["primary"]))
    fig.add_trace(go.Bar(x=ccys, y=vol_3m, name="3M Vol", marker_color=COLORS["positive"]))
    fig.update_layout(**LAYOUT_DEFAULTS, title="Implied Volatility Comparison",
                      barmode="group", yaxis_title="Vol (%)",
                      legend=dict(orientation="h", y=-0.15))
    return _fig_to_base64(fig, width=750, height=350)


def flow_pie_chart(flow_data: dict) -> str:
    by_ccy = flow_data.get("by_currency", {})
    sorted_ccys = sorted(by_ccy.items(), key=lambda x: x[1]["volume_usd"], reverse=True)
    top = sorted_ccys[:10]
    others_vol = sum(v["volume_usd"] for _, v in sorted_ccys[10:])
    labels = [c for c, _ in top]
    values = [v["volume_usd"] for _, v in top]
    if others_vol > 0:
        labels.append("Others")
        values.append(others_vol)
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        marker=dict(colors=PALETTE[:len(labels)]),
        textinfo="label+percent", textfont=dict(size=10),
        hole=0.35,
    )])
    fig.update_layout(**LAYOUT_DEFAULTS, title="FX Volume by Currency", showlegend=False)
    return _fig_to_base64(fig, width=500, height=400)


def flow_bar_by_business(flow_data: dict) -> str:
    by_biz = flow_data.get("by_business", {})
    names = list(by_biz.keys())
    volumes = [by_biz[n]["volume_usd"] / 1e6 for n in names]
    fig = go.Figure(data=[go.Bar(
        y=names, x=volumes, orientation="h",
        marker_color=PALETTE[:len(names)],
        text=[f"${v:,.0f}M" for v in volumes],
        textposition="outside",
    )])
    fig.update_layout(**LAYOUT_DEFAULTS, title="Volume by Business Line",
                      xaxis_title="Volume (USD Millions)")
    return _fig_to_base64(fig, width=600, height=300)


def risk_event_timeline(events: list) -> str:
    if not events:
        return ""
    impact_map = {"High": 3, "Medium": 2, "Low": 1}
    color_map = {"High": COLORS["danger"], "Medium": COLORS["warning"], "Low": COLORS["secondary"]}
    fig = go.Figure()
    for evt in events:
        imp = evt.get("impact", "Medium")
        fig.add_trace(go.Scatter(
            x=[evt["date"]], y=[impact_map.get(imp, 2)],
            mode="markers+text", text=[evt["event"]],
            textposition="top center", textfont=dict(size=9),
            marker=dict(size=14, color=color_map.get(imp, COLORS["secondary"])),
            showlegend=False,
            hovertemplate=f"<b>{evt['event']}</b><br>Date: {evt['date']}<br>Impact: {imp}<br>Currency: {evt.get('currency','')}<extra></extra>",
        ))
    fig.update_layout(**LAYOUT_DEFAULTS, title="Upcoming Risk Events",
                      yaxis=dict(tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"],
                                 range=[0.5, 3.8], gridcolor=COLORS["grid"]),
                      height=280)
    return _fig_to_base64(fig, width=750, height=280)


# ──────────────────────────────────────────────
# Corridor-specific charts
# ──────────────────────────────────────────────

def corridor_volume_chart(corridor_data: dict) -> str:
    """Horizontal bar chart of volume by corridor with direction coloring."""
    corridors = corridor_data.get("corridors", [])
    if not corridors:
        return ""

    labels = [c["label"] for c in corridors]
    volumes = [c["volume_usd"] / 1e6 for c in corridors]
    colors = [COLORS["primary"] if c["direction"] == "inbound" else COLORS["danger"] for c in corridors]

    fig = go.Figure(data=[go.Bar(
        y=labels, x=volumes, orientation="h",
        marker_color=colors,
        text=[f"${v:,.1f}M" for v in volumes],
        textposition="outside",
    )])
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Corridor Volume (USD Millions)",
        xaxis_title="Volume (USD M)",
        height=max(250, len(corridors) * 45 + 80),
        margin=dict(l=200, r=80, t=40, b=40),
    )
    return _fig_to_base64(fig, width=700, height=max(250, len(corridors) * 45 + 80))


def corridor_spread_chart(corridor_data: dict) -> str:
    """Spread (bps) comparison across corridors with trend indicators."""
    corridors = corridor_data.get("corridors", [])
    if not corridors:
        return ""

    labels = [c["pair"] for c in corridors]
    spreads = [c.get("avg_spread_bps", 0) for c in corridors]
    trends = [c.get("spread_trend", "stable") for c in corridors]
    trend_colors = {"tightening": COLORS["positive"], "stable": COLORS["primary"], "widening": COLORS["danger"]}
    colors = [trend_colors.get(t, COLORS["primary"]) for t in trends]

    fig = go.Figure(data=[go.Bar(
        x=labels, y=spreads,
        marker_color=colors,
        text=[f"{s:.1f} bps" for s in spreads],
        textposition="outside",
    )])

    for i, (label, trend) in enumerate(zip(labels, trends)):
        arrow = "↓" if trend == "tightening" else "↑" if trend == "widening" else "→"
        fig.add_annotation(
            x=label, y=spreads[i] + 2,
            text=f"{arrow} {trend.title()}",
            showarrow=False, font=dict(size=8, color=trend_colors.get(trend, "#666")),
            yshift=15,
        )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Average Spread by Corridor (bps)",
        yaxis_title="Spread (bps)",
        height=320,
    )
    return _fig_to_base64(fig, width=650, height=320)


def corridor_seasonality_chart(corridor_data: dict) -> str:
    """Monthly seasonality index chart."""
    seasonality = corridor_data.get("seasonality", [])
    if not seasonality:
        return ""

    base = corridor_data.get("base_currency", "")
    months = [s["month"] for s in seasonality]
    values = [s["index"] for s in seasonality]

    colors = [COLORS["positive"] if v >= 1.0 else COLORS["warning"] for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months, y=values,
        marker_color=colors,
        text=[f"{v:.2f}x" for v in values],
        textposition="outside",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color=COLORS["secondary"], line_width=1)
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=f"{base} Corridor Volume Seasonality Index",
        yaxis_title="Volume Index (1.0 = Average)",
        yaxis=dict(range=[0.7, 1.4], gridcolor=COLORS["grid"]),
        height=300,
    )
    return _fig_to_base64(fig, width=650, height=300)


def focus_pairs_heatmap(spot_data: dict, focus_pairs: list) -> str:
    """Heatmap for client-specific focus pairs only."""
    available = [p for p in focus_pairs if p in spot_data]
    if not available:
        return ""

    horizons = ["chg_1d", "chg_1w", "chg_1m", "chg_ytd"]
    labels = ["1D %", "1W %", "1M %", "YTD %"]
    z = [[spot_data[c].get(h, 0) for h in horizons] for c in available]

    fig = go.Figure(data=go.Heatmap(
        z=z, x=labels, y=available,
        colorscale=[[0, COLORS["negative"]], [0.5, "white"], [1, COLORS["positive"]]],
        zmid=0, text=[[f"{v:+.2f}%" for v in row] for row in z],
        texttemplate="%{text}", textfont=dict(size=11),
        hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
        colorbar=dict(title="% Chg", thickness=12, len=0.8),
    ))
    fig.update_layout(**LAYOUT_DEFAULTS, title="Focus Pairs Performance",
                      height=max(200, len(available) * 40 + 80))
    return _fig_to_base64(fig, width=550, height=max(200, len(available) * 40 + 80))


# ──────────────────────────────────────────────
# NEW: Sparkline mini-charts for cover & tables
# ──────────────────────────────────────────────

def generate_sparkline_svg(values: list, width: int = 80, height: int = 24,
                           color_up: str = None, color_down: str = None) -> str:
    """Generate an inline SVG sparkline from a list of numeric values.
    Returns raw SVG string suitable for embedding in HTML.
    """
    if not values or len(values) < 2:
        return ""
    color_up = color_up or COLORS["positive"]
    color_down = color_down or COLORS["negative"]

    # Determine if trend is up or down
    trend_color = color_up if values[-1] >= values[0] else color_down

    # Normalize values to SVG coordinates
    min_v = min(values)
    max_v = max(values)
    v_range = max_v - min_v if max_v != min_v else 1
    padding = 2

    points = []
    for i, v in enumerate(values):
        x = padding + (i / (len(values) - 1)) * (width - 2 * padding)
        y = height - padding - ((v - min_v) / v_range) * (height - 2 * padding)
        points.append(f"{x:.1f},{y:.1f}")

    polyline = " ".join(points)

    # Create gradient fill area
    fill_points = f"{padding:.1f},{height - padding:.1f} " + polyline + f" {width - padding:.1f},{height - padding:.1f}"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="vertical-align:middle;">
  <defs>
    <linearGradient id="sparkFill_{id(values)}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{trend_color}" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="{trend_color}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <polygon points="{fill_points}" fill="url(#sparkFill_{id(values)})"/>
  <polyline points="{polyline}" fill="none" stroke="{trend_color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{points[-1].split(',')[0]}" cy="{points[-1].split(',')[1]}" r="2" fill="{trend_color}"/>
</svg>'''
    return svg


def market_temperature_gauge(score: float, label: str = "Market Regime") -> str:
    """Generate a semicircular gauge chart showing market temperature.
    score: 0-100, where:
      0-30  = Low Vol / Risk-On (Green)
      30-60 = Normal (Blue)
      60-80 = Elevated (Amber)
      80-100 = High Vol / Risk-Off (Red)
    Returns base64 PNG.
    """
    fig = go.Figure()

    # Background arc segments
    segments = [
        (0, 30, COLORS["positive"], "Low Vol"),
        (30, 60, COLORS["primary"], "Normal"),
        (60, 80, COLORS["warning"], "Elevated"),
        (80, 100, COLORS["danger"], "High Vol"),
    ]

    for start, end, color, seg_label in segments:
        theta_start = 180 - (start / 100) * 180
        theta_end = 180 - (end / 100) * 180
        # Generate arc points
        n_points = 20
        theta_vals = [theta_start + (theta_end - theta_start) * i / n_points for i in range(n_points + 1)]
        x_outer = [1.0 * math.cos(math.radians(t)) for t in theta_vals]
        y_outer = [1.0 * math.sin(math.radians(t)) for t in theta_vals]
        x_inner = [0.65 * math.cos(math.radians(t)) for t in reversed(theta_vals)]
        y_inner = [0.65 * math.sin(math.radians(t)) for t in reversed(theta_vals)]

        fig.add_trace(go.Scatter(
            x=x_outer + x_inner + [x_outer[0]],
            y=y_outer + y_inner + [y_outer[0]],
            fill="toself", fillcolor=color,
            line=dict(color="white", width=1),
            showlegend=False, hoverinfo="skip",
            opacity=0.85,
        ))

    # Needle
    needle_angle = 180 - (score / 100) * 180
    needle_x = 0.9 * math.cos(math.radians(needle_angle))
    needle_y = 0.9 * math.sin(math.radians(needle_angle))

    fig.add_trace(go.Scatter(
        x=[0, needle_x], y=[0, needle_y],
        mode="lines", line=dict(color=COLORS["brand_dark"], width=3),
        showlegend=False, hoverinfo="skip",
    ))
    # Center dot
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(size=10, color=COLORS["brand_dark"]),
        showlegend=False, hoverinfo="skip",
    ))

    # Score text
    fig.add_annotation(
        x=0, y=-0.15, text=f"<b>{score:.0f}</b>",
        font=dict(size=28, color=COLORS["brand_dark"], family="Georgia, serif"),
        showarrow=False,
    )
    fig.add_annotation(
        x=0, y=-0.32, text=label,
        font=dict(size=11, color=COLORS["secondary"]),
        showarrow=False,
    )

    # Segment labels
    for start, end, color, seg_label in segments:
        mid = (start + end) / 2
        angle = 180 - (mid / 100) * 180
        lx = 1.15 * math.cos(math.radians(angle))
        ly = 1.15 * math.sin(math.radians(angle))
        fig.add_annotation(
            x=lx, y=ly, text=seg_label,
            font=dict(size=7, color=COLORS["secondary"]),
            showarrow=False,
        )

    fig.update_layout(
        xaxis=dict(range=[-1.4, 1.4], visible=False, fixedrange=True),
        yaxis=dict(range=[-0.5, 1.3], visible=False, fixedrange=True, scaleanchor="x"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        width=280, height=200,
    )
    return _fig_to_base64(fig, width=280, height=200)


def traffic_light_panel(signals: list) -> str:
    """Generate a traffic light signal panel as base64 PNG.
    signals: list of dicts with keys: pair, signal ('green'/'yellow'/'red'), rationale
    Returns base64 PNG.
    """
    if not signals:
        return ""

    n = len(signals)
    fig = make_subplots(rows=1, cols=n, subplot_titles=[s["pair"] for s in signals],
                         horizontal_spacing=0.02)

    signal_colors = {
        "green": COLORS["positive"],
        "yellow": COLORS["warning"],
        "red": COLORS["negative"],
    }
    signal_icons = {
        "green": "▲",
        "yellow": "●",
        "red": "▼",
    }

    for i, sig in enumerate(signals, 1):
        color = signal_colors.get(sig["signal"], COLORS["secondary"])
        fig.add_trace(go.Scatter(
            x=[0], y=[0.5], mode="markers+text",
            marker=dict(size=40, color=color, opacity=0.9),
            text=[signal_icons.get(sig["signal"], "●")],
            textfont=dict(size=20, color="white"),
            textposition="middle center",
            showlegend=False, hoverinfo="skip",
        ), row=1, col=i)

        # Rationale below
        fig.add_annotation(
            x=0, y=-0.3, text=sig.get("rationale", ""),
            font=dict(size=7, color=COLORS["secondary"]),
            showarrow=False, xref=f"x{i}" if i > 1 else "x",
            yref=f"y{i}" if i > 1 else "y",
        )

    for i in range(1, n + 1):
        axis_suffix = str(i) if i > 1 else ""
        fig.update_layout(**{
            f"xaxis{axis_suffix}": dict(visible=False, range=[-1, 1]),
            f"yaxis{axis_suffix}": dict(visible=False, range=[-0.8, 1.2]),
        })

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=5, r=5, t=30, b=20),
        height=130, width=min(n * 120, 700),
    )

    # Update subplot title styling
    for annotation in fig.layout.annotations:
        annotation.font = dict(size=9, color=COLORS["brand_dark"], family="'TencentSans', Arial, sans-serif")

    return _fig_to_base64(fig, width=min(n * 120, 700), height=130)


def what_changed_chart(changes: list) -> str:
    """Generate a horizontal diverging bar chart showing significant moves.
    changes: list of dicts with keys: pair, change_pct, period
    Returns base64 PNG.
    """
    if not changes:
        return ""

    pairs = [c["pair"] for c in changes]
    values = [c["change_pct"] for c in changes]
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in values]
    text_labels = [f"{v:+.2f}%" for v in values]

    fig = go.Figure(data=[go.Bar(
        y=pairs, x=values, orientation="h",
        marker_color=colors,
        text=text_labels,
        textposition="outside",
        textfont=dict(size=10, color=COLORS["text"]),
    )])

    fig.add_vline(x=0, line_color=COLORS["secondary"], line_width=1.5)

    layout = dict(**LAYOUT_DEFAULTS)
    layout["margin"] = dict(l=100, r=80, t=45, b=35)
    fig.update_layout(
        **layout,
        title=dict(text="Significant Moves Since Last Period", font=dict(size=13)),
        xaxis_title="Change (%)",
        height=max(200, len(changes) * 35 + 80),
    )
    return _fig_to_base64(fig, width=600, height=max(200, len(changes) * 35 + 80))
