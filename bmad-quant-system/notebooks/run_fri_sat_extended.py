"""
Extended Strategy Analysis: max(Friday 22:30 ~ Saturday 06:00)
Trading window: Fri 22:30 ~ Sat 01:30 (every 30min), Reference: Sat 02:00
Extended analysis covers wider window for comparison purposes.
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
print('Extended Strategy: max(Fri 22:00 ~ Sat 06:00) every 30min')
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

# Filter Friday evening (22:00-23:59) and Saturday morning (00:00-06:00)
usdcnh_fri = df_usdcnh[(df_usdcnh['weekday'] == 4) & (df_usdcnh['hour'] >= 22)].copy()  # Friday 22:00+
usdcnh_sat = df_usdcnh[(df_usdcnh['weekday'] == 5) & (df_usdcnh['hour'] <= 6)].copy()   # Saturday 00:00-06:00
jpycnh_fri = df_jpycnh[(df_jpycnh['weekday'] == 4) & (df_jpycnh['hour'] >= 22)].copy()
jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 6)].copy()

# Define time points: Fri 22:00, 22:30, 23:00, 23:30, Sat 00:00, 00:30, ... 06:00
time_points = []
# Friday evening
for h in range(22, 24):
    time_points.append(('Fri', h, 0))
    time_points.append(('Fri', h, 30))
# Saturday morning
for h in range(0, 7):
    time_points.append(('Sat', h, 0))
    if h < 6:
        time_points.append(('Sat', h, 30))

print(f'\nTime points ({len(time_points)} points):')
print('  Friday: ', end='')
for day, h, m in time_points:
    if day == 'Fri':
        print(f'{h:02d}:{m:02d} ', end='')
print('\n  Saturday: ', end='')
for day, h, m in time_points:
    if day == 'Sat':
        print(f'{h:02d}:{m:02d} ', end='')
print('\n')

# Get unique Saturday dates (use as week identifier)
sat_dates = sorted(usdcnh_sat['date'].unique())
print(f'Saturday dates: {len(sat_dates)}')

# Calculate weekly PnL
weekly_data = []

for sat_date in sat_dates:
    # Get Friday date (day before Saturday)
    fri_date = pd.to_datetime(sat_date) - pd.Timedelta(days=1)
    fri_date = fri_date.date()
    
    # Filter data for this weekend
    usdcnh_fri_day = usdcnh_fri[usdcnh_fri['date'] == fri_date]
    usdcnh_sat_day = usdcnh_sat[usdcnh_sat['date'] == sat_date]
    jpycnh_fri_day = jpycnh_fri[jpycnh_fri['date'] == fri_date]
    jpycnh_sat_day = jpycnh_sat[jpycnh_sat['date'] == sat_date]
    
    if usdcnh_sat_day.empty:
        continue
    
    # Get prices at each time point
    extended_prices = []
    extended_times = []
    
    for day, h, m in time_points:
        if day == 'Fri':
            data = usdcnh_fri_day
        else:
            data = usdcnh_sat_day
        
        # Get price at this time (within 30min window)
        mask = (data['hour'] == h) & (data['minute'] >= m) & (data['minute'] < m + 30)
        if mask.sum() > 0:
            price = data[mask]['mid'].mean()
            extended_prices.append(price)
            extended_times.append((day, h, m))
    
    # Get existing strategy prices
    usdcnh_h0 = usdcnh_sat_day[usdcnh_sat_day['hour'] == 0]['mid'].mean() if len(usdcnh_sat_day[usdcnh_sat_day['hour'] == 0]) > 0 else np.nan
    usdcnh_h2 = usdcnh_sat_day[usdcnh_sat_day['hour'] == 2]['mid'].mean() if len(usdcnh_sat_day[usdcnh_sat_day['hour'] == 2]) > 0 else np.nan
    usdcnh_h6 = usdcnh_sat_day[usdcnh_sat_day['hour'] == 6]['mid'].mean() if len(usdcnh_sat_day[usdcnh_sat_day['hour'] == 6]) > 0 else np.nan
    
    # Skip if not enough data
    if len(extended_prices) < 5 or pd.isna(usdcnh_h0) or pd.isna(usdcnh_h2) or pd.isna(usdcnh_h6):
        continue
    
    # JPYCNH
    jpycnh_data = pd.concat([jpycnh_fri_day, jpycnh_sat_day]) if not jpycnh_fri_day.empty else jpycnh_sat_day
    if jpycnh_data.empty:
        continue
    jpycnh_avg = jpycnh_data['mid'].mean()
    jpycnh_per_jpy = jpycnh_avg / 100
    
    # USDCNH avg for JPY adjustment
    usdcnh_data = pd.concat([usdcnh_fri_day, usdcnh_sat_day]) if not usdcnh_fri_day.empty else usdcnh_sat_day
    usdcnh_avg = usdcnh_data['mid'].mean()
    
    # Strategies
    ref_max_0_6 = max(usdcnh_h0, usdcnh_h6)
    ref_max_2_6 = max(usdcnh_h2, usdcnh_h6)
    ref_max_0_2_6 = max(usdcnh_h0, usdcnh_h2, usdcnh_h6)
    ref_max_extended = max(extended_prices)
    
    # Find which time had max
    max_idx = extended_prices.index(ref_max_extended)
    max_time = extended_times[max_idx] if max_idx < len(extended_times) else ('?', 0, 0)
    
    # PnL calculations
    # Extended vs max(0,6)
    usd_diff_ext_vs_06 = (ref_max_extended - ref_max_0_6) * USD_WEEKLY_VOLUME
    jpy_diff_ext_vs_06 = (jpycnh_per_jpy * (ref_max_extended / usdcnh_avg) - jpycnh_per_jpy * (ref_max_0_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    # Extended vs max(2,6)
    usd_diff_ext_vs_26 = (ref_max_extended - ref_max_2_6) * USD_WEEKLY_VOLUME
    jpy_diff_ext_vs_26 = (jpycnh_per_jpy * (ref_max_extended / usdcnh_avg) - jpycnh_per_jpy * (ref_max_2_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    # Extended vs max(0,2,6)
    usd_diff_ext_vs_026 = (ref_max_extended - ref_max_0_2_6) * USD_WEEKLY_VOLUME
    jpy_diff_ext_vs_026 = (jpycnh_per_jpy * (ref_max_extended / usdcnh_avg) - jpycnh_per_jpy * (ref_max_0_2_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    weekly_data.append({
        'date': sat_date,
        'fri_date': fri_date,
        'ref_max_0_6': ref_max_0_6,
        'ref_max_2_6': ref_max_2_6,
        'ref_max_0_2_6': ref_max_0_2_6,
        'ref_max_extended': ref_max_extended,
        'max_time_day': max_time[0],
        'max_time_hour': max_time[1],
        'max_time_minute': max_time[2],
        'n_points': len(extended_prices),
        # Diffs
        'usd_diff_ext_vs_06': usd_diff_ext_vs_06,
        'jpy_diff_ext_vs_06': jpy_diff_ext_vs_06,
        'total_diff_ext_vs_06': usd_diff_ext_vs_06 + jpy_diff_ext_vs_06,
        'usd_diff_ext_vs_26': usd_diff_ext_vs_26,
        'jpy_diff_ext_vs_26': jpy_diff_ext_vs_26,
        'total_diff_ext_vs_26': usd_diff_ext_vs_26 + jpy_diff_ext_vs_26,
        'usd_diff_ext_vs_026': usd_diff_ext_vs_026,
        'jpy_diff_ext_vs_026': jpy_diff_ext_vs_026,
        'total_diff_ext_vs_026': usd_diff_ext_vs_026 + jpy_diff_ext_vs_026,
    })

df = pd.DataFrame(weekly_data)
print(f'Weeks with valid data: {len(df)}')

if len(df) == 0:
    print('No valid data found!')
    exit()

# Cumulative
df['cum_ext_vs_06'] = df['total_diff_ext_vs_06'].cumsum()
df['cum_ext_vs_26'] = df['total_diff_ext_vs_26'].cumsum()
df['cum_ext_vs_026'] = df['total_diff_ext_vs_026'].cumsum()

# BPS
df['bps_ext_vs_06'] = (df['ref_max_extended'] - df['ref_max_0_6']) / df['ref_max_0_6'] * 10000
df['bps_ext_vs_26'] = (df['ref_max_extended'] - df['ref_max_2_6']) / df['ref_max_2_6'] * 10000
df['bps_ext_vs_026'] = (df['ref_max_extended'] - df['ref_max_0_2_6']) / df['ref_max_0_2_6'] * 10000

print('\n' + '='*70)
print('RESULTS: max(Fri 22:00 ~ Sat 06:00) vs Existing Strategies')
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
avg_ext_vs_06 = df['total_diff_ext_vs_06'].mean()
avg_ext_vs_26 = df['total_diff_ext_vs_26'].mean()
avg_ext_vs_026 = df['total_diff_ext_vs_026'].mean()
print(f'Extended vs max(0,6):   {avg_ext_vs_06 * 52 / 1e6:>6.2f}M CNH/year ({df["bps_ext_vs_06"].mean() * 52:>5.1f} bps/year)')
print(f'Extended vs max(2,6):   {avg_ext_vs_26 * 52 / 1e6:>6.2f}M CNH/year ({df["bps_ext_vs_26"].mean() * 52:>5.1f} bps/year)')
print(f'Extended vs max(0,2,6): {avg_ext_vs_026 * 52 / 1e6:>6.2f}M CNH/year ({df["bps_ext_vs_026"].mean() * 52:>5.1f} bps/year)')

# Time analysis
print('\n' + '='*70)
print('Which time point had the MAX price most often?')
print('='*70)

# Create time string for grouping
df['max_time_str'] = df.apply(lambda r: f"{r['max_time_day']} {r['max_time_hour']:02d}:{r['max_time_minute']:02d}", axis=1)
time_counts = df['max_time_str'].value_counts()

print('\nTop time points for MAX:')
for time_str, count in time_counts.head(15).items():
    pct = count / len(df) * 100
    print(f'  {time_str}  -> {count} weeks ({pct:.1f}%)')

# Save
df.to_excel(os.path.join(OUTPUT_DIR, 'strategy_fri_sat_extended.xlsx'), index=False)
print(f'\nData saved: {os.path.join(OUTPUT_DIR, "strategy_fri_sat_extended.xlsx")}')

# Plot
try:
    chinese_font = FontProperties(fname=font_path, size=12)
    chinese_font_title = FontProperties(fname=font_path, size=14)
    chinese_font_legend = FontProperties(fname=font_path, size=11)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    dates = pd.to_datetime(df['date'])
    
    # Plot 1: Reference prices
    ax1 = axes[0, 0]
    ax1.plot(dates, df['ref_max_0_6'], 'b-', linewidth=2, marker='o', markersize=4, alpha=0.7)
    ax1.plot(dates, df['ref_max_2_6'], 'g-', linewidth=2, marker='s', markersize=4, alpha=0.7)
    ax1.plot(dates, df['ref_max_0_2_6'], 'orange', linewidth=2, marker='^', markersize=4, alpha=0.7)
    ax1.plot(dates, df['ref_max_extended'], 'r-', linewidth=2.5, marker='*', markersize=8)
    ax1.set_xlabel('Date', fontproperties=chinese_font)
    ax1.set_ylabel('USDCNH Reference', fontproperties=chinese_font)
    ax1.set_title('Reference Price: max(Fri22~Sat06) vs Others', fontproperties=chinese_font_title)
    ax1.legend(['max(0,6)', 'max(2,6)', 'max(0,2,6)', 'max(Fri22~Sat06)'], loc='upper left', prop=chinese_font_legend)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 2: Cumulative PnL
    ax2 = axes[0, 1]
    ax2.plot(dates, df['cum_ext_vs_06']/1e6, 'b-', linewidth=2.5, marker='o', markersize=5)
    ax2.plot(dates, df['cum_ext_vs_26']/1e6, 'g-', linewidth=2.5, marker='s', markersize=5)
    ax2.plot(dates, df['cum_ext_vs_026']/1e6, 'r-', linewidth=2.5, marker='^', markersize=5)
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax2.fill_between(dates, 0, df['cum_ext_vs_026']/1e6, where=(df['cum_ext_vs_026'] >= 0), color='green', alpha=0.1)
    ax2.fill_between(dates, 0, df['cum_ext_vs_026']/1e6, where=(df['cum_ext_vs_026'] < 0), color='red', alpha=0.1)
    
    ax2.annotate(f'{df["cum_ext_vs_06"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_ext_vs_06'].iloc[-1]/1e6), 
                xytext=(5, 0), textcoords='offset points', fontsize=10, color='blue', fontweight='bold')
    ax2.annotate(f'{df["cum_ext_vs_26"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_ext_vs_26'].iloc[-1]/1e6), 
                xytext=(5, 0), textcoords='offset points', fontsize=10, color='green', fontweight='bold')
    ax2.annotate(f'{df["cum_ext_vs_026"].iloc[-1]/1e6:.2f}M', xy=(dates.iloc[-1], df['cum_ext_vs_026'].iloc[-1]/1e6), 
                xytext=(5, 5), textcoords='offset points', fontsize=10, color='red', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    ax2.set_xlabel('Date', fontproperties=chinese_font)
    ax2.set_ylabel('Cumulative PnL Diff (M CNH)', fontproperties=chinese_font)
    ax2.set_title('Cumulative PnL: Extended vs Others', fontproperties=chinese_font_title)
    ax2.legend(['vs max(0,6)', 'vs max(2,6)', 'vs max(0,2,6)'], loc='upper left', prop=chinese_font_legend)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 3: Time distribution
    ax3 = axes[1, 0]
    time_data = time_counts.head(15)
    bars = ax3.barh(range(len(time_data)), time_data.values, color='steelblue', alpha=0.7)
    ax3.set_yticks(range(len(time_data)))
    ax3.set_yticklabels(time_data.index, fontsize=9)
    ax3.set_xlabel('Frequency (weeks)', fontproperties=chinese_font)
    ax3.set_title('Which time had MAX price?', fontproperties=chinese_font_title)
    ax3.grid(True, alpha=0.3, axis='x')
    ax3.invert_yaxis()
    
    # Highlight top bar
    if len(bars) > 0:
        bars[0].set_color('red')
    
    # Plot 4: Summary
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = f"""
SUMMARY: Extended Strategy max(Fri 22:00 ~ Sat 06:00)
{'='*55}

