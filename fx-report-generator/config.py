"""
FX Research Report Generator - Configuration
Tenpay Global FX Report
"""

# ── Report Branding ──────────────────────────────────────────
REPORT_TITLE = "Tenpay Global FX Research Report"
REPORT_SUBTITLE = "Foreign Exchange Market Analysis"
COMPANY_NAME = "Tenpay Global"
DISCLAIMER = (
    "This report is prepared by Tenpay Global for internal reference only. "
    "It does not constitute investment advice. Past performance is not indicative of future results. "
    "Foreign exchange trading involves significant risk of loss."
)

# ── Color Palette (Tenpay brand-aligned) ─────────────────────
COLORS = {
    "primary": "#1a237e",       # Deep navy
    "secondary": "#0d47a1",     # Blue
    "accent": "#00695c",        # Teal
    "positive": "#2e7d32",      # Green (for gains)
    "negative": "#c62828",      # Red (for losses)
    "neutral": "#546e7a",       # Grey-blue
    "bg_light": "#f5f7fa",      # Light background
    "bg_header": "#1a237e",     # Header background
    "text_dark": "#212121",
    "text_light": "#ffffff",
    "border": "#cfd8dc",
    "chart_colors": ["#1a237e", "#0d47a1", "#1565c0", "#1976d2", "#1e88e5",
                     "#2196f3", "#42a5f5", "#64b5f6", "#90caf9", "#bbdefb"],
}

# ── Currency Pairs ───────────────────────────────────────────
MAJOR_PAIRS = ["USDCNY", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDSGD", "USDHKD"]
EM_PAIRS = ["USDBRL", "USDMXN", "USDINR", "USDPHP", "USDTHB", "USDKRW", "USDIDR"]
ALL_PAIRS = MAJOR_PAIRS + EM_PAIRS

# ── Data API Configuration ───────────────────────────────────
# Free fallback APIs (no key required)
EXCHANGE_RATE_API = "https://open.er-api.com/v6/latest/{base}"

# ECB (European Central Bank) - free, no key
ECB_API = "https://data-api.ecb.europa.eu/service/data/EXR/D.{currency}.EUR.SP00.A"

# ── Report Sections Toggle ───────────────────────────────────
SECTIONS = {
    "cover": True,
    "executive_summary": True,
    "market_overview": True,
    "major_pairs_analysis": True,
    "em_pairs_analysis": True,
    "volatility_analysis": True,
    "correlation_matrix": True,
    "macro_calendar": True,
    "risk_monitor": True,
    "appendix": True,
}

# ── Chart Settings ───────────────────────────────────────────
CHART_DPI = 150
CHART_STYLE = "seaborn-v0_8-whitegrid"
CHART_FIGSIZE_FULL = (7.5, 3.5)
CHART_FIGSIZE_HALF = (3.6, 3.0)
CHART_FIGSIZE_SQUARE = (3.5, 3.5)

# ── PDF Layout ───────────────────────────────────────────────
PAGE_SIZE = "A4"
MARGIN_LEFT = 50
MARGIN_RIGHT = 50
MARGIN_TOP = 60
MARGIN_BOTTOM = 50
