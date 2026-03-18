"""
Weekend Pricing Strategy Backtest
=================================

Analyze optimal weekend (Saturday 00:00~06:00 Beijing time) pricing strategy
for JPYCNH based on USDCNH reference data.

Strategy: Use USDCNH weekend price changes to adjust JPYCNH quotes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add project path
sys.path.insert(0, r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system")

# Output directory
OUTPUT_DIR = r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output"


def load_data():
    """Load JPYCNH and USDCNH data"""
    print("=" * 60)
    print("Loading Data")
    print("=" * 60)
    
    # JPYCNH - corrected data with proper Saturday hours
    jpycnh_file = os.path.join(OUTPUT_DIR, "JPYCNH_Curncy_bidask_1min_corrected_20260130_115938.xlsx")
    
    # USDCNH - original data with Saturday data
    usdcnh_file = os.path.join(OUTPUT_DIR, "USDCNH_Curncy_bidask_1s_20260116_144224.xlsx")
    
    print(f"\nLoading JPYCNH: {os.path.basename(jpycnh_file)}")
    df_jpycnh = pd.read_excel(jpycnh_file)
    df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
    df_jpycnh.set_index('timestamp', inplace=True)
    
    print(f"Loading USDCNH: {os.path.basename(usdcnh_file)}")
    df_usdcnh = pd.read_excel(usdcnh_file)
    df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
    df_usdcnh.set_index('timestamp', inplace=True)
    
    print(f"\nJPYCNH shape: {df_jpycnh.shape}")
    print(f"USDCNH shape: {df_usdcnh.shape}")
    
    return df_jpycnh, df_usdcnh


def analyze_weekend_data(df_jpycnh, df_usdcnh):
    """Analyze weekend data characteristics"""
    print("\n" + "=" * 60)
    print("Weekend Data Analysis")
    print("=" * 60)
    
    # Add weekday column
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_usdcnh['weekday'] = df_usdcnh.index.dayofweek
    
    # Filter Saturday data (Beijing time 00:00~06:00)
    jpycnh_sat = df_jpycnh[df_jpycnh['weekday'] == 5].copy()
    usdcnh_sat = df_usdcnh[df_usdcnh['weekday'] == 5].copy()
    
    print(f"\nJPYCNH Saturday rows: {len(jpycnh_sat)}")
    print(f"USDCNH Saturday rows: {len(usdcnh_sat)}")
    
    # Check hourly distribution
    print("\nJPYCNH Saturday hourly distribution:")
    jpycnh_sat['hour'] = jpycnh_sat.index.hour
    hour_counts = jpycnh_sat.groupby('hour').size()
    for hour, count in hour_counts.items():
        print(f"  {hour:02d}:00 - {count} rows")
    
    print("\nUSDCNH Saturday hourly distribution:")
    usdcnh_sat['hour'] = usdcnh_sat.index.hour
    hour_counts = usdcnh_sat.groupby('hour').size()
    for hour, count in hour_counts.items():
        print(f"  {hour:02d}:00 - {count} rows")
    
    return jpycnh_sat, usdcnh_sat


def calculate_weekend_metrics(df_jpycnh, df_usdcnh):
    """Calculate weekend trading metrics"""
    print("\n" + "=" * 60)
    print("Weekend Trading Metrics")
    print("=" * 60)
    
    # Add weekday and date
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_jpycnh['date'] = df_jpycnh.index.date
    df_usdcnh['weekday'] = df_usdcnh.index.dayofweek
    df_usdcnh['date'] = df_usdcnh.index.date
    
    # Get unique Saturday dates
    jpycnh_sat_dates = df_jpycnh[df_jpycnh['weekday'] == 5]['date'].unique()
    usdcnh_sat_dates = df_usdcnh[df_usdcnh['weekday'] == 5]['date'].unique()
    
    common_dates = sorted(set(jpycnh_sat_dates) & set(usdcnh_sat_dates))
    print(f"\nCommon Saturday dates: {len(common_dates)}")
    
    results = []
    
    for sat_date in common_dates:
        # Get Friday (day before Saturday)
        fri_date = sat_date - timedelta(days=1)
        
        # JPYCNH Saturday data
        jpycnh_sat = df_jpycnh[(df_jpycnh['date'] == sat_date) & (df_jpycnh.index.hour < 6)]
        
        # USDCNH Saturday data
        usdcnh_sat = df_usdcnh[(df_usdcnh['date'] == sat_date) & (df_usdcnh.index.hour < 6)]
        
        if jpycnh_sat.empty or usdcnh_sat.empty:
            continue
        
        # Calculate metrics
        jpycnh_open = jpycnh_sat['mid'].iloc[0] if 'mid' in jpycnh_sat.columns else (jpycnh_sat['bid'].iloc[0] + jpycnh_sat['ask'].iloc[0]) / 2
        jpycnh_close = jpycnh_sat['mid'].iloc[-1] if 'mid' in jpycnh_sat.columns else (jpycnh_sat['bid'].iloc[-1] + jpycnh_sat['ask'].iloc[-1]) / 2
        jpycnh_high = jpycnh_sat['mid'].max() if 'mid' in jpycnh_sat.columns else ((jpycnh_sat['bid'] + jpycnh_sat['ask']) / 2).max()
        jpycnh_low = jpycnh_sat['mid'].min() if 'mid' in jpycnh_sat.columns else ((jpycnh_sat['bid'] + jpycnh_sat['ask']) / 2).min()
        
        usdcnh_open = usdcnh_sat['mid'].iloc[0] if 'mid' in usdcnh_sat.columns else (usdcnh_sat['bid'].iloc[0] + usdcnh_sat['ask'].iloc[0]) / 2
        usdcnh_close = usdcnh_sat['mid'].iloc[-1] if 'mid' in usdcnh_sat.columns else (usdcnh_sat['bid'].iloc[-1] + usdcnh_sat['ask'].iloc[-1]) / 2
        usdcnh_high = usdcnh_sat['mid'].max() if 'mid' in usdcnh_sat.columns else ((usdcnh_sat['bid'] + usdcnh_sat['ask']) / 2).max()
        usdcnh_low = usdcnh_sat['mid'].min() if 'mid' in usdcnh_sat.columns else ((usdcnh_sat['bid'] + usdcnh_sat['ask']) / 2).min()
        
        # Calculate returns
        jpycnh_return = (jpycnh_close - jpycnh_open) / jpycnh_open * 10000  # in bps
        usdcnh_return = (usdcnh_close - usdcnh_open) / usdcnh_open * 10000  # in bps
        
        # Range
        jpycnh_range = (jpycnh_high - jpycnh_low) / jpycnh_open * 10000  # in bps
        usdcnh_range = (usdcnh_high - usdcnh_low) / usdcnh_open * 10000  # in bps
        
        results.append({
            'date': sat_date,
            'jpycnh_open': jpycnh_open,
            'jpycnh_close': jpycnh_close,
            'jpycnh_return_bps': jpycnh_return,
            'jpycnh_range_bps': jpycnh_range,
            'usdcnh_open': usdcnh_open,
            'usdcnh_close': usdcnh_close,
            'usdcnh_return_bps': usdcnh_return,
            'usdcnh_range_bps': usdcnh_range,
        })
    
    df_results = pd.DataFrame(results)
    
    if not df_results.empty:
        # Calculate correlation
        corr = df_results['jpycnh_return_bps'].corr(df_results['usdcnh_return_bps'])
        
        print(f"\nWeekend Trading Summary ({len(df_results)} Saturdays)")
        print("-" * 60)
        print(f"\nJPYCNH Weekend Stats:")
        print(f"  Avg Return: {df_results['jpycnh_return_bps'].mean():.2f} bps")
        print(f"  Std Return: {df_results['jpycnh_return_bps'].std():.2f} bps")
        print(f"  Avg Range:  {df_results['jpycnh_range_bps'].mean():.2f} bps")
        
        print(f"\nUSDCNH Weekend Stats:")
        print(f"  Avg Return: {df_results['usdcnh_return_bps'].mean():.2f} bps")
        print(f"  Std Return: {df_results['usdcnh_return_bps'].std():.2f} bps")
        print(f"  Avg Range:  {df_results['usdcnh_range_bps'].mean():.2f} bps")
        
        print(f"\nCorrelation (JPYCNH vs USDCNH returns): {corr:.4f}")
    
    return df_results


def backtest_pricing_strategy(df_jpycnh, df_usdcnh, spread_bps=5.0):
    """
    Backtest weekend pricing strategy
    
    Strategy: 
    - Use USDCNH movement as reference
    - Adjust JPYCNH quotes based on USDCNH changes
    - Earn spread when client trades against our quote
    
    Args:
        spread_bps: Our quoted spread in basis points
    """
    print("\n" + "=" * 60)
    print(f"Backtest: Weekend Pricing Strategy (spread={spread_bps} bps)")
    print("=" * 60)
    
    # Resample USDCNH to 1-minute to match JPYCNH
    df_usdcnh_1min = df_usdcnh.resample('1min').last().ffill()
    
    # Add columns
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_jpycnh['date'] = df_jpycnh.index.date
    df_usdcnh_1min['weekday'] = df_usdcnh_1min.index.dayofweek
    df_usdcnh_1min['date'] = df_usdcnh_1min.index.date
    
    # Calculate mid prices
    if 'mid' not in df_jpycnh.columns:
        df_jpycnh['mid'] = (df_jpycnh['bid'] + df_jpycnh['ask']) / 2
    if 'mid' not in df_usdcnh_1min.columns:
        df_usdcnh_1min['mid'] = (df_usdcnh_1min['bid'] + df_usdcnh_1min['ask']) / 2
    
    # Get Saturday data
    jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh.index.hour < 6)].copy()
    usdcnh_sat = df_usdcnh_1min[(df_usdcnh_1min['weekday'] == 5) & (df_usdcnh_1min.index.hour < 6)].copy()
    
    # Common timestamps
    common_idx = jpycnh_sat.index.intersection(usdcnh_sat.index)
    print(f"\nCommon timestamps: {len(common_idx)}")
    
    if len(common_idx) < 10:
        print("[Warning] Not enough common data points")
        return None
    
    # Calculate returns
    jpycnh_aligned = jpycnh_sat.loc[common_idx].copy()
    usdcnh_aligned = usdcnh_sat.loc[common_idx].copy()
    
    # Calculate minute-by-minute returns
    jpycnh_aligned['jpycnh_ret'] = jpycnh_aligned['mid'].pct_change() * 10000  # bps
    usdcnh_aligned['usdcnh_ret'] = usdcnh_aligned['mid'].pct_change() * 10000  # bps
    
    # Strategy parameters
    spread_half = spread_bps / 2  # Half spread on each side
    
    # Simulate different adjustment factors
    adjustment_factors = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    
    results = []
    
    for adj_factor in adjustment_factors:
        # Our quote adjustment based on USDCNH
        # adj_factor = 0: No adjustment (static quote)
        # adj_factor = 1: Full adjustment based on USDCNH movement
        
        pnl_total = 0
        trades = 0
        wins = 0
        
        for i in range(1, len(common_idx)):
            ts = common_idx[i]
            ts_prev = common_idx[i-1]
            
            # USDCNH movement
            usdcnh_move = usdcnh_aligned.loc[ts, 'usdcnh_ret']
            
            # Actual JPYCNH movement
            jpycnh_actual = jpycnh_aligned.loc[ts, 'jpycnh_ret']
            
            if pd.isna(usdcnh_move) or pd.isna(jpycnh_actual):
                continue
            
            # Our predicted JPYCNH movement (based on USDCNH)
            jpycnh_predicted = usdcnh_move * adj_factor
            
            # Client trades against us
            # If market moved up more than we predicted, we lose on our ask
            # If market moved down more than we predicted, we lose on our bid
            
            # Our quote error (market moved more/less than we predicted)
            quote_error = jpycnh_actual - jpycnh_predicted  # bps
            
            # PnL = spread earned - quote error
            # If error is within our spread, we still profit
            if abs(quote_error) < spread_half:
                pnl = spread_half  # We earn spread
                wins += 1
            else:
                pnl = spread_half - abs(quote_error)  # We lose the excess
            
            pnl_total += pnl
            trades += 1
        
        avg_pnl = pnl_total / trades if trades > 0 else 0
        win_rate = wins / trades if trades > 0 else 0
        
        results.append({
            'adj_factor': adj_factor,
            'trades': trades,
            'total_pnl_bps': pnl_total,
            'avg_pnl_bps': avg_pnl,
            'win_rate': win_rate,
        })
    
    df_results = pd.DataFrame(results)
    
    print("\nBacktest Results by Adjustment Factor:")
    print("-" * 70)
    print(f"{'Factor':<10} {'Trades':<10} {'Total PnL':<15} {'Avg PnL':<15} {'Win Rate':<10}")
    print("-" * 70)
    
    for _, row in df_results.iterrows():
        print(f"{row['adj_factor']:<10.2f} {row['trades']:<10.0f} {row['total_pnl_bps']:<15.2f} {row['avg_pnl_bps']:<15.4f} {row['win_rate']*100:<10.1f}%")
    
    # Best factor
    best_idx = df_results['total_pnl_bps'].idxmax()
    best = df_results.loc[best_idx]
    
    print("\n" + "=" * 60)
    print(f"BEST ADJUSTMENT FACTOR: {best['adj_factor']:.2f}")
    print(f"  Total PnL: {best['total_pnl_bps']:.2f} bps")
    print(f"  Avg PnL per trade: {best['avg_pnl_bps']:.4f} bps")
    print(f"  Win Rate: {best['win_rate']*100:.1f}%")
    print("=" * 60)
    
    return df_results


def analyze_intraday_patterns(df_jpycnh, df_usdcnh):
    """Analyze intraday patterns for optimization"""
    print("\n" + "=" * 60)
    print("Intraday Pattern Analysis")
    print("=" * 60)
    
    # Resample USDCNH to 1-minute
    df_usdcnh_1min = df_usdcnh.resample('1min').last().ffill()
    
    # Add columns
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_usdcnh_1min['weekday'] = df_usdcnh_1min.index.dayofweek
    
    # Calculate mid
    if 'mid' not in df_jpycnh.columns:
        df_jpycnh['mid'] = (df_jpycnh['bid'] + df_jpycnh['ask']) / 2
    if 'mid' not in df_usdcnh_1min.columns:
        df_usdcnh_1min['mid'] = (df_usdcnh_1min['bid'] + df_usdcnh_1min['ask']) / 2
    
    # Saturday data
    jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh.index.hour < 6)].copy()
    usdcnh_sat = df_usdcnh_1min[(df_usdcnh_1min['weekday'] == 5) & (df_usdcnh_1min.index.hour < 6)].copy()
    
    # Common timestamps
    common_idx = jpycnh_sat.index.intersection(usdcnh_sat.index)
    
    jpycnh_aligned = jpycnh_sat.loc[common_idx].copy()
    usdcnh_aligned = usdcnh_sat.loc[common_idx].copy()
    
    # Calculate returns
    jpycnh_aligned['jpycnh_ret'] = jpycnh_aligned['mid'].pct_change() * 10000
    usdcnh_aligned['usdcnh_ret'] = usdcnh_aligned['mid'].pct_change() * 10000
    
    # Analyze by hour
    jpycnh_aligned['hour'] = jpycnh_aligned.index.hour
    usdcnh_aligned['hour'] = usdcnh_aligned.index.hour
    
    print("\nCorrelation by Hour (Beijing time):")
    print("-" * 50)
    
    for hour in range(6):
        mask = jpycnh_aligned['hour'] == hour
        if mask.sum() > 10:
            corr = jpycnh_aligned.loc[mask, 'jpycnh_ret'].corr(usdcnh_aligned.loc[mask, 'usdcnh_ret'])
            jpycnh_vol = jpycnh_aligned.loc[mask, 'jpycnh_ret'].std()
            usdcnh_vol = usdcnh_aligned.loc[mask, 'usdcnh_ret'].std()
            print(f"  {hour:02d}:00 - Correlation: {corr:.4f}, JPYCNH Vol: {jpycnh_vol:.2f} bps, USDCNH Vol: {usdcnh_vol:.2f} bps")


def main():
    """Main backtest function"""
    print("\n" + "=" * 70)
    print("WEEKEND PRICING STRATEGY BACKTEST")
    print("=" * 70)
    
    # Load data
    df_jpycnh, df_usdcnh = load_data()
    
    # Analyze weekend data
    analyze_weekend_data(df_jpycnh, df_usdcnh)
    
    # Calculate metrics
    metrics = calculate_weekend_metrics(df_jpycnh, df_usdcnh)
    
    # Analyze intraday patterns
    analyze_intraday_patterns(df_jpycnh, df_usdcnh)
    
    # Run backtest with different spreads
    print("\n" + "=" * 70)
    print("BACKTEST WITH DIFFERENT SPREADS")
    print("=" * 70)
    
    for spread in [3.0, 5.0, 7.0, 10.0]:
        backtest_pricing_strategy(df_jpycnh, df_usdcnh, spread_bps=spread)
    
    print("\n" + "=" * 70)
    print("BACKTEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
