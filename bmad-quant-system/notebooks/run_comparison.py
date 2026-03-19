"""
Strategy Comparison: max(0,6) vs max(2,6)
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'
JPY_WEEKLY_VOLUME = 4_000_000_000
SPREAD_BPS = 5.0

print("="*60)
print("Strategy Comparison: max(0,6) vs max(2,6)")
print("="*60)

# Load data
all_files = os.listdir(OUTPUT_DIR)
jpycnh_files = [f for f in all_files if 'JPYCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]
usdcnh_files = [f for f in all_files if 'USDCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]

print(f'Loading JPYCNH: {jpycnh_files[0]}')
df_jpycnh = pd.read_excel(os.path.join(OUTPUT_DIR, jpycnh_files[0]))
df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
df_jpycnh.set_index('timestamp', inplace=True)

print(f'Loading USDCNH: {usdcnh_files[0]}')
df_usdcnh = pd.read_excel(os.path.join(OUTPUT_DIR, usdcnh_files[0]))
df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
df_usdcnh.set_index('timestamp', inplace=True)

# Prepare Saturday data
for df in [df_jpycnh, df_usdcnh]:
    df['weekday'] = df.index.dayofweek
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    if 'mid' not in df.columns:
        df['mid'] = (df['bid'] + df['ask']) / 2

jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 6)].copy()
usdcnh_sat = df_usdcnh[(df_usdcnh['weekday'] == 5) & (df_usdcnh['hour'] <= 6)].copy()
common_dates = sorted(set(jpycnh_sat['date'].unique()) & set(usdcnh_sat['date'].unique()))
print(f'Common Saturday dates: {len(common_dates)}')


def run_backtest(strategy, spread_bps=5.0):
    spread_half = spread_bps / 2
    weekly_results = []
    
    for sat_date in common_dates:
        jpycnh_day = jpycnh_sat[jpycnh_sat['date'] == sat_date].copy()
        usdcnh_day = usdcnh_sat[usdcnh_sat['date'] == sat_date].copy()
        
        if jpycnh_day.empty or usdcnh_day.empty:
            continue
        
        usdcnh_h0 = usdcnh_day[usdcnh_day['hour'] == 0]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 0]) > 0 else np.nan
        usdcnh_h2 = usdcnh_day[usdcnh_day['hour'] == 2]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 2]) > 0 else np.nan
        usdcnh_h6 = usdcnh_day[usdcnh_day['hour'] == 6]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 6]) > 0 else np.nan
        
        if pd.isna(usdcnh_h6):
            continue
        
        if strategy == 'max_0_6':
            if pd.isna(usdcnh_h0): continue
            ref_usdcnh = max(usdcnh_h0, usdcnh_h6)
            ref_used = 'h0' if ref_usdcnh == usdcnh_h0 else 'h6'
        else:
            if pd.isna(usdcnh_h2): continue
            ref_usdcnh = max(usdcnh_h2, usdcnh_h6)
            ref_used = 'h2' if ref_usdcnh == usdcnh_h2 else 'h6'
        
        common_idx = jpycnh_day.index.intersection(usdcnh_day.index)
        if len(common_idx) < 10: continue
        
        jpycnh_aligned = jpycnh_day.loc[common_idx].copy()
        jpycnh_aligned['ret'] = jpycnh_aligned['mid'].pct_change() * 10000
        
        week_pnl_bps, week_trades, week_wins = 0, 0, 0
        
        for i in range(1, len(common_idx)):
            ret = jpycnh_aligned.loc[common_idx[i], 'ret']
            if pd.isna(ret): continue
            quote_error = abs(ret)
            if quote_error < spread_half:
                pnl = spread_half
                week_wins += 1
            else:
                pnl = spread_half - quote_error
            week_pnl_bps += pnl
            week_trades += 1
        
        jpycnh_rate = jpycnh_day['mid'].mean() / 100
        avg_pnl_bps = week_pnl_bps / week_trades if week_trades > 0 else 0
        week_pnl_cnh = avg_pnl_bps * 0.0001 * JPY_WEEKLY_VOLUME * jpycnh_rate
        
        weekly_results.append({
            'date': sat_date, 'ref_used': ref_used, 'trades': week_trades,
            'wins': week_wins, 'win_rate': week_wins/week_trades if week_trades > 0 else 0,
            'avg_pnl_bps': avg_pnl_bps, 'week_pnl_cnh': week_pnl_cnh
        })
    return pd.DataFrame(weekly_results)


print('\nRunning backtests...')
df_0_6 = run_backtest('max_0_6', SPREAD_BPS)
df_2_6 = run_backtest('max_2_6', SPREAD_BPS)

common_weeks = set(df_0_6['date']) & set(df_2_6['date'])
df_0_6 = df_0_6[df_0_6['date'].isin(common_weeks)].sort_values('date').reset_index(drop=True)
df_2_6 = df_2_6[df_2_6['date'].isin(common_weeks)].sort_values('date').reset_index(drop=True)
df_0_6['cumsum_pnl'] = df_0_6['week_pnl_cnh'].cumsum()
df_2_6['cumsum_pnl'] = df_2_6['week_pnl_cnh'].cumsum()

print(f'\nmax(0,6): Total={df_0_6["week_pnl_cnh"].sum():,.0f} CNH, Avg={df_0_6["week_pnl_cnh"].mean():,.0f} CNH/week')
print(f'max(2,6): Total={df_2_6["week_pnl_cnh"].sum():,.0f} CNH, Avg={df_2_6["week_pnl_cnh"].mean():,.0f} CNH/week')

# Plot
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
dates = pd.to_datetime(df_0_6['date'])

# Plot 1: Cumulative PnL
ax1 = axes[0, 0]
ax1.plot(dates, df_0_6['cumsum_pnl']/1000, 'b-', linewidth=2.5, marker='o', markersize=4, label='max(0,6)')
ax1.plot(dates, df_2_6['cumsum_pnl']/1000, 'r-', linewidth=2.5, marker='s', markersize=4, label='max(2,6)')
ax1.fill_between(dates, df_0_6['cumsum_pnl']/1000, df_2_6['cumsum_pnl']/1000, 
                 where=(df_0_6['cumsum_pnl'].values > df_2_6['cumsum_pnl'].values), color='blue', alpha=0.2, label='max(0,6) advantage')
ax1.fill_between(dates, df_0_6['cumsum_pnl']/1000, df_2_6['cumsum_pnl']/1000, 
                 where=(df_0_6['cumsum_pnl'].values < df_2_6['cumsum_pnl'].values), color='red', alpha=0.2, label='max(2,6) advantage')
ax1.set_xlabel('Date', fontsize=12)
ax1.set_ylabel('Cumulative PnL (K CNH)', fontsize=12)
ax1.set_title(f'Cumulative PnL Comparison (spread={SPREAD_BPS}bps)', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

# Plot 2: Weekly difference
ax2 = axes[0, 1]
diff_pnl = (df_0_6['week_pnl_cnh'] - df_2_6['week_pnl_cnh']) / 1000
colors = ['green' if x >= 0 else 'red' for x in diff_pnl]
ax2.bar(range(len(diff_pnl)), diff_pnl, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.axhline(y=diff_pnl.mean(), color='blue', linestyle='--', linewidth=2, label=f'Avg Diff: {diff_pnl.mean():.2f}K')
ax2.set_xlabel('Week', fontsize=12)
ax2.set_ylabel('PnL Difference (K CNH)', fontsize=12)
ax2.set_title('Weekly PnL Difference [max(0,6) - max(2,6)]', fontsize=14, fontweight='bold')
ax2.legend(loc='best', fontsize=10)
ax2.grid(True, alpha=0.3, axis='y')
pos_count = (diff_pnl >= 0).sum()
neg_count = (diff_pnl < 0).sum()
ax2.text(0.98, 0.95, f'max(0,6) better: {pos_count}w\nmax(2,6) better: {neg_count}w', 
         transform=ax2.transAxes, fontsize=11, va='top', ha='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Plot 3: Side-by-side comparison
ax3 = axes[1, 0]
x = np.arange(len(df_0_6))
width = 0.35
ax3.bar(x - width/2, df_0_6['week_pnl_cnh']/1000, width, label='max(0,6)', color='steelblue', alpha=0.8)
ax3.bar(x + width/2, df_2_6['week_pnl_cnh']/1000, width, label='max(2,6)', color='coral', alpha=0.8)
ax3.set_xlabel('Week', fontsize=12)
ax3.set_ylabel('Weekly PnL (K CNH)', fontsize=12)
ax3.set_title('Weekly PnL Side-by-Side Comparison', fontsize=14, fontweight='bold')
ax3.legend(loc='upper right', fontsize=10)
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_xticks(x[::4])
ax3.set_xticklabels([str(i+1) for i in x[::4]])

# Plot 4: Summary
ax4 = axes[1, 1]
ax4.axis('off')
total_0_6 = df_0_6['week_pnl_cnh'].sum()
total_2_6 = df_2_6['week_pnl_cnh'].sum()
avg_0_6 = df_0_6['week_pnl_cnh'].mean()
avg_2_6 = df_2_6['week_pnl_cnh'].mean()
diff_total = total_0_6 - total_2_6
diff_pct = (total_0_6 / total_2_6 - 1) * 100 if total_2_6 != 0 else 0
winrate_0_6 = df_0_6['win_rate'].mean() * 100
winrate_2_6 = df_2_6['win_rate'].mean() * 100

summary = f'''
{'='*55}
Strategy Comparison Summary
spread={SPREAD_BPS}bps, weeks={len(df_0_6)}
{'='*55}

                     max(0,6)        max(2,6)          Diff
{'-'*55}
Total PnL (CNH)    {total_0_6:>12,.0f}  {total_2_6:>12,.0f}   {diff_total:>+12,.0f}
Avg/Week (CNH)     {avg_0_6:>12,.0f}  {avg_2_6:>12,.0f}   {avg_0_6-avg_2_6:>+12,.0f}
Win Rate (%)       {winrate_0_6:>12.1f}  {winrate_2_6:>12.1f}   {winrate_0_6-winrate_2_6:>+12.1f}
{'-'*55}

max(0,6) Relative Advantage: {diff_pct:+.2f}%
Annualized Diff (52w): {(avg_0_6-avg_2_6)*52:+,.0f} CNH

Conclusion: {'max(0,6) is BETTER' if diff_total > 0 else 'max(2,6) is BETTER'}
'''
ax4.text(0.05, 0.95, summary, transform=ax4.transAxes, fontsize=11, va='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

plt.tight_layout()
save_path = os.path.join(OUTPUT_DIR, 'strategy_comparison_max06_vs_max26.png')
plt.savefig(save_path, dpi=150, bbox_inches='tight')
print(f'\nChart saved: {save_path}')
plt.close()

# Print final summary
print("\n" + "="*60)
print("FINAL COMPARISON SUMMARY")
print("="*60)
print(f"\n{'Strategy':<15} {'Total PnL':<15} {'Avg/Week':<12} {'Win Rate':<10}")
print("-"*60)
print(f"{'max(0,6)':<15} {total_0_6:>12,.0f}   {avg_0_6:>10,.0f}   {winrate_0_6:>8.1f}%")
print(f"{'max(2,6)':<15} {total_2_6:>12,.0f}   {avg_2_6:>10,.0f}   {winrate_2_6:>8.1f}%")
print("-"*60)
print(f"{'Difference':<15} {diff_total:>+12,.0f}   {avg_0_6-avg_2_6:>+10,.0f}   {winrate_0_6-winrate_2_6:>+8.1f}%")
print("="*60)
