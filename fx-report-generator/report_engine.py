"""
FX Research Report Generator - PDF Report Engine
Generates professional PDF reports using ReportLab.
"""

import io
import datetime as dt
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import config

PAGE_W, PAGE_H = A4


# ═══════════════════════════════════════════════════════════════
#  Color Helpers
# ═══════════════════════════════════════════════════════════════
def _hex(hex_str):
    return colors.HexColor(hex_str)


C_PRIMARY = _hex(config.COLORS["primary"])
C_SECONDARY = _hex(config.COLORS["secondary"])
C_ACCENT = _hex(config.COLORS["accent"])
C_POS = _hex(config.COLORS["positive"])
C_NEG = _hex(config.COLORS["negative"])
C_BG = _hex(config.COLORS["bg_light"])
C_BORDER = _hex(config.COLORS["border"])
C_TEXT = _hex(config.COLORS["text_dark"])
C_WHITE = colors.white


# ═══════════════════════════════════════════════════════════════
#  Styles
# ═══════════════════════════════════════════════════════════════
def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "CoverTitle", parent=styles["Title"],
        fontSize=28, leading=34, textColor=C_WHITE,
        alignment=TA_LEFT, spaceAfter=6,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "CoverSubtitle", parent=styles["Normal"],
        fontSize=14, leading=18, textColor=colors.HexColor("#bbdefb"),
        alignment=TA_LEFT, spaceAfter=4,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        "CoverDate", parent=styles["Normal"],
        fontSize=11, leading=14, textColor=colors.HexColor("#90caf9"),
        alignment=TA_LEFT,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        "SectionHeader", parent=styles["Heading1"],
        fontSize=14, leading=18, textColor=C_PRIMARY,
        spaceBefore=16, spaceAfter=8,
        fontName="Helvetica-Bold",
        borderWidth=0, borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        "SubSection", parent=styles["Heading2"],
        fontSize=11, leading=14, textColor=C_SECONDARY,
        spaceBefore=10, spaceAfter=4,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "BodyText2", parent=styles["Normal"],
        fontSize=9, leading=13, textColor=C_TEXT,
        alignment=TA_JUSTIFY, spaceAfter=6,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        "SmallText", parent=styles["Normal"],
        fontSize=7.5, leading=10, textColor=colors.HexColor("#78909c"),
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        "TableHeader", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=C_WHITE,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "TableCell", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=C_TEXT,
        alignment=TA_CENTER, fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        "TableCellLeft", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=C_TEXT,
        alignment=TA_LEFT, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "Disclaimer", parent=styles["Normal"],
        fontSize=6.5, leading=9, textColor=colors.HexColor("#9e9e9e"),
        alignment=TA_JUSTIFY, fontName="Helvetica",
    ))

    return styles


# ═══════════════════════════════════════════════════════════════
#  Page Templates (header/footer)
# ═══════════════════════════════════════════════════════════════
def _header_footer(canvas, doc):
    """Draw header and footer on each page."""
    canvas.saveState()

    # Header line
    canvas.setStrokeColor(C_PRIMARY)
    canvas.setLineWidth(1.5)
    canvas.line(config.MARGIN_LEFT, PAGE_H - 42, PAGE_W - config.MARGIN_RIGHT, PAGE_H - 42)

    # Header text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_PRIMARY)
    canvas.drawString(config.MARGIN_LEFT, PAGE_H - 38, config.COMPANY_NAME)
    canvas.drawRightString(PAGE_W - config.MARGIN_RIGHT, PAGE_H - 38, "FX Research Report")

    # Footer
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(config.MARGIN_LEFT, 35, PAGE_W - config.MARGIN_RIGHT, 35)

    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(colors.HexColor("#9e9e9e"))
    canvas.drawString(config.MARGIN_LEFT, 25, "CONFIDENTIAL — For Internal Use Only")
    canvas.drawRightString(PAGE_W - config.MARGIN_RIGHT, 25, f"Page {doc.page}")

    canvas.restoreState()


def _first_page(canvas, doc):
    """No header/footer on cover page."""
    pass


# ═══════════════════════════════════════════════════════════════
#  Helper: build tables
# ═══════════════════════════════════════════════════════════════
def _make_table(headers, rows, col_widths=None):
    """Create a styled table."""
    styles = _build_styles()

    # Header row
    header_row = [Paragraph(h, styles["TableHeader"]) for h in headers]

    # Data rows
    data_rows = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            style = styles["TableCellLeft"] if i == 0 else styles["TableCell"]
            cells.append(Paragraph(str(cell), style))
        data_rows.append(cells)

    table_data = [header_row] + data_rows

    available_width = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
    if col_widths is None:
        col_widths = [available_width / len(headers)] * len(headers)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), C_WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_BG]),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _colored_change(val, fmt="{:+.2f}%"):
    """Format a change value with color."""
    if val is None:
        return "-"
    text = fmt.format(val)
    if val > 0:
        return f'<font color="{config.COLORS["positive"]}">{text}</font>'
    elif val < 0:
        return f'<font color="{config.COLORS["negative"]}">{text}</font>'
    return text


