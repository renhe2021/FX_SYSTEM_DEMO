"""
Weekend Pricing Strategy Full Backtest V3 (Corrected)
======================================================
Complete backtest for weekend pricing strategy using past 1 year data.

IMPORTANT FIX:
- Bloomberg JPYCNH quote is per 100 JPY (i.e., 4.83 = 100 JPY buys 4.83 CNH)
- Need to divide by 100 when calculating CNH PnL

Trading Volume:
- USD: 60 million USD / week
- JPY: 4 billion JPY / week

PnL calculation (CORRECTED):
- For JPY: PnL(CNH) = spread_earned(bps) * 0.0001 * JPY_volume * (JPYCNH_rate / 100)
  where JPYCNH_rate is BBG quote (per 100 JPY)

Strategy: max(hour_0, hour_6) as reference for pricing
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

# Trading parameters
USD_WEEKLY_VOLUME = 60_000_000  # 60 million USD per week
JPY_WEEKLY_VOLUME = 4_000_000_000  # 4 billion JPY per week

print("=" * 80)
print("Weekend Pricing Strategy - Full Backtest V3 (CORRECTED)")
print("=" * 80)
print(f"USD Weekly Volume: {USD_WEEKLY_VOLUME:,.0f} USD")
print(f"JPY Weekly Volume: {JPY_WEEKLY_VOLUME:,.0f} JPY")
print("\n*** IMPORTANT: JPYCNH is quoted per 100 JPY in Bloomberg ***")
print("*** PnL formula corrected to account for this ***")
print("=" * 80)


def load_existing_data():
    """Load existing data files"""
    print("\n[1] Loading Data Files...")
    print("-" * 60)
    
    all_files = os.listdir(OUTPUT_DIR)
    
    # Filter for JPYCNH files (prefer 1year files)
    jpycnh_files = [f for f in all_files if 'JPYCNH' in f and f.endswith('.xlsx') and not f.startswith('~$')]
    jpycnh_1year = [f for f in jpycnh_files if '1year' in f.lower() or 'weekend_1year' in f.lower()]
    if jpycnh_1year:
        jpycnh_files = jpycnh_1year
    
    # Filter for USDCNH files (prefer 1year files)
    usdcnh_files = [f for f in all_files if 'USDCNH' in f and f.endswith('.xlsx') and not f.startswith('~$')]
    usdcnh_1year = [f for f in usdcnh_files if '1year' in f.lower() or 'weekend_1year' in f.lower()]
    if usdcnh_1year:
        usdcnh_files = usdcnh_1year
    
    if not jpycnh_files:
        print("[ERROR] No JPYCNH data files found")
        return None, None
    if not usdcnh_files:
        print("[ERROR] No USDCNH data files found")
        return None, None
    
    # Sort by modification time
    jpycnh_files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    usdcnh_files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    
    jpycnh_file = os.path.join(OUTPUT_DIR, jpycnh_files[0])
    usdcnh_file = os.path.join(OUTPUT_DIR, usdcnh_files[0])
    
    print(f"Loading JPYCNH: {jpycnh_files[0]}")
    df_jpycnh = pd.read_excel(jpycnh_file)
    
    # Handle index/timestamp
    if 'timestamp' in df_jpycnh.columns:
        df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
        df_jpycnh.set_index('timestamp', inplace=True)
    elif 'Unnamed: 0' in df_jpycnh.columns:
        df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['Unnamed: 0'])
        df_jpycnh.set_index('timestamp', inplace=True)
        df_jpycnh.drop(columns=['Unnamed: 0'], errors='ignore', inplace=True)
    elif df_jpycnh.index.name != 'timestamp' and df_jpycnh.index.dtype == 'object':
        df_jpycnh.index = pd.to_datetime(df_jpycnh.index)
    
    print(f"Loading USDCNH: {usdcnh_files[0]}")
    df_usdcnh = pd.read_excel(usdcnh_file)
    
    if 'timestamp' in df_usdcnh.columns:
        df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
        df_usdcnh.set_index('timestamp', inplace=True)
    elif 'Unnamed: 0' in df_usdcnh.columns:
        df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['Unnamed: 0'])
        df_usdcnh.set_index('timestamp', inplace=True)
        df_usdcnh.drop(columns=['Unnamed: 0'], errors='ignore', inplace=True)
    elif df_usdcnh.index.dtype == 'object':
        df_usdcnh.index = pd.to_datetime(df_usdcnh.index)
    
    print(f"JPYCNH shape: {df_jpycnh.shape}")
    print(f"USDCNH shape: {df_usdcnh.shape}")
    print(f"\nJPYCNH date range: {df_jpycnh.index.min()} ~ {df_jpycnh.index.max()}")
    print(f"USDCNH date range: {df_usdcnh.index.min()} ~ {df_usdcnh.index.max()}")
    
    # Verify JPYCNH is per 100 JPY
    jpycnh_avg = df_jpycnh['mid'].mean() if 'mid' in df_jpycnh.columns else df_jpycnh['bid'].mean()
    print(f"\nJPYCNH average: {jpycnh_avg:.4f} (should be ~4.5-5.0 if per 100 JPY)")
    if jpycnh_avg > 1.0:
        print("*** Confirmed: JPYCNH is quoted per 100 JPY ***")
    
    return df_jpycnh, df_usdcnh


def prepare_weekend_data(df_jpycnh, df_usdcnh):
    """Prepare weekend data (Saturday 00:00-06:00 Beijing time)"""
    print("\n[2] Preparing Weekend Data (Saturday 00:00-06:00 Beijing)...")
    print("-" * 60)
    
    df_jpycnh = df_jpycnh.copy()
    df_usdcnh = df_usdcnh.copy()
    
    # Resample USDCNH to 1 minute if needed
    if len(df_usdcnh) > len(df_jpycnh) * 10:
        print("Resampling USDCNH to 1 minute...")
        df_usdcnh = df_usdcnh.resample('1min').last().ffill()
    
    # Add time columns
    df_jpycnh['weekday'] = df_jpycnh.index.dayofweek
    df_jpycnh['date'] = df_jpycnh.index.date
    df_jpycnh['hour'] = df_jpycnh.index.hour
    
    df_usdcnh['weekday'] = df_usdcnh.index.dayofweek
    df_usdcnh['date'] = df_usdcnh.index.date
    df_usdcnh['hour'] = df_usdcnh.index.hour
    
    # Calculate mid price
    if 'mid' not in df_jpycnh.columns:
        if 'bid' in df_jpycnh.columns and 'ask' in df_jpycnh.columns:
            df_jpycnh['mid'] = (df_jpycnh['bid'] + df_jpycnh['ask']) / 2
        elif 'close' in df_jpycnh.columns:
            df_jpycnh['mid'] = df_jpycnh['close']
    
    if 'mid' not in df_usdcnh.columns:
        if 'bid' in df_usdcnh.columns and 'ask' in df_usdcnh.columns:
            df_usdcnh['mid'] = (df_usdcnh['bid'] + df_usdcnh['ask']) / 2
        elif 'close' in df_usdcnh.columns:
            df_usdcnh['mid'] = df_usdcnh['close']
    
    # Filter Saturday data (hours 0-6)
    jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 6)].copy()
    usdcnh_sat = df_usdcnh[(df_usdcnh['weekday'] == 5) & (df_usdcnh['hour'] <= 6)].copy()
    
    print(f"JPYCNH Saturday data: {len(jpycnh_sat)} rows")
    print(f"USDCNH Saturday data: {len(usdcnh_sat)} rows")
    
    # Get common Saturday dates
    jpycnh_dates = jpycnh_sat['date'].unique()
    usdcnh_dates = usdcnh_sat['date'].unique()
    common_dates = sorted(set(jpycnh_dates) & set(usdcnh_dates))
    
    print(f"Common Saturday dates: {len(common_dates)}")
    if len(common_dates) > 0:
        print(f"Date range: {common_dates[0]} ~ {common_dates[-1]}")
    
    return jpycnh_sat, usdcnh_sat, common_dates


def backtest_weekend_strategy(jpycnh_sat, usdcnh_sat, common_dates, spread_bps=5.0):
    """
    Backtest the weekend pricing strategy (CORRECTED VERSION)
    
    Strategy: max(hour_0, hour_6) as USDCNH reference for pricing JPYCNH
    
    PnL calculation (CORRECTED):
    - Bloomberg JPYCNH is quoted per 100 JPY
    - PnL(CNH) = avg_pnl(bps) * 0.0001 * JPY_volume * (JPYCNH_rate / 100)
    """
    print(f"\n[3] Running Backtest (spread={spread_bps} bps)...")
    print("-" * 60)
    
    spread_half = spread_bps / 2
    adjustment_factors = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0]
    
    results = []
    weekly_details_all = {}
    
    for adj_factor in adjustment_factors:
        weekly_details = []
        
        for sat_date in common_dates:
            jpycnh_day = jpycnh_sat[jpycnh_sat['date'] == sat_date].copy()
            usdcnh_day = usdcnh_sat[usdcnh_sat['date'] == sat_date].copy()
            
            if jpycnh_day.empty or usdcnh_day.empty:
                continue
            
            # Get hourly reference prices for USDCNH
            usdcnh_h0 = usdcnh_day[usdcnh_day['hour'] == 0]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 0]) > 0 else np.nan
            usdcnh_h6 = usdcnh_day[usdcnh_day['hour'] == 6]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 6]) > 0 else np.nan
            
            if pd.isna(usdcnh_h0) or pd.isna(usdcnh_h6):
                continue
            
            # Strategy: Reference = max(hour_0, hour_6)
            ref_usdcnh = max(usdcnh_h0, usdcnh_h6)
            ref_used = 'hour_0' if ref_usdcnh == usdcnh_h0 else 'hour_6'
            ref_change_bps = (usdcnh_h6 - ref_usdcnh) / ref_usdcnh * 10000 if ref_usdcnh != usdcnh_h6 else 0
            
            # Get common timestamps
            common_idx = jpycnh_day.index.intersection(usdcnh_day.index)
            if len(common_idx) < 10:
                continue
            
            jpycnh_aligned = jpycnh_day.loc[common_idx].copy()
            usdcnh_aligned = usdcnh_day.loc[common_idx].copy()
            
            jpycnh_aligned['jpycnh_ret'] = jpycnh_aligned['mid'].pct_change() * 10000
            usdcnh_aligned['usdcnh_ret'] = usdcnh_aligned['mid'].pct_change() * 10000
            
            week_pnl_bps = 0
            week_trades = 0
            week_wins = 0
            
            for i in range(1, len(common_idx)):
                ts = common_idx[i]
                
                usdcnh_move = usdcnh_aligned.loc[ts, 'usdcnh_ret']
                jpycnh_actual = jpycnh_aligned.loc[ts, 'jpycnh_ret']
                
                if pd.isna(usdcnh_move) or pd.isna(jpycnh_actual):
                    continue
                
                # Prediction based on USDCNH movement
                predicted = (usdcnh_move + ref_change_bps * 0.01) * adj_factor
                quote_error = abs(jpycnh_actual - predicted)
                
                # PnL calculation
                if quote_error < spread_half:
                    pnl = spread_half  # Win: earn half spread
                    week_wins += 1
                else:
                    pnl = spread_half - quote_error  # Lose: (spread/2 - error)
                
                week_pnl_bps += pnl
                week_trades += 1
            
            # Get average JPYCNH rate (per 100 JPY) and USDCNH rate
            jpycnh_rate_per_100jpy = jpycnh_day['mid'].mean()  # ~4.8 (per 100 JPY)
            usdcnh_rate = usdcnh_day['mid'].mean()  # ~7.2
            
            # CORRECTED PnL calculation:
            # jpycnh_rate is per 100 JPY, so actual rate per 1 JPY = jpycnh_rate / 100
            # PnL(CNH) = avg_pnl(bps) * 0.0001 * JPY_volume * (jpycnh_rate / 100)
            avg_pnl_per_trade_bps = week_pnl_bps / week_trades if week_trades > 0 else 0
            jpycnh_per_jpy = jpycnh_rate_per_100jpy / 100  # Convert to per 1 JPY
            week_pnl_cnh = avg_pnl_per_trade_bps * 0.0001 * JPY_WEEKLY_VOLUME * jpycnh_per_jpy
            
            weekly_details.append({
                'date': sat_date,
                'trades': week_trades,
                'wins': week_wins,
                'win_rate': week_wins / week_trades if week_trades > 0 else 0,
                'total_pnl_bps': week_pnl_bps,
                'avg_pnl_bps': avg_pnl_per_trade_bps,
                'jpycnh_rate_per100': jpycnh_rate_per_100jpy,
                'jpycnh_per_jpy': jpycnh_per_jpy,
                'usdcnh_rate': usdcnh_rate,
                'week_pnl_cnh': week_pnl_cnh,
                'ref_used': ref_used,
            })
        
        # Aggregate results
        if weekly_details:
            total_trades = sum(w['trades'] for w in weekly_details)
            total_wins = sum(w['wins'] for w in weekly_details)
            total_pnl_bps = sum(w['total_pnl_bps'] for w in weekly_details)
            total_pnl_cnh = sum(w['week_pnl_cnh'] for w in weekly_details)
            
            avg_pnl_bps = total_pnl_bps / total_trades if total_trades > 0 else 0
            win_rate = total_wins / total_trades if total_trades > 0 else 0
            avg_weekly_pnl_cnh = total_pnl_cnh / len(weekly_details)
            
            results.append({
                'spread_bps': spread_bps,
                'adj_factor': adj_factor,
                'num_weeks': len(weekly_details),
                'total_trades': total_trades,
                'total_wins': total_wins,
                'win_rate': win_rate,
                'total_pnl_bps': total_pnl_bps,
                'avg_pnl_bps': avg_pnl_bps,
                'total_pnl_cnh': total_pnl_cnh,
                'avg_weekly_pnl_cnh': avg_weekly_pnl_cnh,
            })
            
            weekly_details_all[adj_factor] = weekly_details
    
    df_results = pd.DataFrame(results)
    
    # Get best factor's weekly details
    best_idx = df_results['total_pnl_cnh'].idxmax()
    best_factor = df_results.loc[best_idx, 'adj_factor']
    df_weekly = pd.DataFrame(weekly_details_all.get(best_factor, []))
    
    return df_results, df_weekly


def print_backtest_summary(df_results, spread_bps):
    """Print backtest results summary"""
    print(f"\n{'='*80}")
    print(f"BACKTEST RESULTS (spread={spread_bps} bps)")
    print(f"{'='*80}")
    
    best_idx = df_results['total_pnl_cnh'].idxmax()
    best = df_results.loc[best_idx]
    
    print(f"\nBest Adjustment Factor: {best['adj_factor']:.2f}")
    print(f"  Weeks Analyzed: {best['num_weeks']:.0f}")
    print(f"  Total Trades: {best['total_trades']:,.0f}")
    print(f"  Win Rate: {best['win_rate']*100:.1f}%")
    print(f"  Total PnL: {best['total_pnl_bps']:,.2f} bps")
    print(f"  Avg PnL per Trade: {best['avg_pnl_bps']:.4f} bps")
    print(f"  Total PnL (CNH): {best['total_pnl_cnh']:,.2f} CNH")
    print(f"  Avg Weekly PnL (CNH): {best['avg_weekly_pnl_cnh']:,.2f} CNH")
    
    print(f"\n--- All Results (sorted by Total PnL CNH) ---")
    df_sorted = df_results.sort_values('total_pnl_cnh', ascending=False)
    print(df_sorted[['adj_factor', 'win_rate', 'avg_pnl_bps', 'total_pnl_cnh', 'avg_weekly_pnl_cnh']].to_string(index=False))
    
    return best


def plot_backtest_results(all_results, output_dir):
    """Plot backtest results"""
    print("\n[4] Generating Plots...")
    print("-" * 60)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(all_results)))
    
    # 1. Total PnL (CNH) vs Adjustment Factor
    ax1 = axes[0, 0]
    for i, (spread, df) in enumerate(all_results.items()):
        ax1.plot(df['adj_factor'], df['total_pnl_cnh'], 
                marker='o', linewidth=2, markersize=6, color=colors[i],
                label=f'spread={spread}bps')
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Adjustment Factor', fontsize=12)
    ax1.set_ylabel('Total PnL (CNH)', fontsize=12)
    ax1.set_title('Total PnL vs Adjustment Factor (CORRECTED)', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1e3:.1f}K'))
    
    # 2. Win Rate vs Adjustment Factor
    ax2 = axes[0, 1]
    for i, (spread, df) in enumerate(all_results.items()):
        ax2.plot(df['adj_factor'], df['win_rate'] * 100, 
                marker='o', linewidth=2, markersize=6, color=colors[i],
                label=f'spread={spread}bps')
    ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')
    ax2.set_xlabel('Adjustment Factor', fontsize=12)
    ax2.set_ylabel('Win Rate (%)', fontsize=12)
    ax2.set_title('Win Rate vs Adjustment Factor', fontsize=14, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([80, 102])
    
    # 3. Average Weekly PnL (CNH) vs Spread
    ax3 = axes[1, 0]
    best_factors = []
    best_pnls = []
    spreads_list = []
    for spread, df in all_results.items():
        best_idx = df['total_pnl_cnh'].idxmax()
        best_factors.append(df.loc[best_idx, 'adj_factor'])
        best_pnls.append(df.loc[best_idx, 'avg_weekly_pnl_cnh'])
        spreads_list.append(spread)
    
    bars = ax3.bar(range(len(spreads_list)), best_pnls, color='steelblue', alpha=0.7)
    ax3.set_xticks(range(len(spreads_list)))
    ax3.set_xticklabels([f'{s}bps' for s in spreads_list])
    ax3.set_xlabel('Spread', fontsize=12)
    ax3.set_ylabel('Avg Weekly PnL (CNH)', fontsize=12)
    ax3.set_title('Best Avg Weekly PnL by Spread (CORRECTED)', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e3:.1f}K' if abs(x) >= 1e3 else f'{x:.0f}'))
    
    # Add value labels
    for i, (pnl, factor) in enumerate(zip(best_pnls, best_factors)):
        label = f'{pnl/1e3:.1f}K\n(f={factor})'
        ax3.annotate(label, xy=(i, pnl),
                    xytext=(0, 5), textcoords='offset points',
                    ha='center', fontsize=9)
    
    # 4. Summary text
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = "BACKTEST SUMMARY (CORRECTED)\n" + "="*45 + "\n\n"
    summary_text += f"Trading Parameters:\n"
    summary_text += f"  USD Volume: {USD_WEEKLY_VOLUME/1e6:.0f}M USD/week\n"
    summary_text += f"  JPY Volume: {JPY_WEEKLY_VOLUME/1e9:.0f}B JPY/week\n\n"
    summary_text += "IMPORTANT: JPYCNH is quoted per 100 JPY\n"
    summary_text += "PnL formula adjusted accordingly\n\n"
    
    summary_text += "Best Results by Spread:\n"
    for spread, df in all_results.items():
        best_idx = df['total_pnl_cnh'].idxmax()
        best = df.loc[best_idx]
        summary_text += f"\n  Spread {spread}bps:\n"
        summary_text += f"    Factor: {best['adj_factor']:.2f}\n"
        summary_text += f"    Win Rate: {best['win_rate']*100:.1f}%\n"
        summary_text += f"    Total: {best['total_pnl_cnh']/1e3:.1f}K CNH\n"
        summary_text += f"    Avg/Week: {best['avg_weekly_pnl_cnh']/1e3:.1f}K CNH\n"
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    
    plt.tight_layout()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = os.path.join(output_dir, f'weekend_backtest_v3_corrected_{timestamp}.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")
    
    return save_path


def save_results_to_excel(all_results, df_weekly, output_dir):
    """Save all results to Excel"""
    print("\n[5] Saving Results to Excel...")
    print("-" * 60)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'weekend_backtest_v3_corrected_{timestamp}.xlsx')
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_rows = []
        for spread, df in all_results.items():
            best_idx = df['total_pnl_cnh'].idxmax()
            best = df.loc[best_idx]
            summary_rows.append({
                'Spread (bps)': spread,
                'Best Factor': best['adj_factor'],
                'Weeks': best['num_weeks'],
                'Total Trades': best['total_trades'],
                'Win Rate (%)': best['win_rate'] * 100,
                'Total PnL (bps)': best['total_pnl_bps'],
                'Avg PnL (bps/trade)': best['avg_pnl_bps'],
                'Total PnL (CNH)': best['total_pnl_cnh'],
                'Avg Weekly PnL (CNH)': best['avg_weekly_pnl_cnh'],
                'Annualized PnL (CNH)': best['avg_weekly_pnl_cnh'] * 52,
            })
        df_summary = pd.DataFrame(summary_rows)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Detail sheets
        for spread, df in all_results.items():
            df.to_excel(writer, sheet_name=f'Spread_{int(spread)}bps', index=False)
        
        # Weekly detail
        if df_weekly is not None and not df_weekly.empty:
            df_weekly.to_excel(writer, sheet_name='Weekly_Detail', index=False)
    
    print(f"Saved: {output_file}")
    return output_file


def main():
    """Main function"""
    # Load data
    df_jpycnh, df_usdcnh = load_existing_data()
    
    if df_usdcnh is None or df_jpycnh is None:
        print("[ERROR] No data available. Exiting.")
        return
    
    # Prepare weekend data
    jpycnh_sat, usdcnh_sat, common_dates = prepare_weekend_data(df_jpycnh, df_usdcnh)
    
    if len(common_dates) == 0:
        print("[ERROR] No common Saturday dates found. Exiting.")
        return
    
    # Run backtest with different spreads
    spreads = [3.0, 5.0, 7.0, 10.0]
    all_results = {}
    df_weekly_best = None
    
    for spread in spreads:
        df_results, df_weekly = backtest_weekend_strategy(
            jpycnh_sat, usdcnh_sat, common_dates, spread_bps=spread)
        all_results[spread] = df_results
        
        best = print_backtest_summary(df_results, spread)
        
        if df_weekly is not None and (df_weekly_best is None or len(df_weekly) > len(df_weekly_best)):
            df_weekly_best = df_weekly
    
    # Plot results
    plot_path = plot_backtest_results(all_results, OUTPUT_DIR)
    
    # Save to Excel
    excel_path = save_results_to_excel(all_results, df_weekly_best, OUTPUT_DIR)
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - CNH PROFITS (CORRECTED)")
    print("="*80)
    
    print(f"\nTrading Volume:")
    print(f"  USD: {USD_WEEKLY_VOLUME/1e6:.0f} million USD / week")
    print(f"  JPY: {JPY_WEEKLY_VOLUME/1e9:.0f} billion JPY / week")
    
    print(f"\nIMPORTANT: Bloomberg JPYCNH is quoted per 100 JPY")
    print(f"PnL formula: avg_pnl(bps) * 0.0001 * 4B JPY * (JPYCNH/100)")
    
    print(f"\nBest Results by Spread:")
    print("-"*80)
    print(f"{'Spread':>10} {'Factor':>8} {'Win%':>8} {'Weeks':>8} {'Total CNH':>15} {'Avg/Week CNH':>15}")
    print("-"*80)
    
    for spread, df in all_results.items():
        best_idx = df['total_pnl_cnh'].idxmax()
        best = df.loc[best_idx]
        print(f"{spread:>10.0f} {best['adj_factor']:>8.2f} {best['win_rate']*100:>7.1f}% {best['num_weeks']:>8.0f} {best['total_pnl_cnh']:>15,.2f} {best['avg_weekly_pnl_cnh']:>15,.2f}")
    
    print("-"*80)
    
    # Annualized return estimate
    print(f"\nAnnualized Estimates (52 weeks):")
    for spread, df in all_results.items():
        best_idx = df['total_pnl_cnh'].idxmax()
        best = df.loc[best_idx]
        annual_pnl = best['avg_weekly_pnl_cnh'] * 52
        print(f"  Spread {spread:.0f}bps: ~{annual_pnl:,.0f} CNH / year ({annual_pnl/1e6:.2f}M CNH)")
    
    print(f"\nOutput files:")
    print(f"  Chart: {plot_path}")
    print(f"  Excel: {excel_path}")
    print("="*80)


if __name__ == "__main__":
    main()
