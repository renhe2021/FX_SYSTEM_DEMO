"""
FX Research Report Generator - Main Entry Point
Tenpay Global FX Research Report

Usage:
    python generate_report.py                     # Generate with today's date
    python generate_report.py --date 2026-02-26   # Specific date
    python generate_report.py --pairs USDCNY EURUSD USDJPY   # Specific pairs only
    python generate_report.py --no-em             # Skip EM pairs section
    python generate_report.py --output my_report.pdf  # Custom output name
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

import config
import data_fetcher
import analysis_engine
import chart_builder
import report_engine


def main():
    parser = argparse.ArgumentParser(description="Tenpay Global FX Research Report Generator")
    parser.add_argument("--date", type=str, default=None,
                        help="Report date (YYYY-MM-DD). Default: today")
    parser.add_argument("--pairs", nargs="+", default=None,
                        help="Specific currency pairs to analyze")
    parser.add_argument("--no-em", action="store_true",
                        help="Exclude EM pairs section")
    parser.add_argument("--no-major", action="store_true",
                        help="Exclude major pairs section")
    parser.add_argument("--days", type=int, default=90,
                        help="Historical lookback days (default: 90)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output PDF file path")
    args = parser.parse_args()

    # ── Resolve date ──
    if args.date:
        report_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        report_date = dt.date.today()

    print("=" * 56)
    print("   Tenpay Global - FX Research Report Generator")
    print("=" * 56)
    print(f"  Report Date : {report_date.strftime('%B %d, %Y')}")
    print(f"  Lookback    : {args.days} days")
    print("=" * 56)
    print()

    # ── Resolve pairs ──
    if args.pairs:
        pairs = [p.upper() for p in args.pairs]
    else:
        pairs = list(config.ALL_PAIRS)
        if args.no_em:
            pairs = [p for p in pairs if p in config.MAJOR_PAIRS]
        if args.no_major:
            pairs = [p for p in pairs if p in config.EM_PAIRS]

    major_pairs = [p for p in pairs if p in config.MAJOR_PAIRS]
    em_pairs = [p for p in pairs if p in config.EM_PAIRS]

    # ── Step 1: Fetch Data ──
    print("[1/6] Fetching spot rates...")
    spot_df = data_fetcher.get_spot_table(pairs)
    print(f"       > {len(spot_df)} pairs loaded")

    print("[2/6] Generating historical data...")
    hist_batch = data_fetcher.generate_historical_batch(pairs, days=args.days, end_date=report_date)
    print(f"       > {args.days}-day history for {len(hist_batch)} pairs")

    # ── Step 2: Compute Analytics ──
    print("[3/6] Running analysis engine...")

    # Add technical indicators
    for pair in hist_batch:
        hist_batch[pair] = analysis_engine.add_technical_indicators(hist_batch[pair])

    # Performance
    perf_data = {}
    for pair in pairs:
        perf_data[pair] = analysis_engine.compute_performance(hist_batch[pair])

    # Volatility
    vol_table = data_fetcher.compute_vol_table(hist_batch)

    # Correlation
    corr_matrix = data_fetcher.compute_correlation_matrix(hist_batch)

    # Risk metrics
    risk_df = data_fetcher.compute_risk_metrics(hist_batch)

    # Macro calendar
    macro_df = data_fetcher.get_macro_calendar(report_date)

    # Per-pair analysis
    pair_analyses = {}
    for pair in pairs:
        df = hist_batch[pair]
        trend_info = analysis_engine.assess_trend(df)
        sr_levels = analysis_engine.compute_support_resistance(df)
        perf = perf_data[pair]
        commentary = analysis_engine.generate_pair_commentary(pair, trend_info, perf, sr_levels)
        pair_analyses[pair] = {
            "trend_info": trend_info,
            "sr_levels": sr_levels,
            "commentary": commentary,
        }

    # Executive summary
    summary_text = analysis_engine.generate_executive_summary(spot_df, hist_batch, vol_table)
    print("       > Analysis complete")

    # ── Step 3: Generate Charts ──
    print("[4/6] Building charts...")
    charts = {}

    # Performance bars
    charts["performance_bars"] = chart_builder.chart_performance_bars(perf_data, period="1M")

    # Multi-pair grid
    charts["multi_pair_grid"] = chart_builder.chart_multi_pair_grid(hist_batch, pairs)

    # Per-pair price charts
    for pair in pairs:
        charts[f"price_{pair}"] = chart_builder.chart_price_with_indicators(hist_batch[pair], pair)

    # Volatility bars
    charts["vol_bars"] = chart_builder.chart_volatility_bars(vol_table)

    # Correlation heatmap
    charts["corr_heatmap"] = chart_builder.chart_correlation_heatmap(corr_matrix)

    print(f"       > {len(charts)} charts generated")

    # ── Step 4: Build PDF ──
    print("[5/6] Building PDF report...")

    # Update config sections based on args
    if args.no_em:
        config.SECTIONS["em_pairs_analysis"] = False
    if args.no_major:
        config.SECTIONS["major_pairs_analysis"] = False

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = output_dir / f"FX_Report_{report_date.strftime('%Y%m%d')}.pdf"

    report_engine.build_pdf(
        output_path=output_path,
        report_date=report_date,
        spot_df=spot_df,
        hist_batch=hist_batch,
        perf_data=perf_data,
        vol_table=vol_table,
        corr_matrix=corr_matrix,
        risk_df=risk_df,
        macro_df=macro_df,
        summary_text=summary_text,
        pair_analyses=pair_analyses,
        charts=charts,
    )

    print(f"       PDF saved")
    print()
    print(f"[6/6] Done!")
    print(f"       Report: {output_path.resolve()}")
    print()


if __name__ == "__main__":
    main()