# ═══════════════════════════════════════════════════════════════
#  Section Builders
# ═══════════════════════════════════════════════════════════════
def _build_cover(report_date, styles):
    """Build cover page elements."""
    elements = []

    # Top spacer
    elements.append(Spacer(1, 120))

    # Background rectangle (drawn via canvas, but we use spacers + text)
    elements.append(Paragraph(config.REPORT_TITLE, styles["CoverTitle"]))
    elements.append(Paragraph(config.REPORT_SUBTITLE, styles["CoverSubtitle"]))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        report_date.strftime("%B %d, %Y"), styles["CoverDate"]
    ))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(
        f"Prepared by {config.COMPANY_NAME} — FX Research Desk",
        styles["CoverDate"]
    ))
    elements.append(PageBreak())

    return elements


def _build_executive_summary(summary_text, styles):
    """Build executive summary section."""
    elements = []
    elements.append(Paragraph("1. Executive Summary", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))
    elements.append(Paragraph(summary_text, styles["BodyText2"]))
    elements.append(Spacer(1, 10))
    return elements


def _build_market_overview(spot_df, perf_data, chart_bytes, styles):
    """Build market overview with spot table and performance chart."""
    elements = []
    elements.append(Paragraph("2. Market Overview", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))

    # Spot rate table
    elements.append(Paragraph("Current Spot Rates & Performance", styles["SubSection"]))

    headers = ["Pair", "Spot", "1D", "1W", "1M", "3M"]
    rows = []
    for _, row in spot_df.iterrows():
        pair = row["pair"]
        perf = perf_data.get(pair, {})
        rows.append([
            pair,
            f"{row['spot']:.4f}" if row['spot'] < 100 else f"{row['spot']:.2f}",
            _colored_change(perf.get("1D")),
            _colored_change(perf.get("1W")),
            _colored_change(perf.get("1M")),
            _colored_change(perf.get("3M")),
        ])

    available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
    col_w = [available_w * r for r in [0.15, 0.17, 0.17, 0.17, 0.17, 0.17]]
    elements.append(_make_table(headers, rows, col_w))
    elements.append(Spacer(1, 12))

    # Performance chart
    if chart_bytes:
        elements.append(Image(chart_bytes, width=available_w, height=available_w * 0.45))
        elements.append(Spacer(1, 8))

    return elements


def _build_pair_analysis(pair, commentary, chart_bytes, trend_info, sr_levels, styles):
    """Build analysis section for a single pair."""
    elements = []
    elements.append(Paragraph(pair, styles["SubSection"]))

    # Trend badge
    trend = trend_info.get("trend", "Neutral")
    trend_color = {
        "Bullish": config.COLORS["positive"],
        "Bearish": config.COLORS["negative"],
        "Neutral": config.COLORS["neutral"],
    }.get(trend, config.COLORS["neutral"])

    badge_text = (
        f'<font color="{trend_color}"><b>[{trend}]</b></font> '
        f'RSI: {trend_info.get("rsi", "N/A")} | '
        f'Signal: {trend_info.get("signal", "N/A")}'
    )
    elements.append(Paragraph(badge_text, styles["SmallText"]))
    elements.append(Spacer(1, 4))

    # Chart
    if chart_bytes:
        available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
        elements.append(Image(chart_bytes, width=available_w, height=available_w * 0.55))
        elements.append(Spacer(1, 6))

    # Commentary
    elements.append(Paragraph(commentary, styles["BodyText2"]))

    # Support/Resistance mini table
    sr_headers = ["Level", "Value"]
    sr_rows = [
        ["Resistance 2", f"{sr_levels['resistance_2']:.4f}" if sr_levels['resistance_2'] < 100 else f"{sr_levels['resistance_2']:.2f}"],
        ["Resistance 1", f"{sr_levels['resistance_1']:.4f}" if sr_levels['resistance_1'] < 100 else f"{sr_levels['resistance_1']:.2f}"],
        ["Pivot", f"{sr_levels['pivot']:.4f}" if sr_levels['pivot'] < 100 else f"{sr_levels['pivot']:.2f}"],
        ["Support 1", f"{sr_levels['support_1']:.4f}" if sr_levels['support_1'] < 100 else f"{sr_levels['support_1']:.2f}"],
        ["Support 2", f"{sr_levels['support_2']:.4f}" if sr_levels['support_2'] < 100 else f"{sr_levels['support_2']:.2f}"],
    ]
    available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
    sr_table = _make_table(sr_headers, sr_rows, [available_w * 0.3, available_w * 0.3])
    elements.append(sr_table)
    elements.append(Spacer(1, 12))

    return elements


