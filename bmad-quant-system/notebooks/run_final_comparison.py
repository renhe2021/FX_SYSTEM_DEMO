# -*- coding: utf-8 -*-
"""
Strategy Comparison: max(0,2,6) vs Extended vs max(2,6) baseline
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import warnings
warnings.filterwarnings('ignore')

# Font setup
font_path = r'C:\Windows\Fonts\msyh.ttc'
chinese_font = FontProperties(fname=font_path, size=11)
chinese_font_title = FontProperties(fname=font_path, size=14)
chinese_font_legend = FontProperties(fname=font_path, size=10)

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

USD_WEEKLY = 60_000_000
JPY_WEEKLY = 4_000_000_000

# Load data
print("Loading data...")
all_files = os.listdir(OUTPUT_DIR)
usdcnh_files = [f for f in all_files if 'USDCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]
jpycnh_files = [f for f in all_files if 'JPYCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]

df_usdcnh = pd.read_excel(os.path.join(OUTPUT_DIR, usdcnh_files[0]))
df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
df_usdcnh.set_index('timestamp', inplace=True)

df_jpycnh = pd.read_excel(os.path.join(OUTPUT_DIR, jpycnh_files[0]))
df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
df_jpycnh.set_index('timestamp', inplace=True)

for df in [df_usdcnh, df_jpycnh]:
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['weekday'] = df.index.dayofweek

sat_usdcnh = df_usdcnh[df_usdcnh['weekday'] == 5].copy()
fri_usdcnh = df_usdcnh[df_usdcnh['weekday'] == 4].copy()
sat_dates = sat_usdcnh['date'].unique()

# Build weekly data
results = []
for sat_date in sat_dates:
    sat_day = sat_usdcnh[sat_usdcnh['date'] == sat_date]
    fri_date = (pd.Timestamp(sat_date) - pd.Timedelta(days=1)).date()
    fri_day = fri_usdcnh[fri_usdcnh['date'] == fri_date]
    
    h0 = sat_day[(sat_day['hour'] == 0) & (sat_day['minute'] == 0)]
    h2 = sat_day[(sat_day['hour'] == 2) & (sat_day['minute'] == 0)]
    h6 = sat_day[(sat_day['hour'] == 6) & (sat_day['minute'] == 0)]
    
    if len(h0) == 0 or len(h2) == 0 or len(h6) == 0:
        continue
    
    usdcnh_h0 = h0['mid'].values[0]
    usdcnh_h2 = h2['mid'].values[0]
    usdcnh_h6 = h6['mid'].values[0]
    
    # Extended: Fri 22:00 ~ Sat 06:00 every 30 min
    extended_prices = []
    for h in [22, 23]:
        for m in [0, 30]:
            fri_data = fri_day[(fri_day['hour'] == h) & (fri_day['minute'] == m)]
            if len(fri_data) > 0:
                extended_prices.append(fri_data['mid'].values[0])
    for h in range(7):
        for m in [0, 30]:
            if h == 6 and m == 30:
                continue
            sat_data = sat_day[(sat_day['hour'] == h) & (sat_day['minute'] == m)]
            if len(sat_data) > 0:
                extended_prices.append(sat_data['mid'].values[0])
    
    if len(extended_prices) < 10:
        continue
    
    jpycnh_sat = df_jpycnh[df_jpycnh['date'] == sat_date]
    if len(jpycnh_sat) == 0:
        continue
    jpycnh_per_jpy = jpycnh_sat['mid'].mean()
    usdcnh_avg = sat_day['mid'].mean()
    
    ref_max_26 = max(usdcnh_h2, usdcnh_h6)
    ref_max_026 = max(usdcnh_h0, usdcnh_h2, usdcnh_h6)
    ref_extended = max(extended_prices)
    
    def calc_jpycnh(ref_usdcnh):
        return jpycnh_per_jpy * (ref_usdcnh / usdcnh_avg)
    
    jpycnh_max_26 = calc_jpycnh(ref_max_26)
    jpycnh_max_026 = calc_jpycnh(ref_max_026)
    jpycnh_extended = calc_jpycnh(ref_extended)
    
    bps_026 = (ref_max_026 - ref_max_26) / ref_max_26 * 10000
    bps_ext = (ref_extended - ref_max_26) / ref_max_26 * 10000
    
    usd_pnl_026 = (ref_max_026 - ref_max_26) * USD_WEEKLY
    usd_pnl_ext = (ref_extended - ref_max_26) * USD_WEEKLY
    jpy_pnl_026 = (jpycnh_max_026 - jpycnh_max_26) * JPY_WEEKLY
    jpy_pnl_ext = (jpycnh_extended - jpycnh_max_26) * JPY_WEEKLY
    
    results.append({
        'date': sat_date,
        'bps_026': bps_026,
        'bps_ext': bps_ext,
        'usd_pnl_026': usd_pnl_026,
        'usd_pnl_ext': usd_pnl_ext,
        'jpy_pnl_026': jpy_pnl_026,
        'jpy_pnl_ext': jpy_pnl_ext,
        'total_pnl_026': usd_pnl_026 + jpy_pnl_026,
        'total_pnl_ext': usd_pnl_ext + jpy_pnl_ext,
    })

df = pd.DataFrame(results)

# Cumulative PnL
df['cum_total_026'] = df['total_pnl_026'].cumsum()
df['cum_total_ext'] = df['total_pnl_ext'].cumsum()
df['cum_usd_026'] = df['usd_pnl_026'].cumsum()
df['cum_usd_ext'] = df['usd_pnl_ext'].cumsum()
df['cum_jpy_026'] = df['jpy_pnl_026'].cumsum()
df['cum_jpy_ext'] = df['jpy_pnl_ext'].cumsum()

# Print results
print("\n" + "="*70)
print("Strategy Comparison vs max(2,6) Baseline")
print("="*70)
print(f"\nBacktest period: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]} ({len(df)} weeks)")

print("\n" + "="*70)
print("Average Weekly BPS Premium")
print("="*70)
print(f"\n{'Strategy':<40} {'Avg bps/wk':>12} {'Median':>10} {'Max':>10} {'Min':>10}")
print("-"*82)
print(f"{'max(0,2,6)':<40} {df['bps_026'].mean():>12.2f} {df['bps_026'].median():>10.2f} {df['bps_026'].max():>10.2f} {df['bps_026'].min():>10.2f}")
print(f"{'Extended (22:00~06:00 every 30min)':<40} {df['bps_ext'].mean():>12.2f} {df['bps_ext'].median():>10.2f} {df['bps_ext'].max():>10.2f} {df['bps_ext'].min():>10.2f}")

print("\n" + "="*70)
print("Cumulative PnL")
print("="*70)
print(f"\n{'Strategy':<40} {'USD (CNH)':>15} {'JPY (CNH)':>15} {'Total (CNH)':>15}")
print("-"*85)
print(f"{'max(0,2,6)':<40} {df['cum_usd_026'].iloc[-1]:>15,.0f} {df['cum_jpy_026'].iloc[-1]:>15,.0f} {df['cum_total_026'].iloc[-1]:>15,.0f}")
print(f"{'Extended (22:00~06:00)':<40} {df['cum_usd_ext'].iloc[-1]:>15,.0f} {df['cum_jpy_ext'].iloc[-1]:>15,.0f} {df['cum_total_ext'].iloc[-1]:>15,.0f}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

bps_diff = df['bps_ext'].mean() - df['bps_026'].mean()
pnl_diff = df['cum_total_ext'].iloc[-1] - df['cum_total_026'].iloc[-1]

print(f"\nExtended vs max(0,2,6):")
print(f"  - Extra BPS per week: +{bps_diff:.2f} bps")
print(f"  - Extra cumulative PnL: +{pnl_diff:,.0f} CNH (+{pnl_diff/1e6:.2f}M)")
print(f"  - Annualized extra: +{pnl_diff * 52 / len(df) / 1e6:.2f}M CNH/year")

# Create chart
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Chart 1: Cumulative Total PnL
ax1 = axes[0, 0]
ax1.plot(df['date'], df['cum_total_026']/1e6, 'b-', linewidth=2, marker='o', markersize=4, label='max(0,2,6)')
ax1.plot(df['date'], df['cum_total_ext']/1e6, 'r-', linewidth=2, marker='s', markersize=4, label='Extended')
ax1.set_title('Cumulative PnL (USD+JPY)', fontproperties=chinese_font_title)
ax1.set_xlabel('Date', fontproperties=chinese_font)
ax1.set_ylabel('Cumulative PnL (M CNH)', fontproperties=chinese_font)
ax1.legend(prop=chinese_font_legend)
ax1.grid(True, alpha=0.3)
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
ax1.annotate(f'{df["cum_total_026"].iloc[-1]/1e6:.1f}M', 
             xy=(df['date'].iloc[-1], df['cum_total_026'].iloc[-1]/1e6),
             xytext=(5, 0), textcoords='offset points', fontsize=10, color='blue')
ax1.annotate(f'{df["cum_total_ext"].iloc[-1]/1e6:.1f}M', 
             xy=(df['date'].iloc[-1], df['cum_total_ext'].iloc[-1]/1e6),
             xytext=(5, 0), textcoords='offset points', fontsize=10, color='red')

# Chart 2: USD Cumulative PnL
ax2 = axes[0, 1]
ax2.plot(df['date'], df['cum_usd_026']/1e6, 'b-', linewidth=2, marker='o', markersize=4, label='max(0,2,6)')
ax2.plot(df['date'], df['cum_usd_ext']/1e6, 'r-', linewidth=2, marker='s', markersize=4, label='Extended')
ax2.set_title('USD Cumulative PnL', fontproperties=chinese_font_title)
ax2.set_xlabel('Date', fontproperties=chinese_font)
ax2.set_ylabel('Cumulative PnL (M CNH)', fontproperties=chinese_font)
ax2.legend(prop=chinese_font_legend)
ax2.grid(True, alpha=0.3)
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Chart 3: JPY Cumulative PnL
ax3 = axes[1, 0]
ax3.plot(df['date'], df['cum_jpy_026']/1e6, 'b-', linewidth=2, marker='o', markersize=4, label='max(0,2,6)')
ax3.plot(df['date'], df['cum_jpy_ext']/1e6, 'r-', linewidth=2, marker='s', markersize=4, label='Extended')
ax3.set_title('JPY Cumulative PnL', fontproperties=chinese_font_title)
ax3.set_xlabel('Date', fontproperties=chinese_font)
ax3.set_ylabel('Cumulative PnL (M CNH)', fontproperties=chinese_font)
ax3.legend(prop=chinese_font_legend)
ax3.grid(True, alpha=0.3)
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Chart 4: Weekly BPS
ax4 = axes[1, 1]
x = np.arange(len(df))
width = 0.35
bars1 = ax4.bar(x - width/2, df['bps_026'], width, label='max(0,2,6)', color='steelblue', alpha=0.8)
bars2 = ax4.bar(x + width/2, df['bps_ext'], width, label='Extended', color='indianred', alpha=0.8)
ax4.axhline(y=df['bps_026'].mean(), color='blue', linestyle='--', linewidth=1, label=f'max(0,2,6) avg: {df["bps_026"].mean():.2f}')
ax4.axhline(y=df['bps_ext'].mean(), color='red', linestyle='--', linewidth=1, label=f'Extended avg: {df["bps_ext"].mean():.2f}')
ax4.set_title('Weekly BPS Premium vs max(2,6)', fontproperties=chinese_font_title)
ax4.set_xlabel('Week', fontproperties=chinese_font)
ax4.set_ylabel('BPS', fontproperties=chinese_font)
ax4.legend(prop=chinese_font_legend, loc='upper right')
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'strategy_comparison_final.png'), dpi=150, bbox_inches='tight')
print(f"\nChart saved to: output/strategy_comparison_final.png")

# Save data
df.to_excel(os.path.join(OUTPUT_DIR, 'strategy_comparison_final.xlsx'), index=False)
print(f"Data saved to: output/strategy_comparison_final.xlsx")

print("\n" + "="*70)
print("DONE!")
print("="*70)
