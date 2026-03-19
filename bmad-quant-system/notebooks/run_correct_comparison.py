# -*- coding: utf-8 -*-
"""
Strategy Comparison - CORRECT VERSION
USD uses USDCNH max()
JPY uses JPYCNH max() independently
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

USD_WEEKLY = 60_000_000        # 60M USD/week
JPY_WEEKLY = 4_000_000_000     # 4B JPY/week

# Load data
print("Loading data...")
all_files = os.listdir(OUTPUT_DIR)
usdcnh_files = [f for f in all_files if 'USDCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]
jpycnh_files = [f for f in all_files if 'JPYCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]

print(f"Loading USDCNH: {usdcnh_files[0]}")
df_usdcnh = pd.read_excel(os.path.join(OUTPUT_DIR, usdcnh_files[0]))
df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
df_usdcnh.set_index('timestamp', inplace=True)

print(f"Loading JPYCNH: {jpycnh_files[0]}")
df_jpycnh = pd.read_excel(os.path.join(OUTPUT_DIR, jpycnh_files[0]))
df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
df_jpycnh.set_index('timestamp', inplace=True)

# JPYCNH is per 100 JPY, convert to per 1 JPY
df_jpycnh['mid_per_jpy'] = df_jpycnh['mid'] / 100

for df in [df_usdcnh, df_jpycnh]:
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['weekday'] = df.index.dayofweek

# Get Saturday and Friday data
sat_usdcnh = df_usdcnh[df_usdcnh['weekday'] == 5].copy()
fri_usdcnh = df_usdcnh[df_usdcnh['weekday'] == 4].copy()
sat_jpycnh = df_jpycnh[df_jpycnh['weekday'] == 5].copy()
fri_jpycnh = df_jpycnh[df_jpycnh['weekday'] == 4].copy()

sat_dates = sat_usdcnh['date'].unique()
print(f"Total Saturday dates: {len(sat_dates)}")

# Build weekly data
results = []
for sat_date in sat_dates:
    sat_usd = sat_usdcnh[sat_usdcnh['date'] == sat_date]
    sat_jpy = sat_jpycnh[sat_jpycnh['date'] == sat_date]
    fri_date = (pd.Timestamp(sat_date) - pd.Timedelta(days=1)).date()
    fri_usd = fri_usdcnh[fri_usdcnh['date'] == fri_date]
    fri_jpy = fri_jpycnh[fri_jpycnh['date'] == fri_date]
    
    # USDCNH at hour 0, 2, 6
    usd_h0 = sat_usd[(sat_usd['hour'] == 0) & (sat_usd['minute'] == 0)]
    usd_h2 = sat_usd[(sat_usd['hour'] == 2) & (sat_usd['minute'] == 0)]
    usd_h6 = sat_usd[(sat_usd['hour'] == 6) & (sat_usd['minute'] == 0)]
    
    # JPYCNH at hour 0, 2, 6
    jpy_h0 = sat_jpy[(sat_jpy['hour'] == 0) & (sat_jpy['minute'] == 0)]
    jpy_h2 = sat_jpy[(sat_jpy['hour'] == 2) & (sat_jpy['minute'] == 0)]
    jpy_h6 = sat_jpy[(sat_jpy['hour'] == 6) & (sat_jpy['minute'] == 0)]
    
    if len(usd_h0) == 0 or len(usd_h2) == 0 or len(usd_h6) == 0:
        continue
    if len(jpy_h0) == 0 or len(jpy_h2) == 0 or len(jpy_h6) == 0:
        continue
    
    usdcnh_h0 = usd_h0['mid'].values[0]
    usdcnh_h2 = usd_h2['mid'].values[0]
    usdcnh_h6 = usd_h6['mid'].values[0]
    
    jpycnh_h0 = jpy_h0['mid_per_jpy'].values[0]
    jpycnh_h2 = jpy_h2['mid_per_jpy'].values[0]
    jpycnh_h6 = jpy_h6['mid_per_jpy'].values[0]
    
    # Extended: Fri 22:00 ~ Sat 06:00 every 30 min
    usd_extended_prices = []
    jpy_extended_prices = []
    
    # Friday 22:00, 22:30, 23:00, 23:30
    for h in [22, 23]:
        for m in [0, 30]:
            usd_data = fri_usd[(fri_usd['hour'] == h) & (fri_usd['minute'] == m)]
            jpy_data = fri_jpy[(fri_jpy['hour'] == h) & (fri_jpy['minute'] == m)]
            if len(usd_data) > 0:
                usd_extended_prices.append(usd_data['mid'].values[0])
            if len(jpy_data) > 0:
                jpy_extended_prices.append(jpy_data['mid_per_jpy'].values[0])
    
    # Saturday 00:00 ~ 06:00
    for h in range(7):
        for m in [0, 30]:
            if h == 6 and m == 30:
                continue
            usd_data = sat_usd[(sat_usd['hour'] == h) & (sat_usd['minute'] == m)]
            jpy_data = sat_jpy[(sat_jpy['hour'] == h) & (sat_jpy['minute'] == m)]
            if len(usd_data) > 0:
                usd_extended_prices.append(usd_data['mid'].values[0])
            if len(jpy_data) > 0:
                jpy_extended_prices.append(jpy_data['mid_per_jpy'].values[0])
    
    if len(usd_extended_prices) < 10 or len(jpy_extended_prices) < 10:
        continue
    
    # ============ USD Reference Prices ============
    usd_ref_max_26 = max(usdcnh_h2, usdcnh_h6)  # baseline
    usd_ref_max_026 = max(usdcnh_h0, usdcnh_h2, usdcnh_h6)
    usd_ref_extended = max(usd_extended_prices)
    
    # ============ JPY Reference Prices (INDEPENDENT!) ============
    jpy_ref_max_26 = max(jpycnh_h2, jpycnh_h6)  # baseline
    jpy_ref_max_026 = max(jpycnh_h0, jpycnh_h2, jpycnh_h6)
    jpy_ref_extended = max(jpy_extended_prices)
    
    # ============ BPS Calculation ============
    usd_bps_026 = (usd_ref_max_026 - usd_ref_max_26) / usd_ref_max_26 * 10000
    usd_bps_ext = (usd_ref_extended - usd_ref_max_26) / usd_ref_max_26 * 10000
    
    jpy_bps_026 = (jpy_ref_max_026 - jpy_ref_max_26) / jpy_ref_max_26 * 10000
    jpy_bps_ext = (jpy_ref_extended - jpy_ref_max_26) / jpy_ref_max_26 * 10000
    
    # ============ PnL Calculation ============
    # USD PnL = (ref_price_diff) * USD_volume
    usd_pnl_026 = (usd_ref_max_026 - usd_ref_max_26) * USD_WEEKLY
    usd_pnl_ext = (usd_ref_extended - usd_ref_max_26) * USD_WEEKLY
    
    # JPY PnL = (jpycnh_ref_diff) * JPY_volume
    jpy_pnl_026 = (jpy_ref_max_026 - jpy_ref_max_26) * JPY_WEEKLY
    jpy_pnl_ext = (jpy_ref_extended - jpy_ref_max_26) * JPY_WEEKLY
    
    results.append({
        'date': sat_date,
        # USD
        'usd_ref_max_26': usd_ref_max_26,
        'usd_ref_max_026': usd_ref_max_026,
        'usd_ref_extended': usd_ref_extended,
        'usd_bps_026': usd_bps_026,
        'usd_bps_ext': usd_bps_ext,
        'usd_pnl_026': usd_pnl_026,
        'usd_pnl_ext': usd_pnl_ext,
        # JPY
        'jpy_ref_max_26': jpy_ref_max_26,
        'jpy_ref_max_026': jpy_ref_max_026,
        'jpy_ref_extended': jpy_ref_extended,
        'jpy_bps_026': jpy_bps_026,
        'jpy_bps_ext': jpy_bps_ext,
        'jpy_pnl_026': jpy_pnl_026,
        'jpy_pnl_ext': jpy_pnl_ext,
        # Total
        'total_pnl_026': usd_pnl_026 + jpy_pnl_026,
        'total_pnl_ext': usd_pnl_ext + jpy_pnl_ext,
    })

df = pd.DataFrame(results)

# Cumulative PnL
df['cum_usd_026'] = df['usd_pnl_026'].cumsum()
df['cum_usd_ext'] = df['usd_pnl_ext'].cumsum()
df['cum_jpy_026'] = df['jpy_pnl_026'].cumsum()
df['cum_jpy_ext'] = df['jpy_pnl_ext'].cumsum()
df['cum_total_026'] = df['total_pnl_026'].cumsum()
df['cum_total_ext'] = df['total_pnl_ext'].cumsum()

# Print results
print("\n" + "="*80)
print("Strategy Comparison vs max(2,6) Baseline - CORRECT VERSION")
print("="*80)
print(f"\nBacktest period: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]} ({len(df)} weeks)")

print("\n" + "="*80)
print("USD Average Weekly BPS Premium (vs max(2,6))")
print("="*80)
print(f"\n{'Strategy':<40} {'Avg bps/wk':>12} {'Median':>10} {'Max':>10} {'Min':>10}")
print("-"*82)
print(f"{'max(0,2,6)':<40} {df['usd_bps_026'].mean():>12.2f} {df['usd_bps_026'].median():>10.2f} {df['usd_bps_026'].max():>10.2f} {df['usd_bps_026'].min():>10.2f}")
print(f"{'Extended (22:00~06:00)':<40} {df['usd_bps_ext'].mean():>12.2f} {df['usd_bps_ext'].median():>10.2f} {df['usd_bps_ext'].max():>10.2f} {df['usd_bps_ext'].min():>10.2f}")

print("\n" + "="*80)
print("JPY Average Weekly BPS Premium (vs max(2,6))")
print("="*80)
print(f"\n{'Strategy':<40} {'Avg bps/wk':>12} {'Median':>10} {'Max':>10} {'Min':>10}")
print("-"*82)
print(f"{'max(0,2,6)':<40} {df['jpy_bps_026'].mean():>12.2f} {df['jpy_bps_026'].median():>10.2f} {df['jpy_bps_026'].max():>10.2f} {df['jpy_bps_026'].min():>10.2f}")
print(f"{'Extended (22:00~06:00)':<40} {df['jpy_bps_ext'].mean():>12.2f} {df['jpy_bps_ext'].median():>10.2f} {df['jpy_bps_ext'].max():>10.2f} {df['jpy_bps_ext'].min():>10.2f}")

print("\n" + "="*80)
print("SUMMARY: Average BPS per Week vs max(2,6)")
print("="*80)
print(f"\n{'Strategy':<40} {'USD bps':>12} {'JPY bps':>12}")
print("-"*64)
print(f"{'max(0,2,6)':<40} {df['usd_bps_026'].mean():>12.2f} {df['jpy_bps_026'].mean():>12.2f}")
print(f"{'Extended (22:00~06:00)':<40} {df['usd_bps_ext'].mean():>12.2f} {df['jpy_bps_ext'].mean():>12.2f}")

print("\n" + "="*80)
print("Cumulative PnL vs max(2,6)")
print("="*80)
print(f"\n{'Strategy':<40} {'USD (CNH)':>15} {'JPY (CNH)':>15} {'Total (CNH)':>15}")
print("-"*85)
print(f"{'max(0,2,6)':<40} {df['cum_usd_026'].iloc[-1]:>15,.0f} {df['cum_jpy_026'].iloc[-1]:>15,.0f} {df['cum_total_026'].iloc[-1]:>15,.0f}")
print(f"{'Extended (22:00~06:00)':<40} {df['cum_usd_ext'].iloc[-1]:>15,.0f} {df['cum_jpy_ext'].iloc[-1]:>15,.0f} {df['cum_total_ext'].iloc[-1]:>15,.0f}")

print("\n" + "="*80)
print("Weekly Average PnL vs max(2,6)")
print("="*80)
print(f"\n{'Strategy':<40} {'USD (CNH)':>15} {'JPY (CNH)':>15} {'Total (CNH)':>15}")
print("-"*85)
print(f"{'max(0,2,6)':<40} {df['usd_pnl_026'].mean():>15,.0f} {df['jpy_pnl_026'].mean():>15,.0f} {df['total_pnl_026'].mean():>15,.0f}")
print(f"{'Extended (22:00~06:00)':<40} {df['usd_pnl_ext'].mean():>15,.0f} {df['jpy_pnl_ext'].mean():>15,.0f} {df['total_pnl_ext'].mean():>15,.0f}")

# Create chart
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Chart 1: Cumulative Total PnL
ax1 = axes[0, 0]
ax1.plot(df['date'], df['cum_total_026']/1e6, 'b-', linewidth=2, marker='o', markersize=4, label='max(0,2,6)')
ax1.plot(df['date'], df['cum_total_ext']/1e6, 'r-', linewidth=2, marker='s', markersize=4, label='Extended')
ax1.set_title('Cumulative PnL (USD+JPY) vs max(2,6)', fontproperties=chinese_font_title)
ax1.set_xlabel('Date', fontproperties=chinese_font)
ax1.set_ylabel('Cumulative PnL (M CNH)', fontproperties=chinese_font)
ax1.legend(prop=chinese_font_legend)
ax1.grid(True, alpha=0.3)
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Chart 2: USD vs JPY BPS comparison (bar chart)
ax2 = axes[0, 1]
x_pos = np.arange(2)
width = 0.35
usd_avgs = [df['usd_bps_026'].mean(), df['usd_bps_ext'].mean()]
jpy_avgs = [df['jpy_bps_026'].mean(), df['jpy_bps_ext'].mean()]
bars1 = ax2.bar(x_pos - width/2, usd_avgs, width, label='USD bps/week', color='steelblue')
bars2 = ax2.bar(x_pos + width/2, jpy_avgs, width, label='JPY bps/week', color='indianred')
ax2.set_title('Average Weekly BPS vs max(2,6)', fontproperties=chinese_font_title)
ax2.set_ylabel('BPS per Week', fontproperties=chinese_font)
ax2.set_xticks(x_pos)
ax2.set_xticklabels(['max(0,2,6)', 'Extended'])
ax2.legend(prop=chinese_font_legend)
ax2.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars1, usd_avgs):
    ax2.annotate(f'{val:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                 ha='center', va='bottom', fontsize=10)
for bar, val in zip(bars2, jpy_avgs):
    ax2.annotate(f'{val:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                 ha='center', va='bottom', fontsize=10)

# Chart 3: USD Cumulative PnL
ax3 = axes[1, 0]
ax3.plot(df['date'], df['cum_usd_026']/1e6, 'b-', linewidth=2, marker='o', markersize=4, label='max(0,2,6)')
ax3.plot(df['date'], df['cum_usd_ext']/1e6, 'r-', linewidth=2, marker='s', markersize=4, label='Extended')
ax3.set_title('USD Cumulative PnL vs max(2,6)', fontproperties=chinese_font_title)
ax3.set_xlabel('Date', fontproperties=chinese_font)
ax3.set_ylabel('Cumulative PnL (M CNH)', fontproperties=chinese_font)
ax3.legend(prop=chinese_font_legend)
ax3.grid(True, alpha=0.3)
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Chart 4: JPY Cumulative PnL
ax4 = axes[1, 1]
ax4.plot(df['date'], df['cum_jpy_026']/1e6, 'b-', linewidth=2, marker='o', markersize=4, label='max(0,2,6)')
ax4.plot(df['date'], df['cum_jpy_ext']/1e6, 'r-', linewidth=2, marker='s', markersize=4, label='Extended')
ax4.set_title('JPY Cumulative PnL vs max(2,6)', fontproperties=chinese_font_title)
ax4.set_xlabel('Date', fontproperties=chinese_font)
ax4.set_ylabel('Cumulative PnL (M CNH)', fontproperties=chinese_font)
ax4.legend(prop=chinese_font_legend)
ax4.grid(True, alpha=0.3)
plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'strategy_comparison_correct.png'), dpi=150, bbox_inches='tight')
print(f"\nChart saved to: output/strategy_comparison_correct.png")

# Save data
df.to_excel(os.path.join(OUTPUT_DIR, 'strategy_comparison_correct.xlsx'), index=False)
print(f"Data saved to: output/strategy_comparison_correct.xlsx")

print("\n" + "="*80)
print("DONE!")
print("="*80)