def _build_volatility_section(vol_table, chart_bytes, styles):
    """Build volatility analysis section."""
    elements = []
    elements.append(Paragraph("Volatility Analysis", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))

    # Chart
    if chart_bytes:
        available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
        elements.append(Image(chart_bytes, width=available_w, height=available_w * 0.42))
        elements.append(Spacer(1, 8))

    # Vol table
    headers = ["Pair"] + [c for c in vol_table.columns if c in ["1W", "2W", "1M", "3M"]]
    rows = []
    for pair in vol_table.index:
        row = [pair]
        for h in headers[1:]:
            val = vol_table.loc[pair, h]
            row.append(f"{val:.2f}%" if val else "-")
        rows.append(row)

    available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
    col_w = [available_w / len(headers)] * len(headers)
    elements.append(_make_table(headers, rows, col_w))
    elements.append(Spacer(1, 10))

    return elements


def _build_correlation_section(chart_bytes, styles):
    """Build correlation section."""
    elements = []
    elements.append(Paragraph("Correlation Matrix", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))

    if chart_bytes:
        available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
        size = min(available_w, 350)
        elements.append(Image(chart_bytes, width=size, height=size))
        elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        "The correlation matrix above shows 60-day rolling return correlations between "
        "currency pairs. High positive correlations indicate pairs that tend to move together, "
        "while negative correlations suggest diversification potential.",
        styles["BodyText2"]
    ))
    elements.append(Spacer(1, 10))

    return elements


def _build_macro_calendar(macro_df, styles):
    """Build macro calendar section."""
    elements = []
    elements.append(Paragraph("Macro Event Calendar", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))

    headers = ["Date", "Event", "Currency", "Impact", "Description"]
    rows = []
    for _, row in macro_df.iterrows():
        impact_color = {"High": config.COLORS["negative"], "Medium": config.COLORS["neutral"]}.get(
            row["impact"], config.COLORS["text_dark"])
        impact_str = f'<font color="{impact_color}"><b>{row["impact"]}</b></font>'
        rows.append([
            row["date"],
            row["event"],
            row["currency"],
            impact_str,
            row["description"][:60] + "..." if len(row["description"]) > 60 else row["description"],
        ])

    available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
    col_w = [available_w * r for r in [0.12, 0.22, 0.08, 0.08, 0.50]]
    elements.append(_make_table(headers, rows, col_w))
    elements.append(Spacer(1, 10))

    return elements


def _build_risk_monitor(risk_df, styles):
    """Build risk monitor section."""
    elements = []
    elements.append(Paragraph("Risk Monitor", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))

    headers = ["Pair", "Annual Vol (%)", "Daily VaR 95%", "Max DD (%)", "vs 20D MA (%)"]
    rows = []
    for pair in risk_df.index:
        r = risk_df.loc[pair]
        rows.append([
            pair,
            f"{r['annual_vol_pct']:.2f}",
            f"{r['daily_var_95_pct']:.3f}%",
            _colored_change(r['max_drawdown_pct'], "{:.2f}%"),
            _colored_change(r['vs_20d_ma_pct']),
        ])

    available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
    col_w = [available_w / 5] * 5
    elements.append(_make_table(headers, rows, col_w))
    elements.append(Spacer(1, 10))

    return elements


def _build_disclaimer(styles):
    """Build disclaimer section."""
    elements = []
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=6))
    elements.append(Paragraph("Disclaimer", styles["SmallText"]))
    elements.append(Paragraph(config.DISCLAIMER, styles["Disclaimer"]))
    return elements


# ═══════════════════════════════════════════════════════════════
#  Cover Page Canvas Drawing
# ═══════════════════════════════════════════════════════════════
def _draw_cover_bg(canvas, doc):
    """Draw cover page background."""
    canvas.saveState()

    # Full page navy background
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Accent stripe
    canvas.setFillColor(_hex("#0d47a1"))
    canvas.rect(0, PAGE_H * 0.35, PAGE_W, 4, fill=1, stroke=0)

    # Bottom accent bar
    canvas.setFillColor(_hex("#00695c"))
    canvas.rect(0, 0, PAGE_W, 8, fill=1, stroke=0)

    # Decorative lines
    canvas.setStrokeColor(colors.HexColor("#1565c0"))
    canvas.setLineWidth(0.5)
    for y_offset in [0.7, 0.68, 0.36, 0.34]:
        canvas.line(config.MARGIN_LEFT, PAGE_H * y_offset,
                    PAGE_W - config.MARGIN_RIGHT, PAGE_H * y_offset)

    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════
