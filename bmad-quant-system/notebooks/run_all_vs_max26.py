"""
All Strategies Benchmarked Against max(2,6)
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties

font_path = r'C:\Windows\Fonts\msyh.ttc'
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\simhei.ttf'

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

USD_WEEKLY_VOLUME = 60_000_000
JPY_WEEKLY_VOLUME = 4_000_000_000

print('='*70)
print('All Strategies Benchmarked Against max(2,6)')
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

# Prepare data
for df in [df_usdcnh, df_jpycnh]:
    df['weekday'] = df.index.dayofweek
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    if 'mid' not in df.columns:
        df['mid'] = (df['bid'] + df['ask']) / 2

# Filter data
usdcnh_fri = df_usdcnh[(df_usdcnh['weekday'] == 4) & (df_usdcnh['hour'] >= 22)].copy()
usdcnh_sat = df_usdcnh[(df_usdcnh['weekday'] == 5) & (df_usdcnh['hour'] <= 6)].copy()
jpycnh_fri = df_jpycnh[(df_jpycnh['weekday'] == 4) & (df_jpycnh['hour'] >= 22)].copy()
jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 6)].copy()

# Extended time points: Fri 22:00 ~ Sat 06:00
time_points = []
for h in range(22, 24):
    time_points.append(('Fri', h, 0))
    time_points.append(('Fri', h, 30))
for h in range(0, 7):
    time_points.append(('Sat', h, 0))
    if h < 6:
        time_points.append(('Sat', h, 30))

sat_dates = sorted(usdcnh_sat['date'].unique())
print(f'Total weeks: {len(sat_dates)}')

# Calculate all strategies
weekly_data = []

for sat_date in sat_dates:
    fri_date = (pd.to_datetime(sat_date) - pd.Timedelta(days=1)).date()
    
    usdcnh_fri_day = usdcnh_fri[usdcnh_fri['date'] == fri_date]
    usdcnh_sat_day = usdcnh_sat[usdcnh_sat['date'] == sat_date]
    jpycnh_fri_day = jpycnh_fri[jpycnh_fri['date'] == fri_date]
    jpycnh_sat_day = jpycnh_sat[jpycnh_sat['date'] == sat_date]
    
    if usdcnh_sat_day.empty:
        continue
    
    # Get hourly prices
    usdcnh_h0 = usdcnh_sat_day[usdcnh_sat_day['hour'] == 0]['mid'].mean() if len(usdcnh_sat_day[usdcnh_sat_day['hour'] == 0]) > 0 else np.nan
    usdcnh_h2 = usdcnh_sat_day[usdcnh_sat_day['hour'] == 2]['mid'].mean() if len(usdcnh_sat_day[usdcnh_sat_day['hour'] == 2]) > 0 else np.nan
    usdcnh_h6 = usdcnh_sat_day[usdcnh_sat_day['hour'] == 6]['mid'].mean() if len(usdcnh_sat_day[usdcnh_sat_day['hour'] == 6]) > 0 else np.nan
    
    # Extended prices
    extended_prices = []
    for day, h, m in time_points:
        data = usdcnh_fri_day if day == 'Fri' else usdcnh_sat_day
        mask = (data['hour'] == h) & (data['minute'] >= m) & (data['minute'] < m + 30)
        if mask.sum() > 0:
            extended_prices.append(data[mask]['mid'].mean())
    
    if pd.isna(usdcnh_h0) or pd.isna(usdcnh_h2) or pd.isna(usdcnh_h6) or len(extended_prices) < 5:
        continue
    
    # JPYCNH
    jpycnh_data = pd.concat([jpycnh_fri_day, jpycnh_sat_day]) if not jpycnh_fri_day.empty else jpycnh_sat_day
    if jpycnh_data.empty:
        continue
    jpycnh_avg = jpycnh_data['mid'].mean()
    jpycnh_per_jpy = jpycnh_avg / 100
    
    usdcnh_data = pd.concat([usdcnh_fri_day, usdcnh_sat_day]) if not usdcnh_fri_day.empty else usdcnh_sat_day
    usdcnh_avg = usdcnh_data['mid'].mean()
    
    # All strategies
    ref_max_2_6 = max(usdcnh_h2, usdcnh_h6)              # BASELINE
    ref_max_0_6 = max(usdcnh_h0, usdcnh_h6)
    ref_max_0_2_6 = max(usdcnh_h0, usdcnh_h2, usdcnh_h6)
    ref_extended = max(extended_prices)
    
    # All vs max(2,6)
    def calc_pnl(ref_new, ref_base):
        usd_diff = (ref_new - ref_base) * USD_WEEKLY_VOLUME
        jpy_diff = (jpycnh_per_jpy * (ref_new / usdcnh_avg) - jpycnh_per_jpy * (ref_base / usdcnh_avg)) * JPY_WEEKLY_VOLUME
        return usd_diff, jpy_diff, usd_diff + jpy_diff
    
    usd_06, jpy_06, total_06 = calc_pnl(ref_max_0_6, ref_max_2_6)
    usd_026, jpy_026, total_026 = calc_pnl(ref_max_0_2_6, ref_max_2_6)
    usd_ext, jpy_ext, total_ext = calc_pnl(ref_extended, ref_max_2_6)
    
    weekly_data.append({
        'date': sat_date,
        'ref_max_2_6': ref_max_2_6,
        'ref_max_0_6': ref_max_0_6,
        'ref_max_0_2_6': ref_max_0_2_6,
        'ref_extended': ref_extended,
        # max(0,6) vs max(2,6)
        'usd_06_vs_26': usd_06, 'jpy_06_vs_26': jpy_06, 'total_06_vs_26': total_06,
        # max(0,2,6) vs max(2,6)
        'usd_026_vs_26': usd_026, 'jpy_026_vs_26': jpy_026, 'total_026_vs_26': total_026,
        # Extended vs max(2,6)
        'usd_ext_vs_26': usd_ext, 'jpy_ext_vs_26': jpy_ext, 'total_ext_vs_26': total_ext,
    })

df = pd.DataFrame(weekly_data)
print(f'Valid weeks: {len(df)}')

# Cumulative
df['cum_06_vs_26'] = df['total_06_vs_26'].cumsum()
df['cum_026_vs_26'] = df['total_026_vs_26'].cumsum()
df['cum_ext_vs_26'] = df['total_ext_vs_26'].cumsum()

# BPS
df['bps_06_vs_26'] = (df['ref_max_0_6'] - df['ref_max_2_6']) / df['ref_max_2_6'] * 10000
df['bps_026_vs_26'] = (df['ref_max_0_2_6'] - df['ref_max_2_6']) / df['ref_max_2_6'] * 10000
df['bps_ext_vs_26'] = (df['ref_extended'] - df['ref_max_2_6']) / df['ref_max_2_6'] * 10000

print('\n' + '='*70)
print('ALL STRATEGIES vs max(2,6) BENCHMARK')
print('='*70)

print(f'\nPeriod: {df["date"].iloc[0]} ~ {df["date"].iloc[-1]}')
print(f'Weeks: {len(df)}')

print('\n' + '-'*70)
print('CUMULATIVE PnL DIFFERENCE vs max(2,6)')
print('-'*70)
print(f'{"Strategy":<30} {"USD":>15} {"JPY":>15} {"Total":>15}')
print('-'*70)
print(f'{"max(0,6)":<30} {df["usd_06_vs_26"].sum():>12,.0f} {df["jpy_06_vs_26"].sum():>12,.0f} {df["cum_06_vs_26"].iloc[-1]:>12,.0f}')
print(f'{"max(0,2,6)":<30} {df["usd_026_vs_26"].sum():>12,.0f} {df["jpy_026_vs_26"].sum():>12,.0f} {df["cum_026_vs_26"].iloc[-1]:>12,.0f}')
print(f'{"max(Fri22~Sat06)":<30} {df["usd_ext_vs_26"].sum():>12,.0f} {df["jpy_ext_vs_26"].sum():>12,.0f} {df["cum_ext_vs_26"].iloc[-1]:>12,.0f}')
print('-'*70)

print('\n' + '-'*70)
print('BPS DIFFERENCE vs max(2,6)')
print('-'*70)
print(f'{"Strategy":<30} {"Mean":>10} {"Median":>10} {"Max":>10} {"Min":>10}')
print('-'*70)
print(f'{"max(0,6)":<30} {df["bps_06_vs_26"].mean():>8.2f}bp {df["bps_06_vs_26"].median():>8.2f}bp {df["bps_06_vs_26"].max():>8.2f}bp {df["bps_06_vs_26"].min():>8.2f}bp')
print(f'{"max(0,2,6)":<30} {df["bps_026_vs_26"].mean():>8.2f}bp {df["bps_026_vs_26"].median():>8.2f}bp {df["bps_026_vs_26"].max():>8.2f}bp {df["bps_026_vs_26"].min():>8.2f}bp')
print(f'{"max(Fri22~Sat06)":<30} {df["bps_ext_vs_26"].mean():>8.2f}bp {df["bps_ext_vs_26"].median():>8.2f}bp {df["bps_ext_vs_26"].max():>8.2f}bp {df["bps_ext_vs_26"].min():>8.2f}bp')
print('-'*70)

print('\n' + '-'*70)
print('ANNUALIZED (52 weeks) vs max(2,6)')
print('-'*70)
print(f'{"Strategy":<30} {"CNH/year":>15} {"bps/year":>12}')
print('-'*70)
print(f'{"max(0,6)":<30} {df["total_06_vs_26"].mean() * 52 / 1e6:>12.2f}M {df["bps_06_vs_26"].mean() * 52:>10.1f}bp')
print(f'{"max(0,2,6)":<30} {df["total_026_vs_26"].mean() * 52 / 1e6:>12.2f}M {df["bps_026_vs_26"].mean() * 52:>10.1f}bp')
print(f'{"max(Fri22~Sat06)":<30} {df["total_ext_vs_26"].mean() * 52 / 1e6:>12.2f}M {df["bps_ext_vs_26"].mean() * 52:>10.1f}bp')
print('-'*70)

# Save
df.to_excel(os.path.join(OUTPUT_DIR, 'all_strategies_vs_max26.xlsx'), index=False)

# Plot
try:
    chinese_font = FontProperties(fname=font_path, size=12)
    chinese_font_title = FontProperties(fname=font_path, size=14)
    chinese_font_legend = FontProperties(fname=font_path, size=11)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    dates = pd.to_datetime(df['date'])
    
    # Plot 1: Cumulative PnL vs max(2,6)
    ax1 = axes[0, 0]
    ax1.plot(dates, df['cum_06_vs_26']/1e6, 'b-', linewidth=2.5, marker='o', markersize=5)
    ax1.plot(dates, df['cum_026_vs_26']/1e6, 'orange', linewidth=2.5, marker='s', markersize=5)
    ax1.plot(dates, df['cum_ext_vs_26']/1e6, 'r-', linewidth=3, marker='^', markersize=6)
    ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax1.fill_between(dates, 0, df['cum_ext_vs_26']/1e6, where=(df['cum_ext_vs_26'] >= 0), color='green', alpha=0.1)
    
    ax1.annotate(f'{df["cum_06_vs_26"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_06_vs_26'].iloc[-1]/1e6), 
                xytext=(5, -10), textcoords='offset points', fontsize=10, color='blue', fontweight='bold')
    ax1.annotate(f'{df["cum_026_vs_26"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_026_vs_26'].iloc[-1]/1e6), 
                xytext=(5, 0), textcoords='offset points', fontsize=10, color='orange', fontweight='bold')
    ax1.annotate(f'{df["cum_ext_vs_26"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_ext_vs_26'].iloc[-1]/1e6), 
                xytext=(5, 5), textcoords='offset points', fontsize=11, color='red', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    ax1.set_xlabel('Date', fontproperties=chinese_font)
    ax1.set_ylabel('Cumulative PnL vs max(2,6) (M CNH)', fontproperties=chinese_font)
    ax1.set_title('Cumulative PnL vs max(2,6) Benchmark', fontproperties=chinese_font_title)
    ax1.legend(['max(0,6)', 'max(0,2,6)', 'max(Fri22~Sat06)'], loc='upper left', prop=chinese_font_legend)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 2: Reference Prices
    ax2 = axes[0, 1]
    ax2.plot(dates, df['ref_max_2_6'], 'gray', linewidth=3, marker='D', markersize=6, label='max(2,6) [BASELINE]')
    ax2.plot(dates, df['ref_max_0_6'], 'b-', linewidth=2, marker='o', markersize=4, alpha=0.7)
    ax2.plot(dates, df['ref_max_0_2_6'], 'orange', linewidth=2, marker='s', markersize=4, alpha=0.7)
    ax2.plot(dates, df['ref_extended'], 'r-', linewidth=2.5, marker='^', markersize=5)
    ax2.set_xlabel('Date', fontproperties=chinese_font)
    ax2.set_ylabel('USDCNH Reference Price', fontproperties=chinese_font)
    ax2.set_title('Reference Price Comparison', fontproperties=chinese_font_title)
    ax2.legend(['max(2,6) BASELINE', 'max(0,6)', 'max(0,2,6)', 'max(Fri22~Sat06)'], loc='upper left', prop=chinese_font_legend)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 3: Weekly BPS difference bar chart
    ax3 = axes[1, 0]
    width = 0.25
    x = np.arange(len(df))
    ax3.bar(x - width, df['bps_06_vs_26'], width, label='max(0,6)', color='blue', alpha=0.7)
    ax3.bar(x, df['bps_026_vs_26'], width, label='max(0,2,6)', color='orange', alpha=0.7)
    ax3.bar(x + width, df['bps_ext_vs_26'], width, label='max(Fri22~Sat06)', color='red', alpha=0.7)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_xlabel('Week', fontproperties=chinese_font)
    ax3.set_ylabel('BPS vs max(2,6)', fontproperties=chinese_font)
    ax3.set_title('Weekly BPS Difference vs max(2,6)', fontproperties=chinese_font_title)
    ax3.legend(loc='upper left', prop=chinese_font_legend)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Plot 4: Summary Table
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = f"""
ALL STRATEGIES vs max(2,6) BENCHMARK
{'='*55}

