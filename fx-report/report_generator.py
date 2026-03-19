# -*- coding: utf-8 -*-
"""
Report Generator — assembles data + charts + commentary into HTML, then renders to PDF.
Enhanced with client-profile-aware report generation.
"""
import os
import base64
import yaml
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from data_provider import FXDataProvider
from chart_builder import (
    spot_rate_heatmap, vol_term_structure, vol_bar_comparison,
    flow_pie_chart, flow_bar_by_business, risk_event_timeline,
    corridor_volume_chart, corridor_spread_chart, corridor_seasonality_chart,
    focus_pairs_heatmap,
    generate_sparkline_svg, market_temperature_gauge,
    traffic_light_panel, what_changed_chart,
)

BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"


class ReportGenerator:
    """Orchestrates the full report generation pipeline."""

    def __init__(self, config: dict, overrides: dict = None):
        self.config = config
        self.overrides = overrides or {}
        self.provider = FXDataProvider(config)
        self.sections = config.get("sections", {})
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )
        self.jinja_env.filters["format_number"] = lambda v, d=0: f"{v:,.{d}f}" if v else "N/A"
        self.jinja_env.filters["format_pct"] = lambda v: f"{v:+.2f}%" if v is not None else "N/A"
        self.jinja_env.filters["format_vol"] = lambda v: f"{v:.2f}%" if v else "N/A"
        self.jinja_env.filters["usd_millions"] = lambda v: f"${v/1e6:,.1f}M" if v else "N/A"

    def gather_data(self, as_of: str = None) -> dict:
        """Collect all data needed for the report."""
        data = {
            "report_date": as_of or datetime.now().strftime("%Y-%m-%d"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "config": self.config.get("report", {}),
        }

        # i18n labels — pick language from config
        lang = self.config.get("report", {}).get("language", "en")
        i18n_all = self.config.get("i18n", {})
        data["lang"] = lang
        data["t"] = i18n_all.get(lang, i18n_all.get("en", {}))

        # Client profile info
        profile = self.provider.get_active_profile()
        if profile:
            data["client_profile"] = profile
            data["profile_key"] = self.config.get("_active_client_profile", "")
        else:
            data["client_profile"] = None
            data["profile_key"] = ""

        if self.sections.get("market_overview") or self.sections.get("executive_summary"):
            data["spot_rates"] = self.provider.get_spot_rates(as_of)

        if self.sections.get("volatility_analysis"):
            data["vol_data"] = self.provider.get_vol_data()

        if self.sections.get("flow_analysis"):
            data["flow_data"] = self.provider.get_flow_data()

        if self.sections.get("risk_monitor"):
            data["macro_events"] = self.provider.get_macro_events()

        if self.sections.get("macro_outlook") or self.sections.get("executive_summary"):
            data["commentary"] = self.provider.get_commentary()
            data["news"] = self.provider.get_news()
            data["economic"] = self.provider.get_economic_indicators()

        # Client corridor data
        if self.sections.get("client_corridor") and profile:
            data["corridor_data"] = self.provider.get_corridor_data()
            data["client_commentary"] = self.provider.get_client_commentary()

        # Data sources tracking
        data["data_sources"] = self.provider.get_data_sources()

        # Apply any manual overrides from the web form
        if "commentary" in self.overrides:
            if "commentary" not in data:
                data["commentary"] = {}
            data["commentary"].update(self.overrides["commentary"])

        # ── NEW: Compute enhanced analytics ──
        self._enrich_with_sparklines(data)
        self._enrich_with_traffic_lights(data)
        self._enrich_with_what_changed(data)
        self._enrich_with_market_temperature(data)

        return data

    def _enrich_with_sparklines(self, data: dict):
        """Generate sparkline SVG strings for key pairs using historical rates from Frankfurter."""
        spot_rates = data.get("spot_rates", {})
        if not spot_rates or "_error" in spot_rates:
            return

        sparklines = {}
        for pair, info in spot_rates.items():
            if pair.startswith("_") or not isinstance(info, dict):
                continue
            # Build a synthetic "trend" from the available change data
            # We'll use chg_ytd, chg_1m, chg_1w, chg_1d to create a rough curve
            rate = info.get("rate")
            if rate is None:
                continue
            chg_ytd = info.get("chg_ytd") or 0
            chg_1m = info.get("chg_1m") or 0
            chg_1w = info.get("chg_1w") or 0
            chg_1d = info.get("chg_1d") or 0

            # Reconstruct approximate historical values
            ytd_rate = rate / (1 + chg_ytd / 100) if chg_ytd != 0 else rate
            m1_rate = rate / (1 + chg_1m / 100) if chg_1m != 0 else rate
            w1_rate = rate / (1 + chg_1w / 100) if chg_1w != 0 else rate
            d1_rate = rate / (1 + chg_1d / 100) if chg_1d != 0 else rate

            # Create 5-point series: YTD start → 1M ago → 1W ago → 1D ago → now
            values = [ytd_rate, m1_rate, w1_rate, d1_rate, rate]
            sparklines[pair] = Markup(generate_sparkline_svg(values))

        data["sparklines"] = sparklines

    def _enrich_with_traffic_lights(self, data: dict):
        """Compute traffic light signals for focus pairs based on momentum & volatility."""
        spot_rates = data.get("spot_rates", {})
        if not spot_rates or "_error" in spot_rates:
            return

        profile = data.get("client_profile")
        if profile:
            focus = profile.get("focus_pairs", [])[:6]
        else:
            focus = ["USDCNH", "EURUSD", "USDJPY", "GBPUSD"]

        signals = []
        for pair in focus:
            info = spot_rates.get(pair)
            if not info or not isinstance(info, dict):
                continue
            chg_1w = info.get("chg_1w")
            chg_1m = info.get("chg_1m")
            if chg_1w is None and chg_1m is None:
                continue

            # Signal logic: based on 1W momentum and 1M trend alignment
            w = chg_1w or 0
            m = chg_1m or 0
            abs_w = abs(w)

            if abs_w < 0.5:
                signal = "green"
                rationale = "Stable"
            elif abs_w < 1.5:
                if (w > 0 and m > 0) or (w < 0 and m < 0):
                    signal = "yellow"
                    rationale = "Trending"
                else:
                    signal = "yellow"
                    rationale = "Mixed signals"
            else:
                signal = "red"
                rationale = f"{'▲' if w > 0 else '▼'} {abs_w:.1f}% 1W"

            signals.append({
                "pair": pair,
                "signal": signal,
                "rationale": rationale,
            })

        data["traffic_light_signals"] = signals

    def _enrich_with_what_changed(self, data: dict):
        """Identify significant moves (>0.5% weekly) for the 'What Changed' section."""
        spot_rates = data.get("spot_rates", {})
        if not spot_rates or "_error" in spot_rates:
            return

        changes = []
        for pair, info in spot_rates.items():
            if pair.startswith("_") or not isinstance(info, dict):
                continue
            chg_1w = info.get("chg_1w")
            if chg_1w is not None and abs(chg_1w) >= 0.5:
                changes.append({
                    "pair": pair,
                    "change_pct": chg_1w,
                    "period": "1W",
                    "rate": info.get("rate"),
                })

        # Sort by absolute change, descending
        changes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        data["what_changed"] = changes[:8]  # Top 8 biggest movers

    def _enrich_with_market_temperature(self, data: dict):
        """Calculate a market temperature score (0-100) based on aggregate volatility."""
        spot_rates = data.get("spot_rates", {})
        if not spot_rates or "_error" in spot_rates:
            data["market_temperature"] = 50  # Default neutral
            return

        # Use absolute 1W changes as a proxy for realized vol
        abs_changes = []
        for pair, info in spot_rates.items():
            if pair.startswith("_") or not isinstance(info, dict):
                continue
            chg = info.get("chg_1w")
            if chg is not None:
                abs_changes.append(abs(chg))

        if not abs_changes:
            data["market_temperature"] = 50
            return

        avg_move = sum(abs_changes) / len(abs_changes)
        # Map: 0% avg → score 10, 0.5% avg → 35, 1% avg → 55, 2% avg → 80, 3%+ → 95
        if avg_move <= 0.5:
            score = 10 + (avg_move / 0.5) * 25
        elif avg_move <= 1.0:
            score = 35 + ((avg_move - 0.5) / 0.5) * 20
        elif avg_move <= 2.0:
            score = 55 + ((avg_move - 1.0) / 1.0) * 25
        else:
            score = min(95, 80 + ((avg_move - 2.0) / 1.0) * 15)

        data["market_temperature"] = round(score, 0)

    def generate_charts(self, data: dict) -> dict:
        """Generate all chart images as base64 strings. Skip sections with errors."""
        charts = {}
        profile = data.get("client_profile")

        try:
            spot_rates = data.get("spot_rates", {})
            if spot_rates and "_error" not in spot_rates:
                charts["spot_heatmap"] = spot_rate_heatmap(spot_rates)
        except Exception as e:
            charts["spot_heatmap_error"] = str(e)

        try:
            vol_data = data.get("vol_data", {})
            if vol_data and "_error" not in vol_data:
                if profile:
                    focus = profile.get("focus_pairs", [])
                    available_focus = [p for p in focus if p in vol_data]
                    if available_focus:
                        charts["vol_term_structure"] = vol_term_structure(vol_data, available_focus)
                    else:
                        majors = self.config.get("currencies", {}).get("major", [])
                        charts["vol_term_structure"] = vol_term_structure(vol_data, majors)
                else:
                    majors = self.config.get("currencies", {}).get("major", [])
                    charts["vol_term_structure"] = vol_term_structure(vol_data, majors)
                charts["vol_comparison"] = vol_bar_comparison(vol_data)
        except Exception as e:
            charts["vol_error"] = str(e)

        try:
            flow_data = data.get("flow_data", {})
            if flow_data and "_error" not in flow_data:
                charts["flow_pie"] = flow_pie_chart(flow_data)
                charts["flow_bar"] = flow_bar_by_business(flow_data)
        except Exception as e:
            charts["flow_error"] = str(e)

        try:
            macro_events = data.get("macro_events", [])
            if macro_events and (isinstance(macro_events, list) and len(macro_events) > 0 and "_error" not in macro_events[0]):
                charts["event_timeline"] = risk_event_timeline(macro_events)
        except Exception as e:
            charts["event_error"] = str(e)

        # Corridor-specific charts
        try:
            corridor_data = data.get("corridor_data", {})
            if corridor_data and "_error" not in corridor_data:
                # Only generate volume/spread charts if volume data exists
                corridors = corridor_data.get("corridors", [])
                has_volume = any(c.get("volume_usd") for c in corridors)
                if has_volume:
                    charts["corridor_volume"] = corridor_volume_chart(corridor_data)
                    charts["corridor_spread"] = corridor_spread_chart(corridor_data)
                if corridor_data.get("seasonality"):
                    charts["corridor_seasonality"] = corridor_seasonality_chart(corridor_data)
        except Exception as e:
            charts["corridor_error"] = str(e)

        # Focus pairs heatmap
        try:
            spot_rates = data.get("spot_rates", {})
            if profile and spot_rates and "_error" not in spot_rates:
                focus = profile.get("focus_pairs", [])
                if focus:
                    charts["focus_heatmap"] = focus_pairs_heatmap(spot_rates, focus)
        except Exception as e:
            charts["focus_heatmap_error"] = str(e)

        # ── NEW: Traffic Light Panel ──
        try:
            signals = data.get("traffic_light_signals", [])
            if signals:
                charts["traffic_light"] = traffic_light_panel(signals)
        except Exception as e:
            charts["traffic_light_error"] = str(e)

        # ── NEW: What Changed Chart ──
        try:
            changes = data.get("what_changed", [])
            if changes:
                charts["what_changed"] = what_changed_chart(changes)
        except Exception as e:
            charts["what_changed_error"] = str(e)

        # ── NEW: Market Temperature Gauge ──
        try:
            temp = data.get("market_temperature", 50)
            charts["market_gauge"] = market_temperature_gauge(temp, label="Market Regime")
        except Exception as e:
            charts["market_gauge_error"] = str(e)

        return charts

    def render_html(self, data: dict, charts: dict) -> str:
        """Render the full report as HTML."""
        template = self.jinja_env.get_template("report.html")
        # Load official TenPay Global logo as base64
        logo_path = Path(__file__).parent / "data" / "WXWorkCapture_17724263838761.png"
        logo_b64 = ""
        if logo_path.exists():
            logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        return template.render(data=data, charts=charts, sections=self.sections, logo_b64=logo_b64)

    def generate(self, as_of: str = None, output_format: str = "html") -> str:
        """Full pipeline: data → charts → HTML → optional PDF."""
        data = self.gather_data(as_of)
        charts = self.generate_charts(data)
        html_content = self.render_html(data, charts)

        OUTPUT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_tag = f"_{data.get('profile_key', '')}" if data.get('profile_key') else ""
        base_name = f"FX_Report_{data['report_date']}{profile_tag}_{timestamp}"

        if output_format == "pdf":
            return self._render_pdf(html_content, base_name)
        else:
            html_path = OUTPUT_DIR / f"{base_name}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return str(html_path)

    def _render_pdf(self, html_content: str, base_name: str) -> str:
        try:
            from weasyprint import HTML
            pdf_path = OUTPUT_DIR / f"{base_name}.pdf"
            HTML(string=html_content, base_url=str(BASE_DIR)).write_pdf(str(pdf_path))
            return str(pdf_path)
        except ImportError:
            html_path = OUTPUT_DIR / f"{base_name}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return str(html_path)