#  Main PDF Builder
# ═══════════════════════════════════════════════════════════════
def build_pdf(
    output_path,
    report_date,
    spot_df,
    hist_batch,
    perf_data,
    vol_table,
    corr_matrix,
    risk_df,
    macro_df,
    summary_text,
    pair_analyses,
    charts,
):
    """
    Build the complete PDF report.

    Args:
        output_path: Path to save PDF
        report_date: datetime.date
        spot_df: DataFrame with spot rates
        hist_batch: dict[pair] -> DataFrame
        perf_data: dict[pair] -> performance dict
        vol_table: DataFrame with vol data
        corr_matrix: DataFrame correlation matrix
        risk_df: DataFrame with risk metrics
        macro_df: DataFrame with macro events
        summary_text: str executive summary
        pair_analyses: dict[pair] -> {commentary, trend_info, sr_levels}
        charts: dict of chart bytes keyed by name
    """
    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=config.MARGIN_LEFT,
        rightMargin=config.MARGIN_RIGHT,
        topMargin=config.MARGIN_TOP,
        bottomMargin=config.MARGIN_BOTTOM,
    )

    elements = []

    # ── Cover Page ──
    if config.SECTIONS.get("cover"):
        elements.extend(_build_cover(report_date, styles))

    # ── Executive Summary ──
    if config.SECTIONS.get("executive_summary"):
        elements.extend(_build_executive_summary(summary_text, styles))

    # ── Market Overview ──
    if config.SECTIONS.get("market_overview"):
        elements.extend(_build_market_overview(
            spot_df, perf_data, charts.get("performance_bars"), styles))

    # ── Multi-pair Overview ──
    if charts.get("multi_pair_grid"):
        available_w = PAGE_W - config.MARGIN_LEFT - config.MARGIN_RIGHT
        elements.append(Image(charts["multi_pair_grid"],
                             width=available_w, height=available_w * 0.85))
        elements.append(PageBreak())

    # ── Major Pairs Analysis ──
    if config.SECTIONS.get("major_pairs_analysis"):
        elements.append(Paragraph("3. Major Pairs Analysis", styles["SectionHeader"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))

        for pair in config.MAJOR_PAIRS:
            if pair in pair_analyses:
                pa = pair_analyses[pair]
                chart_key = f"price_{pair}"
                elems = _build_pair_analysis(
                    pair, pa["commentary"], charts.get(chart_key),
                    pa["trend_info"], pa["sr_levels"], styles
                )
                elements.extend(elems)

    elements.append(PageBreak())

    # ── EM Pairs Analysis ──
    if config.SECTIONS.get("em_pairs_analysis"):
        elements.append(Paragraph("4. Emerging Market Pairs Analysis", styles["SectionHeader"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=8))

        for pair in config.EM_PAIRS:
            if pair in pair_analyses:
                pa = pair_analyses[pair]
                chart_key = f"price_{pair}"
                elems = _build_pair_analysis(
                    pair, pa["commentary"], charts.get(chart_key),
                    pa["trend_info"], pa["sr_levels"], styles
                )
                elements.extend(elems)

    elements.append(PageBreak())

    # ── Volatility Analysis ──
    if config.SECTIONS.get("volatility_analysis"):
        elements.extend(_build_volatility_section(vol_table, charts.get("vol_bars"), styles))

    # ── Correlation Matrix ──
    if config.SECTIONS.get("correlation_matrix"):
        elements.extend(_build_correlation_section(charts.get("corr_heatmap"), styles))

    elements.append(PageBreak())

    # ── Macro Calendar ──
    if config.SECTIONS.get("macro_calendar"):
        elements.extend(_build_macro_calendar(macro_df, styles))

    # ── Risk Monitor ──
    if config.SECTIONS.get("risk_monitor"):
        elements.extend(_build_risk_monitor(risk_df, styles))

    # ── Disclaimer ──
    elements.extend(_build_disclaimer(styles))

    # Build PDF with different first page (cover) template
    doc.build(
        elements,
        onFirstPage=_draw_cover_bg,
        onLaterPages=_header_footer,
    )

    return output_path
