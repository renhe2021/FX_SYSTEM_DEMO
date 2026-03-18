"""
Compare Reference Selection Strategies
======================================
Compare two reference selection methods:
- Strategy A: max(hour_0, hour_6) - use hour 0 or hour 6, whichever is larger
- Strategy B: max(hour_2, hour_6) - use hour 2 or hour 6, whichever is larger

This analyzes which reference point provides better pricing accuracy for JPYCNH.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Set font and style
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

try:
    plt.style.use('seaborn-v0_8-whitegrid')
except:
    plt.style.use('ggplot')

# Project path
sys.path.insert(0, r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system")
OUTPUT_DIR = r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output"

print("=" * 70)
print("Compare Reference Selection Strategies")
print("Strategy A: max(hour_0, hour_6)")
print("Strategy B: max(hour_2, hour_6)")
print("=" * 70)


def load_data():
    """Load JPYCNH and USDCNH data"""
    print("\n[1] Loading Data...")
    print("-" * 50)
    
    jpycnh_file = os.path.join(OUTPUT_DIR, "JPYCNH_Curncy_bidask_1min_corrected_20260130_115938.xlsx")
    usdcnh_file = os.path.join(OUTPUT_DIR, "USDCNH_Curncy_bidask_1s_20260116_144224.xlsx")
    
    print(f"Loading JPYCNH: {os.path.basename(jpycnh_file)}")
    df_jpycnh = pd.read_excel(jpycnh_file)
    df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
    df_jpycnh.set_index('timestamp', inplace=True)
    
    print(f"Loading USDCNH: {os.path.basename(usdcnh_file)}")
    df_usdcnh = pd.read_excel(usdcnh_file)
    df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
    df_usdcnh.set_index('timestamp', inplace=True)
    
    print(f"JPYCNH shape: {df_jpycnh.shape}")
    print(f"USDCNH shape: {df_usdcnh.shape}")
    
    return df_jpycnh, df_usdcnh


def prepare_hourly_data(df_jpycnh, df_usdcnh):
    """Prepare hourly aggregated data for Saturday"""
    print("\n[2] Preparing Hourly Data...")
    print("-" * 50)
    
    df_jpycnh = df_jpycnh.copy()
    df_usdcnh = df_usdcnh.copy()
    
    # Resample USDCNH to 1 minute
    df_usdcnh_1min = df_usdcnh.resample('1min').last().ffill()
    
    # Add columns
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_jpycnh['date'] = df_jpycnh.index.date
    df_jpycnh['hour'] = df_jpycnh.index.hour
    
    df_usdcnh_1min['weekday'] = df_usdcnh_1min.index.dayofweek
    df_usdcnh_1min['date'] = df_usdcnh_1min.index.date
    df_usdcnh_1min['hour'] = df_usdcnh_1min.index.hour
    
    # Calculate mid price
    if 'mid' not in df_jpycnh.columns:
        df_jpycnh['mid'] = (df_jpycnh['bid'] + df_jpycnh['ask']) / 2
    if 'mid' not in df_usdcnh_1min.columns:
        df_usdcnh_1min['mid'] = (df_usdcnh_1min['bid'] + df_usdcnh_1min['ask']) / 2
    
    # Filter Saturday data (hours 0-6)
    jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 6)].copy()
    usdcnh_sat = df_usdcnh_1min[(df_usdcnh_1min['weekday'] == 5) & (df_usdcnh_1min['hour'] <= 6)].copy()
    
    # Get unique Saturday dates
    jpycnh_dates = jpycnh_sat['date'].unique()
    usdcnh_dates = usdcnh_sat['date'].unique()
    common_dates = sorted(set(jpycnh_dates) & set(usdcnh_dates))
    
    print(f"Common Saturday dates: {len(common_dates)}")
    
    # Build hourly summary for each Saturday
    hourly_data = []
    
    for sat_date in common_dates:
        jpycnh_day = jpycnh_sat[jpycnh_sat['date'] == sat_date]
        usdcnh_day = usdcnh_sat[usdcnh_sat['date'] == sat_date]
        
        row = {'date': sat_date}
        
        for hour in [0, 2, 6]:
            # JPYCNH hourly data
            jpycnh_hour = jpycnh_day[jpycnh_day['hour'] == hour]
            if not jpycnh_hour.empty:
                row[f'jpycnh_mid_h{hour}'] = jpycnh_hour['mid'].mean()
                row[f'jpycnh_high_h{hour}'] = jpycnh_hour['mid'].max()
                row[f'jpycnh_low_h{hour}'] = jpycnh_hour['mid'].min()
            else:
                row[f'jpycnh_mid_h{hour}'] = np.nan
                row[f'jpycnh_high_h{hour}'] = np.nan
                row[f'jpycnh_low_h{hour}'] = np.nan
            
            # USDCNH hourly data
            usdcnh_hour = usdcnh_day[usdcnh_day['hour'] == hour]
            if not usdcnh_hour.empty:
                row[f'usdcnh_mid_h{hour}'] = usdcnh_hour['mid'].mean()
                row[f'usdcnh_high_h{hour}'] = usdcnh_hour['mid'].max()
                row[f'usdcnh_low_h{hour}'] = usdcnh_hour['mid'].min()
            else:
                row[f'usdcnh_mid_h{hour}'] = np.nan
                row[f'usdcnh_high_h{hour}'] = np.nan
                row[f'usdcnh_low_h{hour}'] = np.nan
        
        hourly_data.append(row)
    
    df_hourly = pd.DataFrame(hourly_data)
    print(f"Hourly data prepared: {len(df_hourly)} Saturdays")
    
    return df_hourly, jpycnh_sat, usdcnh_sat


def analyze_reference_strategies(df_hourly):
    """Analyze which reference strategy is better"""
    print("\n[3] Analyzing Reference Strategies...")
    print("-" * 50)
    
    df = df_hourly.copy()
    
    # Calculate returns from each hour
    # Return = (close - open) / open * 10000 (in bps)
    
    # For JPYCNH
    df['jpycnh_ret_0_6'] = (df['jpycnh_mid_h6'] - df['jpycnh_mid_h0']) / df['jpycnh_mid_h0'] * 10000
    df['jpycnh_ret_2_6'] = (df['jpycnh_mid_h6'] - df['jpycnh_mid_h2']) / df['jpycnh_mid_h2'] * 10000
    
    # For USDCNH
    df['usdcnh_ret_0_6'] = (df['usdcnh_mid_h6'] - df['usdcnh_mid_h0']) / df['usdcnh_mid_h0'] * 10000
    df['usdcnh_ret_2_6'] = (df['usdcnh_mid_h6'] - df['usdcnh_mid_h2']) / df['usdcnh_mid_h2'] * 10000
    
    # Strategy A: max(hour_0, hour_6) for USDCNH as reference
    # If USDCNH at hour 0 > hour 6, use hour 0 as reference; else use hour 6
    df['strategy_a_ref'] = np.where(df['usdcnh_mid_h0'] > df['usdcnh_mid_h6'], 'hour_0', 'hour_6')
    
    # Strategy B: max(hour_2, hour_6) for USDCNH as reference
    df['strategy_b_ref'] = np.where(df['usdcnh_mid_h2'] > df['usdcnh_mid_h6'], 'hour_2', 'hour_6')
    
    print("\nStrategy A (max of hour_0, hour_6) reference selection:")
    print(df['strategy_a_ref'].value_counts())
    
    print("\nStrategy B (max of hour_2, hour_6) reference selection:")
    print(df['strategy_b_ref'].value_counts())
    
    return df


def backtest_strategies(df_jpycnh, df_usdcnh, spread_bps=5.0):
    """
    Backtest both reference selection strategies
    
    Strategy A: Use USDCNH max(hour_0, hour_6) as pricing reference
    Strategy B: Use USDCNH max(hour_2, hour_6) as pricing reference
    """
    print(f"\n[4] Backtesting Strategies (spread={spread_bps} bps)...")
    print("-" * 50)
    
    df_jpycnh = df_jpycnh.copy()
    df_usdcnh = df_usdcnh.copy()
    
    # Resample USDCNH to 1 minute
    df_usdcnh_1min = df_usdcnh.resample('1min').last().ffill()
    
    # Add columns
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_jpycnh['date'] = df_jpycnh.index.date
    df_jpycnh['hour'] = df_jpycnh.index.hour
    
    df_usdcnh_1min['weekday'] = df_usdcnh_1min.index.dayofweek
    df_usdcnh_1min['date'] = df_usdcnh_1min.index.date
    df_usdcnh_1min['hour'] = df_usdcnh_1min.index.hour
    
    # Calculate mid price
    if 'mid' not in df_jpycnh.columns:
        df_jpycnh['mid'] = (df_jpycnh['bid'] + df_jpycnh['ask']) / 2
    if 'mid' not in df_usdcnh_1min.columns:
        df_usdcnh_1min['mid'] = (df_usdcnh_1min['bid'] + df_usdcnh_1min['ask']) / 2
    
    # Filter Saturday data
    jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 6)].copy()
    usdcnh_sat = df_usdcnh_1min[(df_usdcnh_1min['weekday'] == 5) & (df_usdcnh_1min['hour'] <= 6)].copy()
    
    # Get unique Saturday dates
    jpycnh_dates = jpycnh_sat['date'].unique()
    usdcnh_dates = usdcnh_sat['date'].unique()
    common_dates = sorted(set(jpycnh_dates) & set(usdcnh_dates))
    
    spread_half = spread_bps / 2
    
    # Test different adjustment factors
    adjustment_factors = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0]
    
    results_a = []
    results_b = []
    
    cumulative_pnl_a = {}
    cumulative_pnl_b = {}
    
    for adj_factor in adjustment_factors:
        # Strategy A results
        pnl_a_total = 0
        trades_a = 0
        wins_a = 0
        pnl_a_series = [0]
        
        # Strategy B results
        pnl_b_total = 0
        trades_b = 0
        wins_b = 0
        pnl_b_series = [0]
        
        for sat_date in common_dates:
            jpycnh_day = jpycnh_sat[jpycnh_sat['date'] == sat_date].copy()
            usdcnh_day = usdcnh_sat[usdcnh_sat['date'] == sat_date].copy()
            
            # Get hourly reference prices
            usdcnh_h0 = usdcnh_day[usdcnh_day['hour'] == 0]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 0]) > 0 else np.nan
            usdcnh_h2 = usdcnh_day[usdcnh_day['hour'] == 2]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 2]) > 0 else np.nan
            usdcnh_h6 = usdcnh_day[usdcnh_day['hour'] == 6]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 6]) > 0 else np.nan
            
            if pd.isna(usdcnh_h0) or pd.isna(usdcnh_h2) or pd.isna(usdcnh_h6):
                continue
            
            # Strategy A: Reference = max(hour_0, hour_6)
            ref_a = max(usdcnh_h0, usdcnh_h6)
            ref_a_change_bps = (usdcnh_h6 - ref_a) / ref_a * 10000 if ref_a != usdcnh_h6 else 0
            
            # Strategy B: Reference = max(hour_2, hour_6)
            ref_b = max(usdcnh_h2, usdcnh_h6)
            ref_b_change_bps = (usdcnh_h6 - ref_b) / ref_b * 10000 if ref_b != usdcnh_h6 else 0
            
            # Get minute-by-minute data for the day
            common_idx = jpycnh_day.index.intersection(usdcnh_day.index)
            
            if len(common_idx) < 10:
                continue
            
            jpycnh_aligned = jpycnh_day.loc[common_idx].copy()
            usdcnh_aligned = usdcnh_day.loc[common_idx].copy()
            
            jpycnh_aligned['jpycnh_ret'] = jpycnh_aligned['mid'].pct_change() * 10000
            usdcnh_aligned['usdcnh_ret'] = usdcnh_aligned['mid'].pct_change() * 10000
            
            for i in range(1, len(common_idx)):
                ts = common_idx[i]
                
                usdcnh_move = usdcnh_aligned.loc[ts, 'usdcnh_ret']
                jpycnh_actual = jpycnh_aligned.loc[ts, 'jpycnh_ret']
                
                if pd.isna(usdcnh_move) or pd.isna(jpycnh_actual):
                    continue
                
                # Strategy A prediction (adjusted by reference change)
                predicted_a = (usdcnh_move + ref_a_change_bps * 0.01) * adj_factor
                quote_error_a = jpycnh_actual - predicted_a
                
                if abs(quote_error_a) < spread_half:
                    pnl_a = spread_half
                    wins_a += 1
                else:
                    pnl_a = spread_half - abs(quote_error_a)
                
                pnl_a_total += pnl_a
                trades_a += 1
                pnl_a_series.append(pnl_a_total)
                
                # Strategy B prediction (adjusted by reference change)
                predicted_b = (usdcnh_move + ref_b_change_bps * 0.01) * adj_factor
                quote_error_b = jpycnh_actual - predicted_b
                
                if abs(quote_error_b) < spread_half:
                    pnl_b = spread_half
                    wins_b += 1
                else:
                    pnl_b = spread_half - abs(quote_error_b)
                
                pnl_b_total += pnl_b
                trades_b += 1
                pnl_b_series.append(pnl_b_total)
        
        avg_pnl_a = pnl_a_total / trades_a if trades_a > 0 else 0
        win_rate_a = wins_a / trades_a if trades_a > 0 else 0
        
        avg_pnl_b = pnl_b_total / trades_b if trades_b > 0 else 0
        win_rate_b = wins_b / trades_b if trades_b > 0 else 0
        
        results_a.append({
            'strategy': 'A: max(0,6)',
            'spread_bps': spread_bps,
            'adj_factor': adj_factor,
            'trades': trades_a,
            'total_pnl_bps': pnl_a_total,
            'avg_pnl_bps': avg_pnl_a,
            'win_rate': win_rate_a,
        })
        
        results_b.append({
            'strategy': 'B: max(2,6)',
            'spread_bps': spread_bps,
            'adj_factor': adj_factor,
            'trades': trades_b,
            'total_pnl_bps': pnl_b_total,
            'avg_pnl_bps': avg_pnl_b,
            'win_rate': win_rate_b,
        })
        
        cumulative_pnl_a[adj_factor] = pnl_a_series
        cumulative_pnl_b[adj_factor] = pnl_b_series
    
    df_results_a = pd.DataFrame(results_a)
    df_results_b = pd.DataFrame(results_b)
    
    return df_results_a, df_results_b, cumulative_pnl_a, cumulative_pnl_b


def plot_comparison(df_results_a, df_results_b, cumulative_pnl_a, cumulative_pnl_b, spread_bps):
    """Plot comparison of two strategies"""
    print(f"\n[5] Plotting Comparison (spread={spread_bps} bps)...")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Colors
    color_a = '#FF6B6B'  # Red for Strategy A
    color_b = '#4ECDC4'  # Teal for Strategy B
    
    # 1. Total PnL comparison
    ax1 = axes[0, 0]
    ax1.plot(df_results_a['adj_factor'], df_results_a['total_pnl_bps'], 
             marker='o', linewidth=2, markersize=8, color=color_a,
             label='Strategy A: max(0,6)')
    ax1.plot(df_results_b['adj_factor'], df_results_b['total_pnl_bps'], 
             marker='s', linewidth=2, markersize=8, color=color_b,
             label='Strategy B: max(2,6)')
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Adjustment Factor', fontsize=12)
    ax1.set_ylabel('Total PnL (bps)', fontsize=12)
    ax1.set_title(f'Total PnL Comparison (spread={spread_bps} bps)', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # 2. Win Rate comparison
    ax2 = axes[0, 1]
    ax2.plot(df_results_a['adj_factor'], df_results_a['win_rate'] * 100, 
             marker='o', linewidth=2, markersize=8, color=color_a,
             label='Strategy A: max(0,6)')
    ax2.plot(df_results_b['adj_factor'], df_results_b['win_rate'] * 100, 
             marker='s', linewidth=2, markersize=8, color=color_b,
             label='Strategy B: max(2,6)')
    ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')
    ax2.set_xlabel('Adjustment Factor', fontsize=12)
    ax2.set_ylabel('Win Rate (%)', fontsize=12)
    ax2.set_title('Win Rate Comparison', fontsize=14, fontweight='bold')
    ax2.legend(loc='best', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([80, 102])
    
    # 3. Cumulative PnL (best factor)
    ax3 = axes[1, 0]
    best_factor_a = df_results_a.loc[df_results_a['total_pnl_bps'].idxmax(), 'adj_factor']
    best_factor_b = df_results_b.loc[df_results_b['total_pnl_bps'].idxmax(), 'adj_factor']
    
    ax3.plot(cumulative_pnl_a[best_factor_a], linewidth=1.5, color=color_a,
             label=f'Strategy A (factor={best_factor_a})')
    ax3.plot(cumulative_pnl_b[best_factor_b], linewidth=1.5, color=color_b,
             label=f'Strategy B (factor={best_factor_b})')
    ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Trade Count', fontsize=12)
    ax3.set_ylabel('Cumulative PnL (bps)', fontsize=12)
    ax3.set_title('Cumulative PnL (Best Factors)', fontsize=14, fontweight='bold')
    ax3.legend(loc='best', fontsize=11)
    ax3.grid(True, alpha=0.3)
    
    # 4. PnL Difference (B - A)
    ax4 = axes[1, 1]
    pnl_diff = df_results_b['total_pnl_bps'].values - df_results_a['total_pnl_bps'].values
    colors_diff = ['green' if x > 0 else 'red' for x in pnl_diff]
    bars = ax4.bar(df_results_a['adj_factor'], pnl_diff, color=colors_diff, alpha=0.7, width=0.06)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax4.set_xlabel('Adjustment Factor', fontsize=12)
    ax4.set_ylabel('PnL Difference (B - A) in bps', fontsize=12)
    ax4.set_title('Strategy B vs A: PnL Difference\n(Green = B better, Red = A better)', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, val in zip(bars, pnl_diff):
        height = bar.get_height()
        ax4.annotate(f'{val:.0f}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3 if height > 0 else -12), textcoords='offset points',
                    ha='center', fontsize=9)
    
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, f'strategy_comparison_{int(spread_bps)}bps.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")
    
    return save_path


def print_summary(df_results_a, df_results_b, spread_bps):
    """Print summary comparison"""
    print("\n" + "=" * 70)
    print(f"STRATEGY COMPARISON SUMMARY (spread={spread_bps} bps)")
    print("=" * 70)
    
    # Best results for each strategy
    best_a = df_results_a.loc[df_results_a['total_pnl_bps'].idxmax()]
    best_b = df_results_b.loc[df_results_b['total_pnl_bps'].idxmax()]
    
    print("\n--- Strategy A: max(hour_0, hour_6) ---")
    print(f"  Best Adjustment Factor: {best_a['adj_factor']:.2f}")
    print(f"  Total PnL: {best_a['total_pnl_bps']:.2f} bps")
    print(f"  Avg PnL per trade: {best_a['avg_pnl_bps']:.4f} bps")
    print(f"  Win Rate: {best_a['win_rate']*100:.1f}%")
    
    print("\n--- Strategy B: max(hour_2, hour_6) ---")
    print(f"  Best Adjustment Factor: {best_b['adj_factor']:.2f}")
    print(f"  Total PnL: {best_b['total_pnl_bps']:.2f} bps")
    print(f"  Avg PnL per trade: {best_b['avg_pnl_bps']:.4f} bps")
    print(f"  Win Rate: {best_b['win_rate']*100:.1f}%")
    
    # Winner
    print("\n" + "=" * 70)
    if best_b['total_pnl_bps'] > best_a['total_pnl_bps']:
        diff = best_b['total_pnl_bps'] - best_a['total_pnl_bps']
        pct_better = diff / abs(best_a['total_pnl_bps']) * 100
        print(f"WINNER: Strategy B (max(2,6))")
        print(f"  B outperforms A by {diff:.2f} bps ({pct_better:.1f}% better)")
    else:
        diff = best_a['total_pnl_bps'] - best_b['total_pnl_bps']
        pct_better = diff / abs(best_b['total_pnl_bps']) * 100
        print(f"WINNER: Strategy A (max(0,6))")
        print(f"  A outperforms B by {diff:.2f} bps ({pct_better:.1f}% better)")
    print("=" * 70)
    
    return best_a, best_b


def main():
    """Main function"""
    # Load data
    df_jpycnh, df_usdcnh = load_data()
    
    # Prepare hourly data
    df_hourly, jpycnh_sat, usdcnh_sat = prepare_hourly_data(df_jpycnh, df_usdcnh)
    
    # Analyze reference strategies
    df_analysis = analyze_reference_strategies(df_hourly)
    
    # Test with different spreads
    spreads = [3.0, 5.0, 7.0, 10.0]
    all_results = []
    
    for spread in spreads:
        df_results_a, df_results_b, cum_pnl_a, cum_pnl_b = backtest_strategies(
            df_jpycnh, df_usdcnh, spread_bps=spread)
        
        # Plot comparison
        plot_comparison(df_results_a, df_results_b, cum_pnl_a, cum_pnl_b, spread)
        
        # Print summary
        best_a, best_b = print_summary(df_results_a, df_results_b, spread)
        
        all_results.append({
            'spread': spread,
            'strategy_a_pnl': best_a['total_pnl_bps'],
            'strategy_a_factor': best_a['adj_factor'],
            'strategy_a_winrate': best_a['win_rate'],
            'strategy_b_pnl': best_b['total_pnl_bps'],
            'strategy_b_factor': best_b['adj_factor'],
            'strategy_b_winrate': best_b['win_rate'],
            'winner': 'B' if best_b['total_pnl_bps'] > best_a['total_pnl_bps'] else 'A',
            'diff_bps': best_b['total_pnl_bps'] - best_a['total_pnl_bps']
        })
    
    # Final summary table
    print("\n" + "=" * 80)
    print("FINAL COMPARISON ACROSS ALL SPREADS")
    print("=" * 80)
    
    df_final = pd.DataFrame(all_results)
    print("\n")
    print(df_final.to_string(index=False))
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f'strategy_comparison_{timestamp}.xlsx')
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_final.to_excel(writer, sheet_name='Summary', index=False)
        df_analysis.to_excel(writer, sheet_name='Hourly_Analysis', index=False)
    
    print(f"\nResults saved to: {output_file}")
    
    # Overall winner
    a_wins = sum(1 for r in all_results if r['winner'] == 'A')
    b_wins = sum(1 for r in all_results if r['winner'] == 'B')
    
    print("\n" + "=" * 80)
    print("OVERALL CONCLUSION")
    print("=" * 80)
    print(f"\nStrategy A (max(0,6)) wins: {a_wins}/{len(spreads)}")
    print(f"Strategy B (max(2,6)) wins: {b_wins}/{len(spreads)}")
    
    if b_wins > a_wins:
        print("\n>>> RECOMMENDATION: Use Strategy B - max(hour_2, hour_6) <<<")
    elif a_wins > b_wins:
        print("\n>>> RECOMMENDATION: Use Strategy A - max(hour_0, hour_6) <<<")
    else:
        print("\n>>> RECOMMENDATION: Both strategies perform similarly <<<")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
