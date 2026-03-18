"""
Weekend Pricing Strategy Backtest Analysis with Visualization
=============================================================
Analyze JPYCNH weekend (Saturday 00:00~06:00 Beijing time) pricing strategy
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import matplotlib.pyplot as plt
import matplotlib
import warnings
warnings.filterwarnings('ignore')

# Set font
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Set plot style
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except:
    plt.style.use('ggplot')

# Project path
sys.path.insert(0, r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system")
OUTPUT_DIR = r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output"

print("=" * 70)
print("Weekend Pricing Strategy Backtest Analysis")
print("=" * 70)


def load_data():
    """Load JPYCNH and USDCNH data"""
    print("\n[1] Loading Data")
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
    
    print(f"\nJPYCNH shape: {df_jpycnh.shape}")
    print(f"USDCNH shape: {df_usdcnh.shape}")
    
    return df_jpycnh, df_usdcnh


def calculate_weekend_metrics(df_jpycnh, df_usdcnh):
    """Calculate weekend trading metrics"""
    print("\n[2] Weekend Trading Metrics")
    print("-" * 50)
    
    df_jpycnh = df_jpycnh.copy()
    df_usdcnh = df_usdcnh.copy()
    
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_jpycnh['date'] = df_jpycnh.index.date
    df_usdcnh['weekday'] = df_usdcnh.index.dayofweek
    df_usdcnh['date'] = df_usdcnh.index.date
    
    jpycnh_sat_dates = df_jpycnh[df_jpycnh['weekday'] == 5]['date'].unique()
    usdcnh_sat_dates = df_usdcnh[df_usdcnh['weekday'] == 5]['date'].unique()
    
    common_dates = sorted(set(jpycnh_sat_dates) & set(usdcnh_sat_dates))
    print(f"Common Saturday dates: {len(common_dates)}")
    
    results = []
    
    for sat_date in common_dates:
        jpycnh_sat = df_jpycnh[(df_jpycnh['date'] == sat_date) & (df_jpycnh.index.hour < 6)]
        usdcnh_sat = df_usdcnh[(df_usdcnh['date'] == sat_date) & (df_usdcnh.index.hour < 6)]
        
        if jpycnh_sat.empty or usdcnh_sat.empty:
            continue
        
        jpycnh_open = jpycnh_sat['mid'].iloc[0] if 'mid' in jpycnh_sat.columns else (jpycnh_sat['bid'].iloc[0] + jpycnh_sat['ask'].iloc[0]) / 2
        jpycnh_close = jpycnh_sat['mid'].iloc[-1] if 'mid' in jpycnh_sat.columns else (jpycnh_sat['bid'].iloc[-1] + jpycnh_sat['ask'].iloc[-1]) / 2
        jpycnh_high = jpycnh_sat['mid'].max() if 'mid' in jpycnh_sat.columns else ((jpycnh_sat['bid'] + jpycnh_sat['ask']) / 2).max()
        jpycnh_low = jpycnh_sat['mid'].min() if 'mid' in jpycnh_sat.columns else ((jpycnh_sat['bid'] + jpycnh_sat['ask']) / 2).min()
        
        usdcnh_open = usdcnh_sat['mid'].iloc[0] if 'mid' in usdcnh_sat.columns else (usdcnh_sat['bid'].iloc[0] + usdcnh_sat['ask'].iloc[0]) / 2
        usdcnh_close = usdcnh_sat['mid'].iloc[-1] if 'mid' in usdcnh_sat.columns else (usdcnh_sat['bid'].iloc[-1] + usdcnh_sat['ask'].iloc[-1]) / 2
        usdcnh_high = usdcnh_sat['mid'].max() if 'mid' in usdcnh_sat.columns else ((usdcnh_sat['bid'] + usdcnh_sat['ask']) / 2).max()
        usdcnh_low = usdcnh_sat['mid'].min() if 'mid' in usdcnh_sat.columns else ((usdcnh_sat['bid'] + usdcnh_sat['ask']) / 2).min()
        
        jpycnh_return = (jpycnh_close - jpycnh_open) / jpycnh_open * 10000
        usdcnh_return = (usdcnh_close - usdcnh_open) / usdcnh_open * 10000
        
        jpycnh_range = (jpycnh_high - jpycnh_low) / jpycnh_open * 10000
        usdcnh_range = (usdcnh_high - usdcnh_low) / usdcnh_open * 10000
        
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
        corr = df_results['jpycnh_return_bps'].corr(df_results['usdcnh_return_bps'])
        
        print(f"\nWeekend Trading Summary ({len(df_results)} Saturdays)")
        print(f"\nJPYCNH Stats:")
        print(f"  Avg Return: {df_results['jpycnh_return_bps'].mean():.2f} bps")
        print(f"  Std Return: {df_results['jpycnh_return_bps'].std():.2f} bps")
        print(f"  Avg Range:  {df_results['jpycnh_range_bps'].mean():.2f} bps")
        
        print(f"\nUSDCNH Stats:")
        print(f"  Avg Return: {df_results['usdcnh_return_bps'].mean():.2f} bps")
        print(f"  Std Return: {df_results['usdcnh_return_bps'].std():.2f} bps")
        print(f"  Avg Range:  {df_results['usdcnh_range_bps'].mean():.2f} bps")
        
        print(f"\nCorrelation (JPYCNH vs USDCNH returns): {corr:.4f}")
    
    return df_results


def backtest_pricing_strategy(df_jpycnh, df_usdcnh, spread_bps=5.0):
    """Backtest weekend pricing strategy"""
    df_jpycnh = df_jpycnh.copy()
    df_usdcnh = df_usdcnh.copy()
    
    df_usdcnh_1min = df_usdcnh.resample('1min').last().ffill()
    
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_jpycnh['date'] = df_jpycnh.index.date
    df_usdcnh_1min['weekday'] = df_usdcnh_1min.index.dayofweek
    df_usdcnh_1min['date'] = df_usdcnh_1min.index.date
    
    if 'mid' not in df_jpycnh.columns:
        df_jpycnh['mid'] = (df_jpycnh['bid'] + df_jpycnh['ask']) / 2
    if 'mid' not in df_usdcnh_1min.columns:
        df_usdcnh_1min['mid'] = (df_usdcnh_1min['bid'] + df_usdcnh_1min['ask']) / 2
    
    jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh.index.hour < 6)].copy()
    usdcnh_sat = df_usdcnh_1min[(df_usdcnh_1min['weekday'] == 5) & (df_usdcnh_1min.index.hour < 6)].copy()
    
    common_idx = jpycnh_sat.index.intersection(usdcnh_sat.index)
    
    if len(common_idx) < 10:
        return None, None, None
    
    jpycnh_aligned = jpycnh_sat.loc[common_idx].copy()
    usdcnh_aligned = usdcnh_sat.loc[common_idx].copy()
    
    jpycnh_aligned['jpycnh_ret'] = jpycnh_aligned['mid'].pct_change() * 10000
    usdcnh_aligned['usdcnh_ret'] = usdcnh_aligned['mid'].pct_change() * 10000
    
    spread_half = spread_bps / 2
    
    adjustment_factors = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5]
    
    results = []
    cumulative_pnl = {}
    
    for adj_factor in adjustment_factors:
        pnl_total = 0
        trades = 0
        wins = 0
        pnl_series = [0]
        
        for i in range(1, len(common_idx)):
            ts = common_idx[i]
            
            usdcnh_move = usdcnh_aligned.loc[ts, 'usdcnh_ret']
            jpycnh_actual = jpycnh_aligned.loc[ts, 'jpycnh_ret']
            
            if pd.isna(usdcnh_move) or pd.isna(jpycnh_actual):
                pnl_series.append(pnl_series[-1])
                continue
            
            jpycnh_predicted = usdcnh_move * adj_factor
            quote_error = jpycnh_actual - jpycnh_predicted
            
            if abs(quote_error) < spread_half:
                pnl = spread_half
                wins += 1
            else:
                pnl = spread_half - abs(quote_error)
            
            pnl_total += pnl
            trades += 1
            pnl_series.append(pnl_total)
        
        avg_pnl = pnl_total / trades if trades > 0 else 0
        win_rate = wins / trades if trades > 0 else 0
        
        results.append({
            'spread_bps': spread_bps,
            'adj_factor': adj_factor,
            'trades': trades,
            'total_pnl_bps': pnl_total,
            'avg_pnl_bps': avg_pnl,
            'win_rate': win_rate,
        })
        cumulative_pnl[adj_factor] = pnl_series
    
    return pd.DataFrame(results), cumulative_pnl, common_idx


def analyze_hourly_patterns(df_jpycnh, df_usdcnh):
    """Analyze hourly correlation and volatility"""
    df_jpycnh = df_jpycnh.copy()
    df_usdcnh = df_usdcnh.copy()
    
    df_usdcnh_1min = df_usdcnh.resample('1min').last().ffill()
    
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_usdcnh_1min['weekday'] = df_usdcnh_1min.index.dayofweek
    
    if 'mid' not in df_jpycnh.columns:
        df_jpycnh['mid'] = (df_jpycnh['bid'] + df_jpycnh['ask']) / 2
    if 'mid' not in df_usdcnh_1min.columns:
        df_usdcnh_1min['mid'] = (df_usdcnh_1min['bid'] + df_usdcnh_1min['ask']) / 2
    
    jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh.index.hour < 6)].copy()
    usdcnh_sat = df_usdcnh_1min[(df_usdcnh_1min['weekday'] == 5) & (df_usdcnh_1min.index.hour < 6)].copy()
    
    common_idx = jpycnh_sat.index.intersection(usdcnh_sat.index)
    
    jpycnh_aligned = jpycnh_sat.loc[common_idx].copy()
    usdcnh_aligned = usdcnh_sat.loc[common_idx].copy()
    
    jpycnh_aligned['jpycnh_ret'] = jpycnh_aligned['mid'].pct_change() * 10000
    usdcnh_aligned['usdcnh_ret'] = usdcnh_aligned['mid'].pct_change() * 10000
    
    jpycnh_aligned['hour'] = jpycnh_aligned.index.hour
    usdcnh_aligned['hour'] = usdcnh_aligned.index.hour
    
    hourly_stats = []
    for hour in range(6):
        mask = jpycnh_aligned['hour'] == hour
        if mask.sum() > 10:
            corr = jpycnh_aligned.loc[mask, 'jpycnh_ret'].corr(usdcnh_aligned.loc[mask, 'usdcnh_ret'])
            jpycnh_vol = jpycnh_aligned.loc[mask, 'jpycnh_ret'].std()
            usdcnh_vol = usdcnh_aligned.loc[mask, 'usdcnh_ret'].std()
            hourly_stats.append({
                'hour': hour,
                'correlation': corr,
                'jpycnh_vol': jpycnh_vol,
                'usdcnh_vol': usdcnh_vol,
                'data_points': mask.sum()
            })
    
    return pd.DataFrame(hourly_stats)


def plot_returns_analysis(metrics_df):
    """Plot weekend returns analysis"""
    print("\n[3] Plotting Returns Analysis...")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. JPYCNH vs USDCNH scatter plot
    ax1 = axes[0, 0]
    ax1.scatter(metrics_df['usdcnh_return_bps'], metrics_df['jpycnh_return_bps'], 
                alpha=0.7, s=80, c='steelblue', edgecolors='white', linewidth=0.5)
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    corr = metrics_df['jpycnh_return_bps'].corr(metrics_df['usdcnh_return_bps'])
    ax1.set_xlabel('USDCNH Weekend Return (bps)', fontsize=12)
    ax1.set_ylabel('JPYCNH Weekend Return (bps)', fontsize=12)
    ax1.set_title(f'JPYCNH vs USDCNH Weekend Returns\nCorrelation: {corr:.4f}', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Add trend line
    z = np.polyfit(metrics_df['usdcnh_return_bps'], metrics_df['jpycnh_return_bps'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(metrics_df['usdcnh_return_bps'].min(), metrics_df['usdcnh_return_bps'].max(), 100)
    ax1.plot(x_line, p(x_line), 'r--', alpha=0.8, label=f'Trend (slope={z[0]:.3f})')
    ax1.legend()
    
    # 2. JPYCNH return distribution
    ax2 = axes[0, 1]
    ax2.hist(metrics_df['jpycnh_return_bps'], bins=20, color='coral', alpha=0.7, edgecolor='white')
    ax2.axvline(x=metrics_df['jpycnh_return_bps'].mean(), color='red', linestyle='--', 
                label=f'Mean: {metrics_df["jpycnh_return_bps"].mean():.2f}', linewidth=2)
    ax2.axvline(x=0, color='black', linestyle='-', alpha=0.5)
    ax2.set_xlabel('Return (bps)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_title('JPYCNH Weekend Return Distribution', fontsize=14, fontweight='bold')
    ax2.legend()
    
    # 3. USDCNH return distribution
    ax3 = axes[1, 0]
    ax3.hist(metrics_df['usdcnh_return_bps'], bins=20, color='lightseagreen', alpha=0.7, edgecolor='white')
    ax3.axvline(x=metrics_df['usdcnh_return_bps'].mean(), color='darkgreen', linestyle='--', 
                label=f'Mean: {metrics_df["usdcnh_return_bps"].mean():.2f}', linewidth=2)
    ax3.axvline(x=0, color='black', linestyle='-', alpha=0.5)
    ax3.set_xlabel('Return (bps)', fontsize=12)
    ax3.set_ylabel('Frequency', fontsize=12)
    ax3.set_title('USDCNH Weekend Return Distribution', fontsize=14, fontweight='bold')
    ax3.legend()
    
    # 4. Volatility range comparison
    ax4 = axes[1, 1]
    x = np.arange(len(metrics_df))
    width = 0.35
    ax4.bar(x - width/2, metrics_df['jpycnh_range_bps'], width, label='JPYCNH', color='coral', alpha=0.8)
    ax4.bar(x + width/2, metrics_df['usdcnh_range_bps'], width, label='USDCNH', color='lightseagreen', alpha=0.8)
    ax4.set_xlabel('Saturday Index', fontsize=12)
    ax4.set_ylabel('Range (bps)', fontsize=12)
    ax4.set_title('Weekend Volatility Range Comparison', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.axhline(y=metrics_df['jpycnh_range_bps'].mean(), color='coral', linestyle='--', alpha=0.5)
    ax4.axhline(y=metrics_df['usdcnh_range_bps'].mean(), color='lightseagreen', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, 'weekend_returns_analysis.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


def plot_backtest_results(all_results_df, all_cumulative_pnl, spreads):
    """Plot backtest results"""
    print("\n[4] Plotting Backtest Results...")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    colors = {'3.0': '#FF6B6B', '5.0': '#4ECDC4', '7.0': '#45B7D1', '10.0': '#96C93D'}
    
    # 1. Total PnL by spread
    ax1 = axes[0, 0]
    for spread in spreads:
        df_spread = all_results_df[all_results_df['spread_bps'] == spread]
        ax1.plot(df_spread['adj_factor'], df_spread['total_pnl_bps'], 
                 marker='o', linewidth=2, markersize=6,
                 label=f'{spread:.0f} bps spread', color=colors[str(spread)])
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Adjustment Factor', fontsize=12)
    ax1.set_ylabel('Total PnL (bps)', fontsize=12)
    ax1.set_title('Total PnL by Spread Level', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 2. Win rate comparison
    ax2 = axes[0, 1]
    for spread in spreads:
        df_spread = all_results_df[all_results_df['spread_bps'] == spread]
        ax2.plot(df_spread['adj_factor'], df_spread['win_rate'] * 100, 
                 marker='s', linewidth=2, markersize=6,
                 label=f'{spread:.0f} bps spread', color=colors[str(spread)])
    ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')
    ax2.set_xlabel('Adjustment Factor', fontsize=12)
    ax2.set_ylabel('Win Rate (%)', fontsize=12)
    ax2.set_title('Win Rate by Spread Level', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 105])
    
    # 3. Cumulative PnL (5 bps spread)
    ax3 = axes[1, 0]
    cum_pnl_5bps = all_cumulative_pnl.get(5.0, {})
    selected_factors = [0.0, 0.25, 0.5, 1.0]
    for factor in selected_factors:
        if factor in cum_pnl_5bps:
            ax3.plot(cum_pnl_5bps[factor], linewidth=1.5, label=f'Factor={factor}')
    ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Trade Count', fontsize=12)
    ax3.set_ylabel('Cumulative PnL (bps)', fontsize=12)
    ax3.set_title('Cumulative PnL (5 bps spread)', fontsize=14, fontweight='bold')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)
    
    # 4. Optimal factor comparison
    ax4 = axes[1, 1]
    best_factors = []
    best_pnls = []
    best_winrates = []
    
    for spread in spreads:
        df_spread = all_results_df[all_results_df['spread_bps'] == spread]
        best_idx = df_spread['total_pnl_bps'].idxmax()
        best = df_spread.loc[best_idx]
        best_factors.append(best['adj_factor'])
        best_pnls.append(best['total_pnl_bps'])
        best_winrates.append(best['win_rate'] * 100)
    
    x = np.arange(len(spreads))
    width = 0.35
    
    bars1 = ax4.bar(x - width/2, best_factors, width, label='Best Factor', color='steelblue', alpha=0.8)
    ax4_twin = ax4.twinx()
    bars2 = ax4_twin.bar(x + width/2, best_winrates, width, label='Win Rate (%)', color='coral', alpha=0.8)
    
    ax4.set_xlabel('Spread (bps)', fontsize=12)
    ax4.set_ylabel('Best Adjustment Factor', fontsize=12, color='steelblue')
    ax4_twin.set_ylabel('Win Rate (%)', fontsize=12, color='coral')
    ax4.set_xticks(x)
    ax4.set_xticklabels([f'{s:.0f}' for s in spreads])
    ax4.set_title('Optimal Parameters by Spread', fontsize=14, fontweight='bold')
    
    for i, (f, w) in enumerate(zip(best_factors, best_winrates)):
        ax4.annotate(f'{f:.2f}', (x[i] - width/2, f + 0.02), ha='center', fontsize=10)
        ax4_twin.annotate(f'{w:.1f}%', (x[i] + width/2, w + 1), ha='center', fontsize=10)
    
    ax4.legend(loc='upper left')
    ax4_twin.legend(loc='upper right')
    
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, 'backtest_results.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


def plot_hourly_analysis(hourly_df):
    """Plot hourly analysis"""
    print("\n[5] Plotting Hourly Analysis...")
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # 1. Hourly correlation
    ax1 = axes[0]
    bars = ax1.bar(hourly_df['hour'], hourly_df['correlation'], color='steelblue', alpha=0.8, edgecolor='white')
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Hour (Beijing Time)', fontsize=12)
    ax1.set_ylabel('Correlation', fontsize=12)
    ax1.set_title('JPYCNH vs USDCNH Hourly Correlation', fontsize=14, fontweight='bold')
    ax1.set_xticks(hourly_df['hour'])
    ax1.set_xticklabels([f'{h:02d}:00' for h in hourly_df['hour']])
    
    for bar, corr in zip(bars, hourly_df['correlation']):
        height = bar.get_height()
        ax1.annotate(f'{corr:.3f}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)
    
    # 2. Hourly volatility
    ax2 = axes[1]
    x = np.arange(len(hourly_df))
    width = 0.35
    ax2.bar(x - width/2, hourly_df['jpycnh_vol'], width, label='JPYCNH', color='coral', alpha=0.8)
    ax2.bar(x + width/2, hourly_df['usdcnh_vol'], width, label='USDCNH', color='lightseagreen', alpha=0.8)
    ax2.set_xlabel('Hour (Beijing Time)', fontsize=12)
    ax2.set_ylabel('Volatility (bps)', fontsize=12)
    ax2.set_title('Hourly Volatility Comparison', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([f'{h:02d}:00' for h in hourly_df['hour']])
    ax2.legend()
    
    # 3. Data points count
    ax3 = axes[2]
    ax3.bar(hourly_df['hour'], hourly_df['data_points'], color='mediumpurple', alpha=0.8, edgecolor='white')
    ax3.set_xlabel('Hour (Beijing Time)', fontsize=12)
    ax3.set_ylabel('Data Points', fontsize=12)
    ax3.set_title('Data Points per Hour', fontsize=14, fontweight='bold')
    ax3.set_xticks(hourly_df['hour'])
    ax3.set_xticklabels([f'{h:02d}:00' for h in hourly_df['hour']])
    
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, 'hourly_analysis.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


def main():
    """Main function"""
    # Load data
    df_jpycnh, df_usdcnh = load_data()
    
    # Calculate weekend metrics
    metrics_df = calculate_weekend_metrics(df_jpycnh, df_usdcnh)
    
    # Plot returns analysis
    if not metrics_df.empty:
        plot_returns_analysis(metrics_df)
    
    # Run backtest
    print("\n[6] Running Backtest...")
    print("-" * 50)
    
    spreads = [3.0, 5.0, 7.0, 10.0]
    all_results = []
    all_cumulative_pnl = {}
    
    for spread in spreads:
        print(f"Testing spread = {spread} bps...")
        result, cum_pnl, common_idx = backtest_pricing_strategy(df_jpycnh, df_usdcnh, spread_bps=spread)
        if result is not None:
            all_results.append(result)
            all_cumulative_pnl[spread] = cum_pnl
    
    all_results_df = pd.concat(all_results, ignore_index=True)
    
    # Plot backtest results
    plot_backtest_results(all_results_df, all_cumulative_pnl, spreads)
    
    # Analyze hourly patterns
    hourly_df = analyze_hourly_patterns(df_jpycnh, df_usdcnh)
    if not hourly_df.empty:
        plot_hourly_analysis(hourly_df)
    
    # Output summary
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 70)
    
    for spread in spreads:
        df_spread = all_results_df[all_results_df['spread_bps'] == spread]
        best_idx = df_spread['total_pnl_bps'].idxmax()
        best = df_spread.loc[best_idx]
        
        print(f"\nSpread = {spread:.0f} bps:")
        print(f"  Best Adjustment Factor: {best['adj_factor']:.2f}")
        print(f"  Total PnL: {best['total_pnl_bps']:.2f} bps")
        print(f"  Avg PnL per trade: {best['avg_pnl_bps']:.4f} bps")
        print(f"  Win Rate: {best['win_rate']*100:.1f}%")
    
    # Output detailed table
    print("\n" + "=" * 70)
    print("DETAILED RESULTS (5 bps spread)")
    print("=" * 70)
    df_5bps = all_results_df[all_results_df['spread_bps'] == 5.0].copy()
    df_5bps['win_rate_pct'] = df_5bps['win_rate'] * 100
    print(df_5bps[['adj_factor', 'trades', 'total_pnl_bps', 'avg_pnl_bps', 'win_rate_pct']].to_string(index=False))
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f'backtest_full_results_{timestamp}.xlsx')
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        metrics_df.to_excel(writer, sheet_name='Weekend_Metrics', index=False)
        all_results_df.to_excel(writer, sheet_name='Backtest_Results', index=False)
        hourly_df.to_excel(writer, sheet_name='Hourly_Analysis', index=False)
    
    print(f"\n\nResults saved to: {output_file}")
    
    print("\n" + "=" * 70)
    print("CHARTS GENERATED:")
    print("=" * 70)
    print(f"1. {os.path.join(OUTPUT_DIR, 'weekend_returns_analysis.png')}")
    print(f"2. {os.path.join(OUTPUT_DIR, 'backtest_results.png')}")
    print(f"3. {os.path.join(OUTPUT_DIR, 'hourly_analysis.png')}")
    
    print("\n" + "=" * 70)
    print("BACKTEST COMPLETED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
