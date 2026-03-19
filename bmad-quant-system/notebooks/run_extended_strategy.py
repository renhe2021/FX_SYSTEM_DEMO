"""
Extended Strategy Analysis: max(10:00, 10:30, 11:00, ... 18:00)
Compare with existing max(0,6) and max(2,6) strategies
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties

# Font setup
font_path = r'C:\Windows\Fonts\msyh.ttc'
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\simhei.ttf'

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

USD_WEEKLY_VOLUME = 60_000_000
JPY_WEEKLY_VOLUME = 4_000_000_000

print('='*70)
print('Extended Strategy: max(10:00, 10:30, 11:00, ... 18:00)')
print('='*70)

# Load data
all_files = os.listdir(OUTPUT_DIR)
usdcnh_files = [f for f in all_files if 'USDCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]
jpycnh_files = [f for f in all_files if 'JPYCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]

print(f'Loading USDCNH: {usdcnh_files[0]}')
df_usdcnh = pd.read_excel(os.path.join(OUTPUT_DIR, usdcnh_files[0]))
df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
df_usdcnh.set_index('timestamp', inplace=True)

print(f'Loading JPYCNH: {jpycnh_files[0]}')
df_jpycnh = pd.read_excel(os.path.join(OUTPUT_DIR, jpycnh_files[0]))
df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
df_jpycnh.set_index('timestamp', inplace=True)

# Prepare Saturday data
for df in [df_usdcnh, df_jpycnh]:
    df['weekday'] = df.index.dayofweek
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    if 'mid' not in df.columns:
        df['mid'] = (df['bid'] + df['ask']) / 2

# Filter Saturday data (extended to 18:00)
usdcnh_sat = df_usdcnh[(df_usdcnh['weekday'] == 5) & (df_usdcnh['hour'] <= 18)].copy()
jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 18)].copy()

common_dates = sorted(set(usdcnh_sat['date'].unique()) & set(jpycnh_sat['date'].unique()))
print(f'Common dates: {len(common_dates)} weeks')

# Define time points: 10:00, 10:30, 11:00, ... 18:00
time_points = []
for h in range(10, 19):  # 10 to 18
    time_points.append((h, 0))   # :00
    if h < 18:  # No 18:30
        time_points.append((h, 30))  # :30

print(f'\nTime points for extended strategy ({len(time_points)} points):')
for h, m in time_points:
    print(f'  {h:02d}:{m:02d}', end='')
print('\n')

# Calculate weekly PnL
weekly_data = []

for sat_date in common_dates:
    usdcnh_day = usdcnh_sat[usdcnh_sat['date'] == sat_date]
    jpycnh_day = jpycnh_sat[jpycnh_sat['date'] == sat_date]
    
    if usdcnh_day.empty or jpycnh_day.empty:
        continue
    
    # Get prices at specific hours (existing strategy)
    usdcnh_h0 = usdcnh_day[usdcnh_day['hour'] == 0]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 0]) > 0 else np.nan
    usdcnh_h2 = usdcnh_day[usdcnh_day['hour'] == 2]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 2]) > 0 else np.nan
    usdcnh_h6 = usdcnh_day[usdcnh_day['hour'] == 6]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 6]) > 0 else np.nan
    
    # Get prices at extended time points
    extended_prices = []
    for h, m in time_points:
        mask = (usdcnh_day['hour'] == h) & (usdcnh_day['minute'] >= m) & (usdcnh_day['minute'] < m + 30)
        if mask.sum() > 0:
            price = usdcnh_day[mask]['mid'].mean()
            extended_prices.append(price)
    
    # Skip if missing data
    if pd.isna(usdcnh_h0) or pd.isna(usdcnh_h2) or pd.isna(usdcnh_h6) or len(extended_prices) < 5:
        continue
    
    jpycnh_avg = jpycnh_day['mid'].mean()
    jpycnh_per_jpy = jpycnh_avg / 100
    usdcnh_avg = usdcnh_day['mid'].mean()
    
    # Strategies
    ref_max_0_6 = max(usdcnh_h0, usdcnh_h6)           # Current: max(0,6)
    ref_max_2_6 = max(usdcnh_h2, usdcnh_h6)           # Alternative: max(2,6)
    ref_max_0_2_6 = max(usdcnh_h0, usdcnh_h2, usdcnh_h6)  # max(0,2,6)
    ref_max_extended = max(extended_prices)           # Extended: max(10:00 ~ 18:00)
    
    # Find which time point had the max
    max_extended_idx = extended_prices.index(ref_max_extended)
    max_extended_time = time_points[max_extended_idx] if max_extended_idx < len(time_points) else (0, 0)
    
    # === Extended vs max(0,6) ===
    usd_diff_ext_vs_06 = (ref_max_extended - ref_max_0_6) * USD_WEEKLY_VOLUME
    jpy_diff_ext_vs_06 = (jpycnh_per_jpy * (ref_max_extended / usdcnh_avg) - jpycnh_per_jpy * (ref_max_0_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    # === Extended vs max(2,6) ===
    usd_diff_ext_vs_26 = (ref_max_extended - ref_max_2_6) * USD_WEEKLY_VOLUME
    jpy_diff_ext_vs_26 = (jpycnh_per_jpy * (ref_max_extended / usdcnh_avg) - jpycnh_per_jpy * (ref_max_2_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    # === Extended vs max(0,2,6) ===
    usd_diff_ext_vs_026 = (ref_max_extended - ref_max_0_2_6) * USD_WEEKLY_VOLUME
    jpy_diff_ext_vs_026 = (jpycnh_per_jpy * (ref_max_extended / usdcnh_avg) - jpycnh_per_jpy * (ref_max_0_2_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    weekly_data.append({
        'date': sat_date,
        'ref_max_0_6': ref_max_0_6,
        'ref_max_2_6': ref_max_2_6,
        'ref_max_0_2_6': ref_max_0_2_6,
        'ref_max_extended': ref_max_extended,
        'max_extended_hour': max_extended_time[0],
        'max_extended_minute': max_extended_time[1],
        'n_extended_points': len(extended_prices),
        # vs max(0,6)
        'usd_diff_ext_vs_06': usd_diff_ext_vs_06,
        'jpy_diff_ext_vs_06': jpy_diff_ext_vs_06,
        'total_diff_ext_vs_06': usd_diff_ext_vs_06 + jpy_diff_ext_vs_06,
        # vs max(2,6)
        'usd_diff_ext_vs_26': usd_diff_ext_vs_26,
        'jpy_diff_ext_vs_26': jpy_diff_ext_vs_26,
        'total_diff_ext_vs_26': usd_diff_ext_vs_26 + jpy_diff_ext_vs_26,
        # vs max(0,2,6)
        'usd_diff_ext_vs_026': usd_diff_ext_vs_026,
        'jpy_diff_ext_vs_026': jpy_diff_ext_vs_026,
        'total_diff_ext_vs_026': usd_diff_ext_vs_026 + jpy_diff_ext_vs_026,
    })

df = pd.DataFrame(weekly_data)
print(f'Weeks with valid data: {len(df)}')

# Cumulative
df['cum_ext_vs_06'] = df['total_diff_ext_vs_06'].cumsum()
df['cum_ext_vs_26'] = df['total_diff_ext_vs_26'].cumsum()
df['cum_ext_vs_026'] = df['total_diff_ext_vs_026'].cumsum()

# BPS calculation
df['bps_ext_vs_06'] = (df['ref_max_extended'] - df['ref_max_0_6']) / df['ref_max_0_6'] * 10000
df['bps_ext_vs_26'] = (df['ref_max_extended'] - df['ref_max_2_6']) / df['ref_max_2_6'] * 10000
df['bps_ext_vs_026'] = (df['ref_max_extended'] - df['ref_max_0_2_6']) / df['ref_max_0_2_6'] * 10000

print('\n' + '='*70)
print('RESULTS: Extended Strategy max(10:00~18:00) vs Existing Strategies')
print('='*70)

print(f'\nPeriod: {df["date"].iloc[0]} ~ {df["date"].iloc[-1]}')
print(f'Weeks: {len(df)}')

print('\n--- Cumulative PnL Difference (CNH) ---')
print(f'{"Comparison":<35} {"USD":>15} {"JPY":>15} {"Total":>15}')
print('-'*80)
print(f'{"Extended vs max(0,6)":<35} {df["usd_diff_ext_vs_06"].sum():>12,.0f} {df["jpy_diff_ext_vs_06"].sum():>12,.0f} {df["cum_ext_vs_06"].iloc[-1]:>12,.0f}')
print(f'{"Extended vs max(2,6)":<35} {df["usd_diff_ext_vs_26"].sum():>12,.0f} {df["jpy_diff_ext_vs_26"].sum():>12,.0f} {df["cum_ext_vs_26"].iloc[-1]:>12,.0f}')
print(f'{"Extended vs max(0,2,6)":<35} {df["usd_diff_ext_vs_026"].sum():>12,.0f} {df["jpy_diff_ext_vs_026"].sum():>12,.0f} {df["cum_ext_vs_026"].iloc[-1]:>12,.0f}')
print('-'*80)

print('\n--- BPS Difference ---')
print(f'{"Comparison":<35} {"Mean":>10} {"Median":>10} {"Max":>10} {"Min":>10}')
print('-'*80)
print(f'{"Extended vs max(0,6)":<35} {df["bps_ext_vs_06"].mean():>8.2f}bp {df["bps_ext_vs_06"].median():>8.2f}bp {df["bps_ext_vs_06"].max():>8.2f}bp {df["bps_ext_vs_06"].min():>8.2f}bp')
print(f'{"Extended vs max(2,6)":<35} {df["bps_ext_vs_26"].mean():>8.2f}bp {df["bps_ext_vs_26"].median():>8.2f}bp {df["bps_ext_vs_26"].max():>8.2f}bp {df["bps_ext_vs_26"].min():>8.2f}bp')
print(f'{"Extended vs max(0,2,6)":<35} {df["bps_ext_vs_026"].mean():>8.2f}bp {df["bps_ext_vs_026"].median():>8.2f}bp {df["bps_ext_vs_026"].max():>8.2f}bp {df["bps_ext_vs_026"].min():>8.2f}bp')
print('-'*80)

print('\n--- Annualized (52 weeks) ---')
avg_weekly_ext_vs_06 = df['total_diff_ext_vs_06'].mean()
avg_weekly_ext_vs_26 = df['total_diff_ext_vs_26'].mean()
avg_weekly_ext_vs_026 = df['total_diff_ext_vs_026'].mean()
print(f'Extended vs max(0,6):  {avg_weekly_ext_vs_06 * 52 / 1e6:.2f}M CNH/year ({df["bps_ext_vs_06"].mean() * 52:.1f} bps/year)')
print(f'Extended vs max(2,6):  {avg_weekly_ext_vs_26 * 52 / 1e6:.2f}M CNH/year ({df["bps_ext_vs_26"].mean() * 52:.1f} bps/year)')
print(f'Extended vs max(0,2,6): {avg_weekly_ext_vs_026 * 52 / 1e6:.2f}M CNH/year ({df["bps_ext_vs_026"].mean() * 52:.1f} bps/year)')

# Best time analysis
print('\n' + '='*70)
print('Which time point had the MAX most often?')
print('='*70)
time_counts = df.groupby(['max_extended_hour', 'max_extended_minute']).size().sort_values(ascending=False)
print('\nTop time points:')
for (h, m), count in time_counts.head(10).items():
    pct = count / len(df) * 100
    print(f'  {h:02d}:{m:02d}  -> {count} weeks ({pct:.1f}%)')

# Save results
df.to_excel(os.path.join(OUTPUT_DIR, 'strategy_extended_analysis.xlsx'), index=False)
print(f'\nData saved: {os.path.join(OUTPUT_DIR, "strategy_extended_analysis.xlsx")}')

# Plot
try:
    chinese_font = FontProperties(fname=font_path, size=12)
    chinese_font_title = FontProperties(fname=font_path, size=14)
    chinese_font_legend = FontProperties(fname=font_path, size=11)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    dates = pd.to_datetime(df['date'])
    
    # Plot 1: Reference prices comparison
    ax1 = axes[0, 0]
    ax1.plot(dates, df['ref_max_0_6'], 'b-', linewidth=2, marker='o', markersize=4, alpha=0.7)
    ax1.plot(dates, df['ref_max_2_6'], 'g-', linewidth=2, marker='s', markersize=4, alpha=0.7)
    ax1.plot(dates, df['ref_max_0_2_6'], 'orange', linewidth=2, marker='^', markersize=4, alpha=0.7)
    ax1.plot(dates, df['ref_max_extended'], 'r-', linewidth=2.5, marker='*', markersize=8)
    ax1.set_xlabel('Date', fontproperties=chinese_font)
    ax1.set_ylabel('USDCNH Reference', fontproperties=chinese_font)
    ax1.set_title('Reference Price Comparison\nmax(0,6) vs max(2,6) vs max(0,2,6) vs max(10:00~18:00)', fontproperties=chinese_font_title)
    ax1.legend(['max(0,6)', 'max(2,6)', 'max(0,2,6)', 'max(10:00~18:00)'], loc='upper left', prop=chinese_font_legend)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 2: Cumulative PnL vs all baselines
    ax2 = axes[0, 1]
    ax2.plot(dates, df['cum_ext_vs_06']/1e6, 'b-', linewidth=2.5, marker='o', markersize=5)
    ax2.plot(dates, df['cum_ext_vs_26']/1e6, 'g-', linewidth=2.5, marker='s', markersize=5)
    ax2.plot(dates, df['cum_ext_vs_026']/1e6, 'r-', linewidth=2.5, marker='^', markersize=5)
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax2.fill_between(dates, 0, df['cum_ext_vs_026']/1e6, where=(df['cum_ext_vs_026'] >= 0), color='green', alpha=0.1)
    
    ax2.annotate(f'{df["cum_ext_vs_06"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_ext_vs_06'].iloc[-1]/1e6), 
                xytext=(5, 0), textcoords='offset points', fontsize=10, color='blue', fontweight='bold')
    ax2.annotate(f'{df["cum_ext_vs_26"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_ext_vs_26'].iloc[-1]/1e6), 
                xytext=(5, 0), textcoords='offset points', fontsize=10, color='green', fontweight='bold')
    ax2.annotate(f'{df["cum_ext_vs_026"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_ext_vs_026'].iloc[-1]/1e6), 
                xytext=(5, 5), textcoords='offset points', fontsize=10, color='red', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    ax2.set_xlabel('Date', fontproperties=chinese_font)
    ax2.set_ylabel('Cumulative PnL Diff (M CNH)', fontproperties=chinese_font)
    ax2.set_title('Cumulative PnL: Extended Strategy vs Others', fontproperties=chinese_font_title)
    ax2.legend(['vs max(0,6)', 'vs max(2,6)', 'vs max(0,2,6)'], loc='upper left', prop=chinese_font_legend)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 3: Best time distribution
    ax3 = axes[1, 0]
    time_labels = [f'{h:02d}:{m:02d}' for h, m in time_points]
    time_freq = []
    for h, m in time_points:
        count = len(df[(df['max_extended_hour'] == h) & (df['max_extended_minute'] == m)])
        time_freq.append(count)
    
    bars = ax3.bar(range(len(time_points)), time_freq, color='steelblue', alpha=0.7)
    ax3.set_xticks(range(len(time_points)))
    ax3.set_xticklabels(time_labels, rotation=90, fontsize=8)
    ax3.set_xlabel('Time Point', fontproperties=chinese_font)
    ax3.set_ylabel('Frequency (weeks)', fontproperties=chinese_font)
    ax3.set_title('Which time had the MAX price?', fontproperties=chinese_font_title)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Highlight top bars
    max_freq = max(time_freq)
    for i, freq in enumerate(time_freq):
        if freq == max_freq:
            bars[i].set_color('red')
    
    # Plot 4: Summary stats
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = f"""
SUMMARY: Extended Strategy max(10:00 ~ 18:00)
{'='*55}

