"""
Weekend Pricing Strategy Full Backtest
======================================
Complete backtest for weekend pricing strategy using past 1 year data.

Trading Volume:
- USD: 60 million USD / week
- JPY: 4 billion JPY / week

PnL will be calculated in CNH.

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
print("Weekend Pricing Strategy - Full Backtest (1 Year)")
print("=" * 80)
print(f"USD Weekly Volume: {USD_WEEKLY_VOLUME:,.0f} USD")
print(f"JPY Weekly Volume: {JPY_WEEKLY_VOLUME:,.0f} JPY")
print("=" * 80)


def download_data_from_bbg():
    """Download 1 year of weekend data from Bloomberg"""
    print("\n[1] Downloading Data from Bloomberg...")
    print("-" * 60)
    
    try:
        from quant_system.tools.bbg_wrapper import BloombergWrapper
        
        bbg = BloombergWrapper()
        if not bbg.connect():
            print("[ERROR] Cannot connect to Bloomberg")
            return None, None
        
        # Time range: past 1 year
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        print(f"Time range: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        # Download USDCNH bid/ask data (1 minute bars)
        print("\n[1.1] Downloading USDCNH Bid/Ask data...")
        usdcnh_data = bbg.get_bid_ask_bars(
            symbol="USDCNH Curncy",
            start_date=start_date,
            end_date=end_date,
            resample="1min",
            is_beijing_time=True
        )
        
        if usdcnh_data is not None:
            print(f"USDCNH data: {len(usdcnh_data)} rows")
            # Convert to Beijing time
            usdcnh_data.index = usdcnh_data.index + timedelta(hours=8)
            
            # Save to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            usdcnh_file = os.path.join(OUTPUT_DIR, f"USDCNH_weekend_1year_{timestamp}.xlsx")
            usdcnh_data.to_excel(usdcnh_file)
            print(f"Saved: {usdcnh_file}")
        
        # Download JPYCNH bid/ask data (1 minute bars)
        print("\n[1.2] Downloading JPYCNH Bid/Ask data...")
        jpycnh_data = bbg.get_bid_ask_bars(
            symbol="JPYCNH Curncy",
            start_date=start_date,
            end_date=end_date,
            resample="1min",
            is_beijing_time=True
        )
        
        if jpycnh_data is not None:
            print(f"JPYCNH data: {len(jpycnh_data)} rows")
            # Convert to Beijing time
            jpycnh_data.index = jpycnh_data.index + timedelta(hours=8)
            
            # Save to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            jpycnh_file = os.path.join(OUTPUT_DIR, f"JPYCNH_weekend_1year_{timestamp}.xlsx")
            jpycnh_data.to_excel(jpycnh_file)
            print(f"Saved: {jpycnh_file}")
        
        bbg.disconnect()
        
        return usdcnh_data, jpycnh_data
        
    except ImportError as e:
        print(f"[ERROR] Bloomberg API not available: {e}")
        return None, None
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def load_existing_data():
    """Load existing data files if Bloomberg is not available"""
    print("\n[1] Loading Existing Data Files...")
    print("-" * 60)
    
    # Find the most recent JPYCNH and USDCNH files
    jpycnh_files = [f for f in os.listdir(OUTPUT_DIR) if 'JPYCNH' in f and f.endswith('.xlsx') and not f.startswith('~$')]
    usdcnh_files = [f for f in os.listdir(OUTPUT_DIR) if 'USDCNH' in f and f.endswith('.xlsx') and not f.startswith('~$')]
    
    if not jpycnh_files:
        print("[ERROR] No JPYCNH data files found")
        return None, None
    if not usdcnh_files:
        print("[ERROR] No USDCNH data files found")
        return None, None
    
    # Sort by modification time and get the most recent
    jpycnh_files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    usdcnh_files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    
    jpycnh_file = os.path.join(OUTPUT_DIR, jpycnh_files[0])
    usdcnh_file = os.path.join(OUTPUT_DIR, usdcnh_files[0])
    
    print(f"Loading JPYCNH: {jpycnh_files[0]}")
    df_jpycnh = pd.read_excel(jpycnh_file)
    if 'timestamp' in df_jpycnh.columns:
        df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
        df_jpycnh.set_index('timestamp', inplace=True)
    elif df_jpycnh.index.name != 'timestamp':
        df_jpycnh.index = pd.to_datetime(df_jpycnh.iloc[:, 0])
        df_jpycnh = df_jpycnh.iloc[:, 1:]
    
    print(f"Loading USDCNH: {usdcnh_files[0]}")
    df_usdcnh = pd.read_excel(usdcnh_file)
    if 'timestamp' in df_usdcnh.columns:
        df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
        df_usdcnh.set_index('timestamp', inplace=True)
    elif df_usdcnh.index.name != 'timestamp':
        df_usdcnh.index = pd.to_datetime(df_usdcnh.iloc[:, 0])
        df_usdcnh = df_usdcnh.iloc[:, 1:]
    
    print(f"JPYCNH shape: {df_jpycnh.shape}")
    print(f"USDCNH shape: {df_usdcnh.shape}")
    
    # Data date range
    print(f"\nJPYCNH date range: {df_jpycnh.index.min()} ~ {df_jpycnh.index.max()}")
    print(f"USDCNH date range: {df_usdcnh.index.min()} ~ {df_usdcnh.index.max()}")
    
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
    
    # Calculate mid price if not exists
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


def get_usdcnh_rate(df_usdcnh, sat_date):
    """Get USDCNH rate for a Saturday (for CNH conversion)"""
    usdcnh_day = df_usdcnh[df_usdcnh['date'] == sat_date]
    if usdcnh_day.empty:
        return 7.25  # Default value if no data
    return usdcnh_day['mid'].mean()


def backtest_weekend_strategy(jpycnh_sat, usdcnh_sat, common_dates, spread_bps=5.0):
    """
    Backtest the weekend pricing strategy
    
    Strategy: max(hour_0, hour_6) as USDCNH reference for pricing JPYCNH
    
    Returns weekly PnL in CNH
    """
    print(f"\n[3] Running Backtest (spread={spread_bps} bps)...")
    print("-" * 60)
    
    spread_half = spread_bps / 2
    
    # Test different adjustment factors
    adjustment_factors = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0]
    
    results = []
    weekly_details = []
    
    for adj_factor in adjustment_factors:
        total_pnl_bps = 0
        total_trades = 0
        total_wins = 0
        
        # Weekly PnL tracking
        weekly_pnl_cnh = []
        
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
            
            # Strategy A: Reference = max(hour_0, hour_6)
            ref_usdcnh = max(usdcnh_h0, usdcnh_h6)
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
                quote_error = jpycnh_actual - predicted
                
                # PnL calculation
                if abs(quote_error) < spread_half:
                    pnl = spread_half
                    week_wins += 1
                else:
                    pnl = spread_half - abs(quote_error)
                
                week_pnl_bps += pnl
                week_trades += 1
            
            total_pnl_bps += week_pnl_bps
            total_trades += week_trades
            total_wins += week_wins
            
            # Convert weekly PnL to CNH
            # For JPYCNH: 1 bps = 0.0001 * JPYCNH rate
            # PnL in CNH = pnl_bps * 0.0001 * JPY_volume * JPYCNH_rate
            
            jpycnh_rate = jpycnh_day['mid'].mean()  # Average JPYCNH rate for the day
            usdcnh_rate = get_usdcnh_rate(usdcnh_sat, sat_date)
            
            # Weekly PnL in CNH for JPY trading
            # Assume trading volume is distributed across the weekend
            jpy_pnl_cnh = week_pnl_bps * 0.0001 * JPY_WEEKLY_VOLUME * jpycnh_rate
            
            if adj_factor == 0.3:  # Track details for the best factor (approximately)
                weekly_details.append({
                    'date': sat_date,
                    'trades': week_trades,
                    'wins': week_wins,
                    'win_rate': week_wins / week_trades if week_trades > 0 else 0,
                    'pnl_bps': week_pnl_bps,
                    'jpycnh_rate': jpycnh_rate,
                    'usdcnh_rate': usdcnh_rate,
                    'jpy_pnl_cnh': jpy_pnl_cnh,
                    'ref_used': 'hour_0' if ref_usdcnh == usdcnh_h0 else 'hour_6',
                })
            
            weekly_pnl_cnh.append(jpy_pnl_cnh)
        
        avg_pnl_bps = total_pnl_bps / total_trades if total_trades > 0 else 0
        win_rate = total_wins / total_trades if total_trades > 0 else 0
        total_pnl_cnh = sum(weekly_pnl_cnh)
        avg_weekly_pnl_cnh = np.mean(weekly_pnl_cnh) if weekly_pnl_cnh else 0
        
        results.append({
            'spread_bps': spread_bps,
            'adj_factor': adj_factor,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'win_rate': win_rate,
            'total_pnl_bps': total_pnl_bps,
            'avg_pnl_bps': avg_pnl_bps,
            'total_pnl_cnh': total_pnl_cnh,
            'avg_weekly_pnl_cnh': avg_weekly_pnl_cnh,
            'num_weeks': len(weekly_pnl_cnh),
        })
    
    df_results = pd.DataFrame(results)
    df_weekly = pd.DataFrame(weekly_details) if weekly_details else None
    
    return df_results, df_weekly


def print_backtest_summary(df_results, spread_bps):
    """Print backtest results summary"""
    print(f"\n{'='*80}")
    print(f"BACKTEST RESULTS (spread={spread_bps} bps)")
    print(f"{'='*80}")
    
    # Find best factor
    best_idx = df_results['total_pnl_cnh'].idxmax()
    best = df_results.loc[best_idx]
    
    print(f"\nBest Adjustment Factor: {best['adj_factor']:.2f}")
    print(f"  Total Trades: {best['total_trades']:,.0f}")
    print(f"  Win Rate: {best['win_rate']*100:.1f}%")
    print(f"  Total PnL: {best['total_pnl_bps']:,.2f} bps")
    print(f"  Total PnL (CNH): {best['total_pnl_cnh']:,.2f} CNH")
    print(f"  Avg Weekly PnL (CNH): {best['avg_weekly_pnl_cnh']:,.2f} CNH")
    print(f"  Number of Weeks: {best['num_weeks']}")
    
    print(f"\n--- All Results ---")
    print(df_results[['adj_factor', 'win_rate', 'total_pnl_bps', 'total_pnl_cnh', 'avg_weekly_pnl_cnh']].to_string(index=False))
    
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
    ax1.set_title('Total PnL vs Adjustment Factor', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
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
    
    ax3.bar(range(len(spreads_list)), best_pnls, color='steelblue', alpha=0.7)
    ax3.set_xticks(range(len(spreads_list)))
    ax3.set_xticklabels([f'{s}bps' for s in spreads_list])
    ax3.set_xlabel('Spread', fontsize=12)
    ax3.set_ylabel('Avg Weekly PnL (CNH)', fontsize=12)
    ax3.set_title('Best Avg Weekly PnL by Spread', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for i, (pnl, factor) in enumerate(zip(best_pnls, best_factors)):
        ax3.annotate(f'{pnl:,.0f}\n(f={factor})', xy=(i, pnl),
                    xytext=(0, 5), textcoords='offset points',
                    ha='center', fontsize=9)
    
    # 4. Summary text
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = "BACKTEST SUMMARY\n" + "="*40 + "\n\n"
    summary_text += f"Trading Parameters:\n"
    summary_text += f"  USD Volume: {USD_WEEKLY_VOLUME/1e6:.0f}M USD/week\n"
    summary_text += f"  JPY Volume: {JPY_WEEKLY_VOLUME/1e9:.0f}B JPY/week\n\n"
    
    summary_text += "Best Results by Spread:\n"
    for spread, df in all_results.items():
        best_idx = df['total_pnl_cnh'].idxmax()
        best = df.loc[best_idx]
        summary_text += f"\n  Spread {spread}bps:\n"
        summary_text += f"    Factor: {best['adj_factor']:.2f}\n"
        summary_text += f"    Win Rate: {best['win_rate']*100:.1f}%\n"
        summary_text += f"    Total PnL: {best['total_pnl_cnh']:,.0f} CNH\n"
        summary_text += f"    Weeks: {best['num_weeks']}\n"
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    
    plt.tight_layout()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = os.path.join(output_dir, f'weekend_backtest_full_{timestamp}.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")
    
    return save_path


def save_results_to_excel(all_results, df_weekly, output_dir):
    """Save all results to Excel"""
    print("\n[5] Saving Results to Excel...")
    print("-" * 60)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'weekend_backtest_full_{timestamp}.xlsx')
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_rows = []
        for spread, df in all_results.items():
            best_idx = df['total_pnl_cnh'].idxmax()
            best = df.loc[best_idx]
            summary_rows.append({
                'Spread (bps)': spread,
                'Best Factor': best['adj_factor'],
                'Total Trades': best['total_trades'],
                'Win Rate (%)': best['win_rate'] * 100,
                'Total PnL (bps)': best['total_pnl_bps'],
                'Total PnL (CNH)': best['total_pnl_cnh'],
                'Avg Weekly PnL (CNH)': best['avg_weekly_pnl_cnh'],
                'Weeks': best['num_weeks'],
            })
        df_summary = pd.DataFrame(summary_rows)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Detail sheets for each spread
        for spread, df in all_results.items():
            df.to_excel(writer, sheet_name=f'Spread_{int(spread)}bps', index=False)
        
        # Weekly detail sheet
        if df_weekly is not None and not df_weekly.empty:
            df_weekly.to_excel(writer, sheet_name='Weekly_Detail', index=False)
    
    print(f"Saved: {output_file}")
    return output_file


def main():
    """Main function"""
    # Try to download from Bloomberg first
    print("\n" + "="*80)
    print("Step 1: Data Acquisition")
    print("="*80)
    
    df_usdcnh, df_jpycnh = None, None
    
    # Try Bloomberg download
    try:
        df_usdcnh, df_jpycnh = download_data_from_bbg()
    except Exception as e:
        print(f"Bloomberg download failed: {e}")
    
    # If Bloomberg failed, load existing data
    if df_usdcnh is None or df_jpycnh is None:
        print("\nFalling back to existing data files...")
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
        
        if df_weekly is not None and df_weekly_best is None:
            df_weekly_best = df_weekly
    
    # Plot results
    plot_path = plot_backtest_results(all_results, OUTPUT_DIR)
    
    # Save to Excel
    excel_path = save_results_to_excel(all_results, df_weekly_best, OUTPUT_DIR)
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - CNH PROFITS")
    print("="*80)
    
    print(f"\nTrading Volume:")
    print(f"  USD: {USD_WEEKLY_VOLUME/1e6:.0f} million USD / week")
    print(f"  JPY: {JPY_WEEKLY_VOLUME/1e9:.0f} billion JPY / week")
    
    print(f"\nBest Results by Spread:")
    print("-"*60)
    print(f"{'Spread':>10} {'Factor':>8} {'Win%':>8} {'Total CNH':>15} {'Avg/Week':>12}")
    print("-"*60)
    
    for spread, df in all_results.items():
        best_idx = df['total_pnl_cnh'].idxmax()
        best = df.loc[best_idx]
        print(f"{spread:>10.0f} {best['adj_factor']:>8.2f} {best['win_rate']*100:>7.1f}% {best['total_pnl_cnh']:>15,.0f} {best['avg_weekly_pnl_cnh']:>12,.0f}")
    
    print("-"*60)
    print(f"\nOutput files:")
    print(f"  Chart: {plot_path}")
    print(f"  Excel: {excel_path}")
    print("="*80)


if __name__ == "__main__":
    main()
