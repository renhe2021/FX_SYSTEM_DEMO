# -*- coding: utf-8 -*-
"""
Calculate BPS differences by currency (USD and JPY separately)
All benchmarked against max(2,6)
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

# Paths
OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

# Trading volumes
USD_WEEKLY = 60_000_000  # 60M USD/week
JPY_WEEKLY = 4_000_000_000  # 4B JPY/week

# Load data from output directory
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

# Add date columns
for df in [df_usdcnh, df_jpycnh]:
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['weekday'] = df.index.dayofweek  # 5 = Saturday, 4 = Friday

# Get Saturday data
sat_usdcnh = df_usdcnh[df_usdcnh['weekday'] == 5].copy()
fri_usdcnh = df_usdcnh[df_usdcnh['weekday'] == 4].copy()

# Get unique Saturday dates
sat_dates = sat_usdcnh['date'].unique()
print(f"Total Saturday dates: {len(sat_dates)}")

# Build weekly data
weeks = []
for sat_date in sat_dates:
    # Get Saturday data for this date
    sat_day = sat_usdcnh[sat_usdcnh['date'] == sat_date]
    
    # Get Friday (day before)
    fri_date = pd.Timestamp(sat_date) - pd.Timedelta(days=1)
    fri_date = fri_date.date()
    fri_day = fri_usdcnh[fri_usdcnh['date'] == fri_date]
    
    # Get USDCNH at hour 0, 2, 6
    h0 = sat_day[(sat_day['hour'] == 0) & (sat_day['minute'] == 0)]
    h2 = sat_day[(sat_day['hour'] == 2) & (sat_day['minute'] == 0)]
    h6 = sat_day[(sat_day['hour'] == 6) & (sat_day['minute'] == 0)]
    
    if len(h0) == 0 or len(h2) == 0 or len(h6) == 0:
        continue
    
    usdcnh_h0 = h0['mid'].values[0]
    usdcnh_h2 = h2['mid'].values[0]
    usdcnh_h6 = h6['mid'].values[0]
    
    # Get extended prices (Friday 22:00 ~ Saturday 06:00)
    extended_prices = []
    
    # Friday 22:00, 22:30, 23:00, 23:30
    for h in [22, 23]:
        for m in [0, 30]:
            fri_data = fri_day[(fri_day['hour'] == h) & (fri_day['minute'] == m)]
            if len(fri_data) > 0:
                extended_prices.append(fri_data['mid'].values[0])
    
    # Saturday 00:00 ~ 06:00
    for h in range(7):
        for m in [0, 30]:
            if h == 6 and m == 30:
                continue
            sat_data = sat_day[(sat_day['hour'] == h) & (sat_day['minute'] == m)]
            if len(sat_data) > 0:
                extended_prices.append(sat_data['mid'].values[0])
    
    if len(extended_prices) < 10:
        continue
    
    # Get JPYCNH average on Saturday
    jpycnh_sat = df_jpycnh[df_jpycnh['date'] == sat_date]
    if len(jpycnh_sat) == 0:
        continue
    jpycnh_per_jpy = jpycnh_sat['mid'].mean()  # Use average for JPYCNH
    
    # USDCNH average for the day
    usdcnh_avg = sat_day['mid'].mean()
    
    weeks.append({
        'date': sat_date,
        'usdcnh_h0': usdcnh_h0,
        'usdcnh_h2': usdcnh_h2,
        'usdcnh_h6': usdcnh_h6,
        'extended_max': max(extended_prices),
        'jpycnh_per_jpy': jpycnh_per_jpy,
        'usdcnh_avg': usdcnh_avg
    })

print(f"Valid weeks: {len(weeks)}")

# Calculate strategies
results = []
for w in weeks:
    # Reference prices
    ref_max_06 = max(w['usdcnh_h0'], w['usdcnh_h6'])
    ref_max_26 = max(w['usdcnh_h2'], w['usdcnh_h6'])
    ref_max_026 = max(w['usdcnh_h0'], w['usdcnh_h2'], w['usdcnh_h6'])
    ref_extended = w['extended_max']
    
    # JPYCNH adjustment
    def calc_jpycnh(ref_usdcnh):
        return w['jpycnh_per_jpy'] * (ref_usdcnh / w['usdcnh_avg'])
    
    jpycnh_max_06 = calc_jpycnh(ref_max_06)
    jpycnh_max_26 = calc_jpycnh(ref_max_26)
    jpycnh_max_026 = calc_jpycnh(ref_max_026)
    jpycnh_extended = calc_jpycnh(ref_extended)
    
    results.append({
        'date': w['date'],
        # USDCNH reference prices
        'ref_max_06': ref_max_06,
        'ref_max_26': ref_max_26,
        'ref_max_026': ref_max_026,
        'ref_extended': ref_extended,
        # JPYCNH adjusted prices
        'jpycnh_max_06': jpycnh_max_06,
        'jpycnh_max_26': jpycnh_max_26,
        'jpycnh_max_026': jpycnh_max_026,
        'jpycnh_extended': jpycnh_extended,
    })

df = pd.DataFrame(results)

# Calculate BPS differences (vs max(2,6) baseline)
# USD: based on USDCNH reference price
# JPY: based on JPYCNH adjusted price

print("\n" + "="*80)
print("BPS Analysis by Currency (vs max(2,6) baseline)")
print("="*80)

# USD BPS calculation
df['usd_bps_06_vs_26'] = (df['ref_max_06'] - df['ref_max_26']) / df['ref_max_26'] * 10000
df['usd_bps_026_vs_26'] = (df['ref_max_026'] - df['ref_max_26']) / df['ref_max_26'] * 10000
df['usd_bps_ext_vs_26'] = (df['ref_extended'] - df['ref_max_26']) / df['ref_max_26'] * 10000

# JPY BPS calculation (same % because JPYCNH is proportional to USDCNH)
df['jpy_bps_06_vs_26'] = (df['jpycnh_max_06'] - df['jpycnh_max_26']) / df['jpycnh_max_26'] * 10000
df['jpy_bps_026_vs_26'] = (df['jpycnh_max_026'] - df['jpycnh_max_26']) / df['jpycnh_max_26'] * 10000
df['jpy_bps_ext_vs_26'] = (df['jpycnh_extended'] - df['jpycnh_max_26']) / df['jpycnh_max_26'] * 10000

# Print USD statistics
print("\n" + "-"*80)
print("USD BPS Statistics (vs max(2,6))")
print("-"*80)

print("\n1. max(0,6) vs max(2,6):")
print(f"   Average:  {df['usd_bps_06_vs_26'].mean():>8.2f} bps")
print(f"   Median:   {df['usd_bps_06_vs_26'].median():>8.2f} bps")
print(f"   Max:      {df['usd_bps_06_vs_26'].max():>8.2f} bps")
print(f"   Min:      {df['usd_bps_06_vs_26'].min():>8.2f} bps")
print(f"   Std:      {df['usd_bps_06_vs_26'].std():>8.2f} bps")

print("\n2. max(0,2,6) vs max(2,6):")
print(f"   Average:  {df['usd_bps_026_vs_26'].mean():>8.2f} bps")
print(f"   Median:   {df['usd_bps_026_vs_26'].median():>8.2f} bps")
print(f"   Max:      {df['usd_bps_026_vs_26'].max():>8.2f} bps")
print(f"   Min:      {df['usd_bps_026_vs_26'].min():>8.2f} bps")
print(f"   Std:      {df['usd_bps_026_vs_26'].std():>8.2f} bps")

print("\n3. Extended (Fri22:00~Sat06:00) vs max(2,6):")
print(f"   Average:  {df['usd_bps_ext_vs_26'].mean():>8.2f} bps")
print(f"   Median:   {df['usd_bps_ext_vs_26'].median():>8.2f} bps")
print(f"   Max:      {df['usd_bps_ext_vs_26'].max():>8.2f} bps")
print(f"   Min:      {df['usd_bps_ext_vs_26'].min():>8.2f} bps")
print(f"   Std:      {df['usd_bps_ext_vs_26'].std():>8.2f} bps")

# Print JPY statistics
print("\n" + "-"*80)
print("JPY BPS Statistics (vs max(2,6))")
print("-"*80)

print("\n1. max(0,6) vs max(2,6):")
print(f"   Average:  {df['jpy_bps_06_vs_26'].mean():>8.2f} bps")
print(f"   Median:   {df['jpy_bps_06_vs_26'].median():>8.2f} bps")
print(f"   Max:      {df['jpy_bps_06_vs_26'].max():>8.2f} bps")
print(f"   Min:      {df['jpy_bps_06_vs_26'].min():>8.2f} bps")
print(f"   Std:      {df['jpy_bps_06_vs_26'].std():>8.2f} bps")

print("\n2. max(0,2,6) vs max(2,6):")
print(f"   Average:  {df['jpy_bps_026_vs_26'].mean():>8.2f} bps")
print(f"   Median:   {df['jpy_bps_026_vs_26'].median():>8.2f} bps")
print(f"   Max:      {df['jpy_bps_026_vs_26'].max():>8.2f} bps")
print(f"   Min:      {df['jpy_bps_026_vs_26'].min():>8.2f} bps")
print(f"   Std:      {df['jpy_bps_026_vs_26'].std():>8.2f} bps")

print("\n3. Extended (Fri22:00~Sat06:00) vs max(2,6):")
print(f"   Average:  {df['jpy_bps_ext_vs_26'].mean():>8.2f} bps")
print(f"   Median:   {df['jpy_bps_ext_vs_26'].median():>8.2f} bps")
print(f"   Max:      {df['jpy_bps_ext_vs_26'].max():>8.2f} bps")
print(f"   Min:      {df['jpy_bps_ext_vs_26'].min():>8.2f} bps")
print(f"   Std:      {df['jpy_bps_ext_vs_26'].std():>8.2f} bps")

# Summary table
print("\n" + "="*80)
print("SUMMARY: Average BPS per Week vs max(2,6)")
print("="*80)

print("\n{:<35} {:>12} {:>12}".format("Strategy", "USD bps", "JPY bps"))
print("-"*60)
print("{:<35} {:>12.2f} {:>12.2f}".format(
    "max(0,6)", 
    df['usd_bps_06_vs_26'].mean(),
    df['jpy_bps_06_vs_26'].mean()
))
print("{:<35} {:>12.2f} {:>12.2f}".format(
    "max(0,2,6)", 
    df['usd_bps_026_vs_26'].mean(),
    df['jpy_bps_026_vs_26'].mean()
))
print("{:<35} {:>12.2f} {:>12.2f}".format(
    "Extended (Fri22:00~Sat06:00)", 
    df['usd_bps_ext_vs_26'].mean(),
    df['jpy_bps_ext_vs_26'].mean()
))

# Calculate CNH value
print("\n" + "="*80)
print("CNH Value Calculation")
print("="*80)

avg_usdcnh = df['ref_max_26'].mean()
avg_jpycnh = df['jpycnh_max_26'].mean()

print(f"\nAverage USDCNH: {avg_usdcnh:.4f}")
print(f"Average JPYCNH (adjusted): {avg_jpycnh:.6f}")

# USD: 1 bps = 0.0001 * USD_WEEKLY = 6,000 CNH
usd_cnh_per_bps = 0.0001 * USD_WEEKLY
print(f"\nUSD: 1 bps = 0.0001 * {USD_WEEKLY/1e6:.0f}M = {usd_cnh_per_bps:,.0f} CNH/week")

# JPY: 1 bps of JPYCNH rate difference
# PnL = JPYCNH_diff * JPY_VOLUME = 0.0001 * JPYCNH * JPY_VOLUME
jpy_cnh_per_bps = 0.0001 * avg_jpycnh * JPY_WEEKLY
print(f"JPY: 1 bps = 0.0001 * {avg_jpycnh:.6f} * {JPY_WEEKLY/1e9:.0f}B = {jpy_cnh_per_bps:,.0f} CNH/week")

total_cnh_per_bps = usd_cnh_per_bps + jpy_cnh_per_bps
print(f"Total: 1 bps = {total_cnh_per_bps:,.0f} CNH/week (if both move by 1 bps)")

# Annual calculation
print("\n" + "="*80)
print("ANNUAL CNH GAIN vs max(2,6)")
print("="*80)

strategies = [
    ("max(0,6)", df['usd_bps_06_vs_26'].mean(), df['jpy_bps_06_vs_26'].mean()),
    ("max(0,2,6)", df['usd_bps_026_vs_26'].mean(), df['jpy_bps_026_vs_26'].mean()),
    ("Extended (Fri22:00~Sat06:00)", df['usd_bps_ext_vs_26'].mean(), df['jpy_bps_ext_vs_26'].mean()),
]

print("\n{:<35} {:>15} {:>15} {:>15}".format("Strategy", "USD CNH/year", "JPY CNH/year", "Total CNH/year"))
print("-"*80)

for name, usd_bps, jpy_bps in strategies:
    usd_annual = usd_bps * usd_cnh_per_bps * 52
    jpy_annual = jpy_bps * jpy_cnh_per_bps * 52
    total_annual = usd_annual + jpy_annual
    print("{:<35} {:>15,.0f} {:>15,.0f} {:>15,.0f}".format(name, usd_annual, jpy_annual, total_annual))

# Calculate using actual PnL (not just bps)
print("\n" + "="*80)
print("Actual Weekly PnL Calculation")
print("="*80)

# USD PnL
df['usd_pnl_06_vs_26'] = (df['ref_max_06'] - df['ref_max_26']) * USD_WEEKLY
df['usd_pnl_026_vs_26'] = (df['ref_max_026'] - df['ref_max_26']) * USD_WEEKLY
df['usd_pnl_ext_vs_26'] = (df['ref_extended'] - df['ref_max_26']) * USD_WEEKLY

# JPY PnL
df['jpy_pnl_06_vs_26'] = (df['jpycnh_max_06'] - df['jpycnh_max_26']) * JPY_WEEKLY
df['jpy_pnl_026_vs_26'] = (df['jpycnh_max_026'] - df['jpycnh_max_26']) * JPY_WEEKLY
df['jpy_pnl_ext_vs_26'] = (df['jpycnh_extended'] - df['jpycnh_max_26']) * JPY_WEEKLY

print("\n{:<35} {:>18} {:>18} {:>18}".format("Strategy", "USD Cum PnL", "JPY Cum PnL", "Total Cum PnL"))
print("-"*90)
print("{:<35} {:>18,.0f} {:>18,.0f} {:>18,.0f}".format(
    "max(0,6)",
    df['usd_pnl_06_vs_26'].sum(),
    df['jpy_pnl_06_vs_26'].sum(),
    df['usd_pnl_06_vs_26'].sum() + df['jpy_pnl_06_vs_26'].sum()
))
print("{:<35} {:>18,.0f} {:>18,.0f} {:>18,.0f}".format(
    "max(0,2,6)",
    df['usd_pnl_026_vs_26'].sum(),
    df['jpy_pnl_026_vs_26'].sum(),
    df['usd_pnl_026_vs_26'].sum() + df['jpy_pnl_026_vs_26'].sum()
))
print("{:<35} {:>18,.0f} {:>18,.0f} {:>18,.0f}".format(
    "Extended (Fri22:00~Sat06:00)",
    df['usd_pnl_ext_vs_26'].sum(),
    df['jpy_pnl_ext_vs_26'].sum(),
    df['usd_pnl_ext_vs_26'].sum() + df['jpy_pnl_ext_vs_26'].sum()
))

# Average weekly PnL
print("\n{:<35} {:>18} {:>18} {:>18}".format("Strategy", "USD Avg/Week", "JPY Avg/Week", "Total Avg/Week"))
print("-"*90)
print("{:<35} {:>18,.0f} {:>18,.0f} {:>18,.0f}".format(
    "max(0,6)",
    df['usd_pnl_06_vs_26'].mean(),
    df['jpy_pnl_06_vs_26'].mean(),
    df['usd_pnl_06_vs_26'].mean() + df['jpy_pnl_06_vs_26'].mean()
))
print("{:<35} {:>18,.0f} {:>18,.0f} {:>18,.0f}".format(
    "max(0,2,6)",
    df['usd_pnl_026_vs_26'].mean(),
    df['jpy_pnl_026_vs_26'].mean(),
    df['usd_pnl_026_vs_26'].mean() + df['jpy_pnl_026_vs_26'].mean()
))
print("{:<35} {:>18,.0f} {:>18,.0f} {:>18,.0f}".format(
    "Extended (Fri22:00~Sat06:00)",
    df['usd_pnl_ext_vs_26'].mean(),
    df['jpy_pnl_ext_vs_26'].mean(),
    df['usd_pnl_ext_vs_26'].mean() + df['jpy_pnl_ext_vs_26'].mean()
))

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Chart 1: USD bps comparison
ax1 = axes[0, 0]
x = range(len(df))
ax1.bar([i-0.25 for i in x], df['usd_bps_06_vs_26'], width=0.25, label='max(0,6)', color='steelblue', alpha=0.8)
ax1.bar([i for i in x], df['usd_bps_026_vs_26'], width=0.25, label='max(0,2,6)', color='darkorange', alpha=0.8)
ax1.bar([i+0.25 for i in x], df['usd_bps_ext_vs_26'], width=0.25, label='Extended', color='forestgreen', alpha=0.8)
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax1.set_title('USD BPS vs max(2,6) - Weekly', fontproperties=chinese_font_title)
ax1.set_xlabel('Week', fontproperties=chinese_font)
ax1.set_ylabel('BPS', fontproperties=chinese_font)
ax1.legend(prop=chinese_font_legend)
ax1.grid(True, alpha=0.3)

# Chart 2: JPY bps comparison
ax2 = axes[0, 1]
ax2.bar([i-0.25 for i in x], df['jpy_bps_06_vs_26'], width=0.25, label='max(0,6)', color='steelblue', alpha=0.8)
ax2.bar([i for i in x], df['jpy_bps_026_vs_26'], width=0.25, label='max(0,2,6)', color='darkorange', alpha=0.8)
ax2.bar([i+0.25 for i in x], df['jpy_bps_ext_vs_26'], width=0.25, label='Extended', color='forestgreen', alpha=0.8)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax2.set_title('JPY BPS vs max(2,6) - Weekly', fontproperties=chinese_font_title)
ax2.set_xlabel('Week', fontproperties=chinese_font)
ax2.set_ylabel('BPS', fontproperties=chinese_font)
ax2.legend(prop=chinese_font_legend)
ax2.grid(True, alpha=0.3)

# Chart 3: Cumulative PnL (USD vs JPY) for Extended strategy
ax3 = axes[1, 0]
df['usd_cum_pnl'] = df['usd_pnl_ext_vs_26'].cumsum()
df['jpy_cum_pnl'] = df['jpy_pnl_ext_vs_26'].cumsum()
ax3.plot(df['date'], df['usd_cum_pnl']/1e6, 'b-', linewidth=2, marker='o', markersize=4, label='USD')
ax3.plot(df['date'], df['jpy_cum_pnl']/1e6, 'r-', linewidth=2, marker='s', markersize=4, label='JPY')
ax3.set_title('Extended vs max(2,6): Cumulative PnL (Million CNH)', fontproperties=chinese_font_title)
ax3.set_xlabel('Date', fontproperties=chinese_font)
ax3.set_ylabel('Cumulative PnL (M CNH)', fontproperties=chinese_font)
ax3.legend(prop=chinese_font_legend)
ax3.grid(True, alpha=0.3)
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Chart 4: Summary bar chart
ax4 = axes[1, 1]
strategies_names = ['max(0,6)', 'max(0,2,6)', 'Extended']
usd_bps_avgs = [df['usd_bps_06_vs_26'].mean(), df['usd_bps_026_vs_26'].mean(), df['usd_bps_ext_vs_26'].mean()]
jpy_bps_avgs = [df['jpy_bps_06_vs_26'].mean(), df['jpy_bps_026_vs_26'].mean(), df['jpy_bps_ext_vs_26'].mean()]

x_pos = np.arange(len(strategies_names))
width = 0.35

bars1 = ax4.bar(x_pos - width/2, usd_bps_avgs, width, label='USD bps/week', color='steelblue')
bars2 = ax4.bar(x_pos + width/2, jpy_bps_avgs, width, label='JPY bps/week', color='indianred')

ax4.set_title('Average Weekly BPS vs max(2,6)', fontproperties=chinese_font_title)
ax4.set_ylabel('BPS per Week', fontproperties=chinese_font)
ax4.set_xticks(x_pos)
ax4.set_xticklabels(strategies_names)
ax4.legend(prop=chinese_font_legend)
ax4.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for bar, val in zip(bars1, usd_bps_avgs):
    ax4.annotate(f'{val:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                 ha='center', va='bottom', fontsize=10)
for bar, val in zip(bars2, jpy_bps_avgs):
    ax4.annotate(f'{val:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                 ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'bps_by_currency.png'), dpi=150, bbox_inches='tight')
print(f"\nChart saved to: output/bps_by_currency.png")

# Save detailed data
output_df = df[['date', 'ref_max_06', 'ref_max_26', 'ref_max_026', 'ref_extended',
                'jpycnh_max_06', 'jpycnh_max_26', 'jpycnh_max_026', 'jpycnh_extended',
                'usd_bps_06_vs_26', 'usd_bps_026_vs_26', 'usd_bps_ext_vs_26',
                'jpy_bps_06_vs_26', 'jpy_bps_026_vs_26', 'jpy_bps_ext_vs_26',
                'usd_pnl_06_vs_26', 'usd_pnl_026_vs_26', 'usd_pnl_ext_vs_26',
                'jpy_pnl_06_vs_26', 'jpy_pnl_026_vs_26', 'jpy_pnl_ext_vs_26']].copy()
output_df.to_excel(os.path.join(OUTPUT_DIR, 'bps_by_currency_detail.xlsx'), index=False)
print(f"Data saved to: output/bps_by_currency_detail.xlsx")

print("\n" + "="*80)
print("DONE!")
print("="*80)