Period: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}
Weeks: {len(df)}
Time points: {len(time_points)} (every 30min from 10:00 to 18:00)

{'='*55}
Cumulative PnL Difference
{'='*55}

Extended vs max(0,6):    {df['cum_ext_vs_06'].iloc[-1]:>12,.0f} CNH ({df['cum_ext_vs_06'].iloc[-1]/1e6:.2f}M)
Extended vs max(2,6):    {df['cum_ext_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_ext_vs_26'].iloc[-1]/1e6:.2f}M)
Extended vs max(0,2,6):  {df['cum_ext_vs_026'].iloc[-1]:>12,.0f} CNH ({df['cum_ext_vs_026'].iloc[-1]/1e6:.2f}M)

{'='*55}
Average BPS Improvement
{'='*55}

vs max(0,6):   +{df['bps_ext_vs_06'].mean():.2f} bps/week  (~{df['bps_ext_vs_06'].mean()*52:.0f} bps/year)
vs max(2,6):   +{df['bps_ext_vs_26'].mean():.2f} bps/week  (~{df['bps_ext_vs_26'].mean()*52:.0f} bps/year)
vs max(0,2,6): +{df['bps_ext_vs_026'].mean():.2f} bps/week  (~{df['bps_ext_vs_026'].mean()*52:.0f} bps/year)

