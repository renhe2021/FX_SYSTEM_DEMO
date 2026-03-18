"""
Weekend Pricing Analysis - Combined USDCNH + JPYCNH
====================================================
Compare Friday closing price vs Saturday 00:00-06:00 best price
Calculate PnL in CNY

Trading Volume:
- USDCNH: 60,000,000 USD per week
- JPYCNH: 4,000,000,000 JPY per week
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Data files
USDCNH_FILE = "USDCNH_Curncy_bidask_1s_20260116_144224.xlsx"  # Existing data
JPYCNH_FILE = "JPYCNH_Curncy_bidask_10s_weekly_20260130_100245.xlsx"  # New downloaded data

# Weekly trading volume
USDCNH_WEEKLY_VOLUME = 60_000_000  # 60M USD
JPYCNH_WEEKLY_VOLUME = 4_000_000_000  # 4B JPY


def load_data(filename: str) -> pd.DataFrame:
    """Load data file"""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        print(f"  [ERROR] File not found: {filename}")
        return None
    
    print(f"  Loading: {filename}")
    df = pd.read_excel(filepath, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df


def analyze_weekend_pricing(df: pd.DataFrame, symbol: str, weekly_volume: float, is_jpycnh: bool = False):
    """
    Analyze weekend pricing improvement
    
    For USDCNH:
        - Sell USD (client buys USD from us): we want higher ask price
        - Base currency is CNH, quote is per 1 USD
        
    For JPYCNH:
        - Sell JPY (client buys JPY from us): we want higher ask price
        - Base currency is CNH, quote is per 100 JPY typically
        
    Args:
        df: DataFrame with bid/ask data
        symbol: Currency pair name
        weekly_volume: Weekly trading volume
        is_jpycnh: True if analyzing JPYCNH
    """
    print(f"\n{'='*60}")
    print(f"Analyzing {symbol}")
    print(f"Weekly Volume: {weekly_volume:,.0f}")
    print(f"{'='*60}")
    
    # Filter Saturday 00:00-06:00 Beijing Time
    df['weekday'] = df.index.dayofweek
    df['hour'] = df.index.hour
    
    saturday_data = df[(df['weekday'] == 5) & (df['hour'] < 6)]
    print(f"\nSaturday 00:00-05:59 records: {len(saturday_data)}")
    
    if saturday_data.empty:
        print("[ERROR] No Saturday data")
        return None
    
    # Group by week (Saturday date)
    saturday_data = saturday_data.copy()
    saturday_data['date'] = saturday_data.index.date
    
    results = []
    
    for sat_date in saturday_data['date'].unique():
        week_data = saturday_data[saturday_data['date'] == sat_date]
        
        # Get Friday's last price (use first Saturday 00:00 as proxy for Friday close)
        friday_close_ask = week_data['ask'].iloc[0]
        friday_close_bid = week_data['bid'].iloc[0]
        
        # Saturday best ask (highest during 00:00-06:00)
        saturday_best_ask = week_data['ask'].max()
        saturday_best_bid = week_data['bid'].max()
        
        # Calculate improvement
        ask_improvement = saturday_best_ask - friday_close_ask
        
        results.append({
            'date': sat_date,
            'friday_close_ask': friday_close_ask,
            'friday_close_bid': friday_close_bid,
            'saturday_best_ask': saturday_best_ask,
            'saturday_best_bid': saturday_best_bid,
            'ask_improvement': ask_improvement,
            'improvement_pips': ask_improvement * (1000 if is_jpycnh else 10000),  # JPYCNH is quoted differently
            'new_better': ask_improvement > 0.00001  # Small threshold to account for floating point
        })
    
    results_df = pd.DataFrame(results)
    
    # Summary statistics
    total_weeks = len(results_df)
    weeks_improved = results_df['new_better'].sum()
    pct_improved = weeks_improved / total_weeks * 100
    
    avg_improvement_pips = results_df[results_df['new_better']]['improvement_pips'].mean() if weeks_improved > 0 else 0
    max_improvement_pips = results_df['improvement_pips'].max()
    
    print(f"\n--- Summary ---")
    print(f"Total weeks analyzed: {total_weeks}")
    print(f"Weeks with improvement: {weeks_improved} ({pct_improved:.1f}%)")
    print(f"Average improvement (when better): {avg_improvement_pips:.2f} pips")
    print(f"Max improvement: {max_improvement_pips:.2f} pips")
    
    # Calculate PnL
    # For sell transactions: higher ask = more CNY received per unit
    # PnL = improvement * volume
    
    if is_jpycnh:
        # JPYCNH is quoted as CNY per 100 JPY
        # If ask improves by X CNY/100JPY, for 4B JPY volume:
        # PnL = X * (4,000,000,000 / 100) = X * 40,000,000
        pnl_per_pip = weekly_volume / 100 / 1000  # 1 pip = 0.001 CNY/100JPY
    else:
        # USDCNH is quoted as CNY per 1 USD  
        # If ask improves by X CNY/USD, for 60M USD volume:
        # PnL = X * 60,000,000
        pnl_per_pip = weekly_volume / 10000  # 1 pip = 0.0001 CNY/USD
    
    # Total PnL (only for weeks with improvement)
    total_pnl = 0
    for _, row in results_df.iterrows():
        if row['new_better']:
            if is_jpycnh:
                # Direct calculation
                pnl = row['ask_improvement'] * (weekly_volume / 100)
            else:
                pnl = row['ask_improvement'] * weekly_volume
            total_pnl += pnl
    
    annualized_pnl = total_pnl / total_weeks * 52
    
    print(f"\n--- PnL (CNY) ---")
    print(f"Total PnL from {total_weeks} weeks: CNY {total_pnl:,.0f}")
    print(f"Annualized PnL estimate: CNY {annualized_pnl:,.0f}")
    
    return {
        'symbol': symbol,
        'total_weeks': total_weeks,
        'weeks_improved': weeks_improved,
        'pct_improved': pct_improved,
        'avg_improvement_pips': avg_improvement_pips,
        'max_improvement_pips': max_improvement_pips,
        'total_pnl_cny': total_pnl,
        'annualized_pnl_cny': annualized_pnl,
        'details': results_df
    }


def main():
    print("=" * 70)
    print("Weekend Pricing Analysis - USDCNH + JPYCNH")
    print("=" * 70)
    print(f"\nWeekly Trading Volume:")
    print(f"  USDCNH: {USDCNH_WEEKLY_VOLUME:,} USD")
    print(f"  JPYCNH: {JPYCNH_WEEKLY_VOLUME:,} JPY")
    
    # Load USDCNH data
    print("\n[1] Loading USDCNH data...")
    usdcnh_df = load_data(USDCNH_FILE)
    
    # Load JPYCNH data
    print("\n[2] Loading JPYCNH data...")
    jpycnh_df = load_data(JPYCNH_FILE)
    
    # Analyze USDCNH
    usdcnh_result = None
    if usdcnh_df is not None:
        usdcnh_result = analyze_weekend_pricing(
            usdcnh_df, "USDCNH", USDCNH_WEEKLY_VOLUME, is_jpycnh=False
        )
    
    # Analyze JPYCNH
    jpycnh_result = None
    if jpycnh_df is not None:
        jpycnh_result = analyze_weekend_pricing(
            jpycnh_df, "JPYCNH", JPYCNH_WEEKLY_VOLUME, is_jpycnh=True
        )
    
    # Combined Summary
    print("\n")
    print("=" * 70)
    print("COMBINED SUMMARY")
    print("=" * 70)
    
    total_pnl = 0
    total_annualized = 0
    
    if usdcnh_result:
        print(f"\nUSDCNH:")
        print(f"  Weeks analyzed: {usdcnh_result['total_weeks']}")
        print(f"  Improvement rate: {usdcnh_result['pct_improved']:.1f}%")
        print(f"  Total PnL: CNY {usdcnh_result['total_pnl_cny']:,.0f}")
        print(f"  Annualized PnL: CNY {usdcnh_result['annualized_pnl_cny']:,.0f}")
        total_pnl += usdcnh_result['total_pnl_cny']
        total_annualized += usdcnh_result['annualized_pnl_cny']
    
    if jpycnh_result:
        print(f"\nJPYCNH:")
        print(f"  Weeks analyzed: {jpycnh_result['total_weeks']}")
        print(f"  Improvement rate: {jpycnh_result['pct_improved']:.1f}%")
        print(f"  Total PnL: CNY {jpycnh_result['total_pnl_cny']:,.0f}")
        print(f"  Annualized PnL: CNY {jpycnh_result['annualized_pnl_cny']:,.0f}")
        total_pnl += jpycnh_result['total_pnl_cny']
        total_annualized += jpycnh_result['annualized_pnl_cny']
    
    print(f"\n{'='*50}")
    print(f"TOTAL COMBINED PnL: CNY {total_pnl:,.0f}")
    print(f"TOTAL ANNUALIZED PnL: CNY {total_annualized:,.0f}")
    print(f"{'='*50}")
    
    # Save results to Excel
    output_file = OUTPUT_DIR / f"weekend_pricing_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            'Metric': [
                'USDCNH Weekly Volume (USD)',
                'JPYCNH Weekly Volume (JPY)',
                'USDCNH Weeks Analyzed',
                'JPYCNH Weeks Analyzed',
                'USDCNH Improvement Rate (%)',
                'JPYCNH Improvement Rate (%)',
                'USDCNH Total PnL (CNY)',
                'JPYCNH Total PnL (CNY)',
                'USDCNH Annualized PnL (CNY)',
                'JPYCNH Annualized PnL (CNY)',
                'Total Combined PnL (CNY)',
                'Total Annualized PnL (CNY)'
            ],
            'Value': [
                USDCNH_WEEKLY_VOLUME,
                JPYCNH_WEEKLY_VOLUME,
                usdcnh_result['total_weeks'] if usdcnh_result else 0,
                jpycnh_result['total_weeks'] if jpycnh_result else 0,
                usdcnh_result['pct_improved'] if usdcnh_result else 0,
                jpycnh_result['pct_improved'] if jpycnh_result else 0,
                usdcnh_result['total_pnl_cny'] if usdcnh_result else 0,
                jpycnh_result['total_pnl_cny'] if jpycnh_result else 0,
                usdcnh_result['annualized_pnl_cny'] if usdcnh_result else 0,
                jpycnh_result['annualized_pnl_cny'] if jpycnh_result else 0,
                total_pnl,
                total_annualized
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        # Detail sheets
        if usdcnh_result:
            usdcnh_result['details'].to_excel(writer, sheet_name='USDCNH_Details', index=False)
        
        if jpycnh_result:
            jpycnh_result['details'].to_excel(writer, sheet_name='JPYCNH_Details', index=False)
    
    print(f"\n[SAVED] Results saved to: {output_file.name}")
    
    return usdcnh_result, jpycnh_result


if __name__ == "__main__":
    main()
