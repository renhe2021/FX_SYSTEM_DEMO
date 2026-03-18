"""
Weekend Pricing Analysis - USDCNH + JPYCNH (Final)
====================================================
Compare Friday closing price vs Saturday 00:00-06:00 best price
Calculate PnL in CNY

Key Finding:
- USDCNH: Has real price movement on Saturday 00:00-06:00 (NDF/offshore trading)
- JPYCNH: NO price movement on Saturday (market closed, static quotes)

Trading Volume:
- USDCNH: 60,000,000 USD per week
- JPYCNH: 4,000,000,000 JPY per week (NO BENEFIT from weekend optimization)
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
USDCNH_FILE = "USDCNH_Curncy_bidask_1s_20260116_144224.xlsx"

# Weekly trading volume
USDCNH_WEEKLY_VOLUME = 60_000_000  # 60M USD
JPYCNH_WEEKLY_VOLUME = 4_000_000_000  # 4B JPY (but no weekend optimization benefit)


def load_usdcnh_data():
    """Load USDCNH data file"""
    filepath = OUTPUT_DIR / USDCNH_FILE
    if not filepath.exists():
        print(f"  [ERROR] File not found: {USDCNH_FILE}")
        return None
    
    print(f"  Loading: {USDCNH_FILE}")
    df = pd.read_excel(filepath, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df


def analyze_usdcnh_weekend(df: pd.DataFrame):
    """
    Analyze USDCNH weekend pricing improvement
    
    Logic:
    - Old method: Use Friday closing ask price for weekend client pricing
    - New method: Use the BEST (highest) ask price during Saturday 00:00-06:00
    
    For SELL USD transactions (client buys USD):
    - We receive CNH, pay USD
    - Higher ask price = more CNH received per USD sold
    - PnL improvement = (new_ask - old_ask) * volume
    """
    print(f"\n{'='*60}")
    print(f"Analyzing USDCNH Weekend Pricing")
    print(f"Weekly Volume: {USDCNH_WEEKLY_VOLUME:,} USD")
    print(f"{'='*60}")
    
    # Filter Saturday 00:00-06:00 Beijing Time
    df = df.copy()
    df['weekday'] = df.index.dayofweek
    df['hour'] = df.index.hour
    
    saturday_data = df[(df['weekday'] == 5) & (df['hour'] < 6)].copy()
    print(f"\nSaturday 00:00-05:59 records: {len(saturday_data)}")
    
    if saturday_data.empty:
        print("[ERROR] No Saturday data")
        return None
    
    saturday_data['date'] = saturday_data.index.date
    
    results = []
    
    for sat_date in sorted(saturday_data['date'].unique()):
        week_data = saturday_data[saturday_data['date'] == sat_date]
        
        # Friday close price = first Saturday 00:00 price (last price before weekend)
        friday_close_ask = week_data['ask'].iloc[0]
        friday_close_bid = week_data['bid'].iloc[0]
        
        # Saturday best ask = highest ask during 00:00-06:00
        saturday_best_ask = week_data['ask'].max()
        saturday_best_bid = week_data['bid'].max()
        
        # Calculate improvement
        ask_improvement = saturday_best_ask - friday_close_ask
        improvement_pips = ask_improvement * 10000  # USDCNH: 1 pip = 0.0001
        
        # PnL for this week (only if improvement > 0)
        week_pnl = max(0, ask_improvement * USDCNH_WEEKLY_VOLUME)
        
        # Determine if new method is better
        new_better = ask_improvement > 0.00001
        
        results.append({
            'date': sat_date,
            'friday_close_ask': friday_close_ask,
            'saturday_best_ask': saturday_best_ask,
            'improvement': ask_improvement,
            'improvement_pips': improvement_pips,
            'new_better': new_better,
            'week_pnl_cny': week_pnl
        })
    
    results_df = pd.DataFrame(results)
    
    # Summary
    total_weeks = len(results_df)
    weeks_improved = results_df['new_better'].sum()
    pct_improved = weeks_improved / total_weeks * 100
    
    avg_improvement_pips = results_df[results_df['new_better']]['improvement_pips'].mean() if weeks_improved > 0 else 0
    max_improvement_pips = results_df['improvement_pips'].max()
    
    total_pnl = results_df['week_pnl_cny'].sum()
    annualized_pnl = total_pnl / total_weeks * 52
    
    print(f"\n--- Summary ---")
    print(f"Total weeks analyzed: {total_weeks}")
    print(f"Weeks with improvement: {weeks_improved} ({pct_improved:.1f}%)")
    print(f"Average improvement: {avg_improvement_pips:.2f} pips")
    print(f"Max improvement: {max_improvement_pips:.2f} pips")
    
    print(f"\n--- PnL (CNY) ---")
    print(f"Total PnL from {total_weeks} weeks: CNY {total_pnl:,.0f}")
    print(f"Annualized PnL estimate: CNY {annualized_pnl:,.0f}")
    
    return {
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
    print("Weekend Pricing Analysis - FINAL REPORT")
    print("=" * 70)
    
    print(f"\nWeekly Trading Volume:")
    print(f"  USDCNH: {USDCNH_WEEKLY_VOLUME:,} USD")
    print(f"  JPYCNH: {JPYCNH_WEEKLY_VOLUME:,} JPY")
    
    # Load and analyze USDCNH
    print("\n[1] Loading USDCNH data...")
    usdcnh_df = load_usdcnh_data()
    
    usdcnh_result = None
    if usdcnh_df is not None:
        usdcnh_result = analyze_usdcnh_weekend(usdcnh_df)
    
    # JPYCNH Analysis Note
    print("\n" + "=" * 60)
    print("JPYCNH Analysis")
    print("=" * 60)
    print("\n*** IMPORTANT FINDING ***")
    print("JPYCNH has NO price movement during Saturday 00:00-06:00")
    print("(Market is closed, quotes are static from Friday close)")
    print("Therefore, weekend pricing optimization does NOT benefit JPYCNH")
    print("\nJPYCNH Weekend Optimization PnL: CNY 0")
    
    # Final Summary
    print("\n")
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    if usdcnh_result:
        print(f"\nUSDCNH (60M USD/week):")
        print(f"  Weeks analyzed: {usdcnh_result['total_weeks']}")
        print(f"  Improvement rate: {usdcnh_result['pct_improved']:.1f}%")
        print(f"  Avg improvement: {usdcnh_result['avg_improvement_pips']:.2f} pips")
        print(f"  Max improvement: {usdcnh_result['max_improvement_pips']:.2f} pips")
        print(f"  Total PnL: CNY {usdcnh_result['total_pnl_cny']:,.0f}")
        print(f"  Annualized PnL: CNY {usdcnh_result['annualized_pnl_cny']:,.0f}")
    
    print(f"\nJPYCNH (4B JPY/week):")
    print(f"  Weekend optimization benefit: CNY 0")
    print(f"  Reason: No price movement on Saturday (market closed)")
    
    total_annualized = usdcnh_result['annualized_pnl_cny'] if usdcnh_result else 0
    
    print(f"\n{'='*50}")
    print(f"TOTAL ANNUALIZED PnL: CNY {total_annualized:,.0f}")
    print(f"{'='*50}")
    
    # Save results
    if usdcnh_result:
        output_file = OUTPUT_DIR / f"weekend_pricing_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Summary
            summary_data = {
                'Currency': ['USDCNH', 'JPYCNH', 'TOTAL'],
                'Weekly Volume': [f'{USDCNH_WEEKLY_VOLUME:,} USD', f'{JPYCNH_WEEKLY_VOLUME:,} JPY', '-'],
                'Weeks Analyzed': [usdcnh_result['total_weeks'], 20, '-'],
                'Improvement Rate': [f"{usdcnh_result['pct_improved']:.1f}%", '0% (no movement)', '-'],
                'Avg Improvement (pips)': [f"{usdcnh_result['avg_improvement_pips']:.2f}", 'N/A', '-'],
                'Max Improvement (pips)': [f"{usdcnh_result['max_improvement_pips']:.2f}", 'N/A', '-'],
                'Total PnL (CNY)': [f"{usdcnh_result['total_pnl_cny']:,.0f}", '0', f"{usdcnh_result['total_pnl_cny']:,.0f}"],
                'Annualized PnL (CNY)': [f"{usdcnh_result['annualized_pnl_cny']:,.0f}", '0', f"{total_annualized:,.0f}"]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # USDCNH Details
            usdcnh_result['details'].to_excel(writer, sheet_name='USDCNH_Details', index=False)
            
            # Notes
            notes_df = pd.DataFrame({
                'Note': [
                    'Analysis Period: Saturday 00:00-06:00 Beijing Time',
                    'USDCNH: Has real price movement (NDF/offshore trading active)',
                    'JPYCNH: NO price movement (market closed, static quotes)',
                    'PnL calculation: (Best Saturday Ask - Friday Close Ask) x Weekly Volume',
                    'Only SELL USD transactions considered (client buys USD)',
                ]
            })
            notes_df.to_excel(writer, sheet_name='Notes', index=False)
        
        print(f"\n[SAVED] Results saved to: {output_file.name}")
    
    return usdcnh_result


if __name__ == "__main__":
    main()