Period: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}
Weeks: {len(df)}
Volume: USD 60M/wk, JPY 4B/wk

{'='*55}
CUMULATIVE PnL vs max(2,6)
{'='*55}

  max(0,6):        {df['cum_06_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_06_vs_26'].iloc[-1]/1e6:.2f}M)
  max(0,2,6):      {df['cum_026_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_026_vs_26'].iloc[-1]/1e6:.2f}M)
  max(Fri22~Sat06):{df['cum_ext_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_ext_vs_26'].iloc[-1]/1e6:.2f}M)

{'='*55}
AVERAGE BPS vs max(2,6)
{'='*55}

  max(0,6):         +{df['bps_06_vs_26'].mean():.2f} bps/week
  max(0,2,6):       +{df['bps_026_vs_26'].mean():.2f} bps/week
  max(Fri22~Sat06): +{df['bps_ext_vs_26'].mean():.2f} bps/week

{'='*55}
ANNUALIZED (52 weeks) vs max(2,6)
{'='*55}

  max(0,6):         +{df['total_06_vs_26'].mean()*52/1e6:.2f}M CNH/yr (+{df['bps_06_vs_26'].mean()*52:.0f}bp/yr)
  max(0,2,6):       +{df['total_026_vs_26'].mean()*52/1e6:.2f}M CNH/yr (+{df['bps_026_vs_26'].mean()*52:.0f}bp/yr)
  max(Fri22~Sat06): +{df['total_ext_vs_26'].mean()*52/1e6:.2f}M CNH/yr (+{df['bps_ext_vs_26'].mean()*52:.0f}bp/yr)