{'='*55}
Annualized Extra Revenue (52 weeks)
{'='*55}

vs max(0,6):   ~{avg_weekly_ext_vs_06 * 52 / 1e6:.2f}M CNH/year
vs max(2,6):   ~{avg_weekly_ext_vs_26 * 52 / 1e6:.2f}M CNH/year
vs max(0,2,6): ~{avg_weekly_ext_vs_026 * 52 / 1e6:.2f}M CNH/year
"""
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', fontproperties=chinese_font,
             family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, 'strategy_extended_comparison.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f'Chart saved: {save_path}')
    plt.close()
    
except Exception as e:
    print(f'Chart error: {e}')

print('\n' + '='*70)
print('CONCLUSION')
print('='*70)
print(f'\nExtended strategy max(10:00~18:00) improvement:')
print(f'  vs max(0,6):   +{df["bps_ext_vs_06"].mean():.2f} bps/week -> {df["cum_ext_vs_06"].iloc[-1]/1e6:.2f}M CNH total')
print(f'  vs max(2,6):   +{df["bps_ext_vs_26"].mean():.2f} bps/week -> {df["cum_ext_vs_26"].iloc[-1]/1e6:.2f}M CNH total')
print(f'  vs max(0,2,6): +{df["bps_ext_vs_026"].mean():.2f} bps/week -> {df["cum_ext_vs_026"].iloc[-1]/1e6:.2f}M CNH total')
print('='*70)