Period: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}
Weeks: {len(df)}
Time points: {len(time_points)} (every 30min)

{'='*55}
Cumulative PnL Difference
{'='*55}

Extended vs max(0,6):    {df['cum_ext_vs_06'].iloc[-1]:>12,.0f} CNH ({df['cum_ext_vs_06'].iloc[-1]/1e6:.2f}M)
Extended vs max(2,6):    {df['cum_ext_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_ext_vs_26'].iloc[-1]/1e6:.2f}M)
Extended vs max(0,2,6):  {df['cum_ext_vs_026'].iloc[-1]:>12,.0f} CNH ({df['cum_ext_vs_026'].iloc[-1]/1e6:.2f}M)

{'='*55}
Average BPS Improvement (per week)
{'='*55}

vs max(0,6):   +{df['bps_ext_vs_06'].mean():.2f} bps/week
vs max(2,6):   +{df['bps_ext_vs_26'].mean():.2f} bps/week
vs max(0,2,6): +{df['bps_ext_vs_026'].mean():.2f} bps/week

{'='*55}
Annualized Extra Revenue (52 weeks)
{'='*55}

vs max(0,6):   ~{avg_ext_vs_06 * 52 / 1e6:.2f}M CNH/year
vs max(2,6):   ~{avg_ext_vs_26 * 52 / 1e6:.2f}M CNH/year
vs max(0,2,6): ~{avg_ext_vs_026 * 52 / 1e6:.2f}M CNH/year

{'='*55}
Most frequent MAX time: {time_counts.index[0]}
({'='*55})
"""
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', fontproperties=chinese_font,
             family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, 'strategy_fri_sat_extended.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f'Chart saved: {save_path}')
    plt.close()
    
except Exception as e:
    print(f'Chart error: {e}')

print('\n' + '='*70)
print('CONCLUSION')
print('='*70)
print(f'\nExtended strategy max(Fri 22:00 ~ Sat 06:00):')
print(f'  vs max(0,6):   +{df["bps_ext_vs_06"].mean():.2f} bps/week -> {df["cum_ext_vs_06"].iloc[-1]/1e6:.2f}M CNH total')
print(f'  vs max(2,6):   +{df["bps_ext_vs_26"].mean():.2f} bps/week -> {df["cum_ext_vs_26"].iloc[-1]/1e6:.2f}M CNH total')
print(f'  vs max(0,2,6): +{df["bps_ext_vs_026"].mean():.2f} bps/week -> {df["cum_ext_vs_026"].iloc[-1]/1e6:.2f}M CNH total')
print('='*70)