{'='*55}
BEST STRATEGY: max(Fri22~Sat06)
{'='*55}
"""
    
    ax4.text(0.02, 0.98, summary_text, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', fontproperties=chinese_font,
             family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, 'all_strategies_vs_max26.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f'\nChart saved: {save_path}')
    plt.close()
    
except Exception as e:
    print(f'Chart error: {e}')

print('\n' + '='*70)
print('FINAL RANKING vs max(2,6) BENCHMARK')
print('='*70)
print(f'\n{"Rank":<6} {"Strategy":<25} {"Annualized":>15} {"bps/year":>12}')
print('-'*60)
print(f'{"1":<6} {"max(Fri22~Sat06)":<25} {df["total_ext_vs_26"].mean()*52/1e6:>12.2f}M {df["bps_ext_vs_26"].mean()*52:>10.1f}bp')
print(f'{"2":<6} {"max(0,2,6)":<25} {df["total_026_vs_26"].mean()*52/1e6:>12.2f}M {df["bps_026_vs_26"].mean()*52:>10.1f}bp')
print(f'{"3":<6} {"max(0,6)":<25} {df["total_06_vs_26"].mean()*52/1e6:>12.2f}M {df["bps_06_vs_26"].mean()*52:>10.1f}bp')
print(f'{"4":<6} {"max(2,6) [BASELINE]":<25} {"0.00":>12}M {"0.0":>10}bp')
print('-'*60)
print('='*70)
