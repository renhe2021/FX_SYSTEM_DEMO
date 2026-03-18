"""
三种策略对比: max(0,6) vs max(2,6) vs max(0,2,6)
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import warnings
warnings.filterwarnings('ignore')

# 中文字体设置
font_path = r'C:\Windows\Fonts\msyh.ttc'
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\simhei.ttf'
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\simsun.ttc'

chinese_font = FontProperties(fname=font_path, size=12)
chinese_font_title = FontProperties(fname=font_path, size=14)
chinese_font_legend = FontProperties(fname=font_path, size=11)

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

# 交易量
USD_WEEKLY_VOLUME = 60_000_000      
JPY_WEEKLY_VOLUME = 4_000_000_000   

print("="*70)
print("Three Strategy Comparison: max(0,6) vs max(2,6) vs max(0,2,6)")
print("="*70)

# 加载数据
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

# 准备周六数据
for df in [df_usdcnh, df_jpycnh]:
    df['weekday'] = df.index.dayofweek
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    if 'mid' not in df.columns:
        df['mid'] = (df['bid'] + df['ask']) / 2

usdcnh_sat = df_usdcnh[(df_usdcnh['weekday'] == 5) & (df_usdcnh['hour'] <= 6)].copy()
jpycnh_sat = df_jpycnh[(df_jpycnh['weekday'] == 5) & (df_jpycnh['hour'] <= 6)].copy()
common_dates = sorted(set(usdcnh_sat['date'].unique()) & set(jpycnh_sat['date'].unique()))
print(f"Common dates: {len(common_dates)} weeks")

# 计算每周PnL - 三种策略
weekly_data = []
for sat_date in common_dates:
    usdcnh_day = usdcnh_sat[usdcnh_sat['date'] == sat_date]
    jpycnh_day = jpycnh_sat[jpycnh_sat['date'] == sat_date]
    
    if usdcnh_day.empty or jpycnh_day.empty:
        continue
    
    usdcnh_h0 = usdcnh_day[usdcnh_day['hour'] == 0]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 0]) > 0 else np.nan
    usdcnh_h2 = usdcnh_day[usdcnh_day['hour'] == 2]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 2]) > 0 else np.nan
    usdcnh_h6 = usdcnh_day[usdcnh_day['hour'] == 6]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 6]) > 0 else np.nan
    jpycnh_avg = jpycnh_day['mid'].mean()
    jpycnh_per_jpy = jpycnh_avg / 100
    
    if pd.isna(usdcnh_h0) or pd.isna(usdcnh_h2) or pd.isna(usdcnh_h6):
        continue
    
    # 三种策略的参照物
    ref_max_0_6 = max(usdcnh_h0, usdcnh_h6)           # 策略1: max(0,6)
    ref_max_2_6 = max(usdcnh_h2, usdcnh_h6)           # 策略2: max(2,6)
    ref_max_0_2_6 = max(usdcnh_h0, usdcnh_h2, usdcnh_h6)  # 策略3: max(0,2,6)
    
    usdcnh_avg = usdcnh_day['mid'].mean()
    
    # ===== max(0,6) vs max(2,6) =====
    usd_diff_06_vs_26 = (ref_max_0_6 - ref_max_2_6) * USD_WEEKLY_VOLUME
    jpy_diff_06_vs_26 = (jpycnh_per_jpy * (ref_max_0_6 / usdcnh_avg) - jpycnh_per_jpy * (ref_max_2_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    # ===== max(0,2,6) vs max(0,6) =====
    usd_diff_026_vs_06 = (ref_max_0_2_6 - ref_max_0_6) * USD_WEEKLY_VOLUME
    jpy_diff_026_vs_06 = (jpycnh_per_jpy * (ref_max_0_2_6 / usdcnh_avg) - jpycnh_per_jpy * (ref_max_0_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    # ===== max(0,2,6) vs max(2,6) =====
    usd_diff_026_vs_26 = (ref_max_0_2_6 - ref_max_2_6) * USD_WEEKLY_VOLUME
    jpy_diff_026_vs_26 = (jpycnh_per_jpy * (ref_max_0_2_6 / usdcnh_avg) - jpycnh_per_jpy * (ref_max_2_6 / usdcnh_avg)) * JPY_WEEKLY_VOLUME
    
    weekly_data.append({
        'date': sat_date,
        'usdcnh_h0': usdcnh_h0,
        'usdcnh_h2': usdcnh_h2,
        'usdcnh_h6': usdcnh_h6,
        'ref_max_0_6': ref_max_0_6,
        'ref_max_2_6': ref_max_2_6,
        'ref_max_0_2_6': ref_max_0_2_6,
        # max(0,6) vs max(2,6)
        'usd_diff_06_vs_26': usd_diff_06_vs_26,
        'jpy_diff_06_vs_26': jpy_diff_06_vs_26,
        'total_diff_06_vs_26': usd_diff_06_vs_26 + jpy_diff_06_vs_26,
        # max(0,2,6) vs max(0,6)
        'usd_diff_026_vs_06': usd_diff_026_vs_06,
        'jpy_diff_026_vs_06': jpy_diff_026_vs_06,
        'total_diff_026_vs_06': usd_diff_026_vs_06 + jpy_diff_026_vs_06,
        # max(0,2,6) vs max(2,6)
        'usd_diff_026_vs_26': usd_diff_026_vs_26,
        'jpy_diff_026_vs_26': jpy_diff_026_vs_26,
        'total_diff_026_vs_26': usd_diff_026_vs_26 + jpy_diff_026_vs_26,
    })

df = pd.DataFrame(weekly_data)

# 累计
df['cum_06_vs_26'] = df['total_diff_06_vs_26'].cumsum()
df['cum_026_vs_06'] = df['total_diff_026_vs_06'].cumsum()
df['cum_026_vs_26'] = df['total_diff_026_vs_26'].cumsum()

# USD + JPY 分开累计
df['usd_cum_06_vs_26'] = df['usd_diff_06_vs_26'].cumsum()
df['jpy_cum_06_vs_26'] = df['jpy_diff_06_vs_26'].cumsum()
df['usd_cum_026_vs_06'] = df['usd_diff_026_vs_06'].cumsum()
df['jpy_cum_026_vs_06'] = df['jpy_diff_026_vs_06'].cumsum()
df['usd_cum_026_vs_26'] = df['usd_diff_026_vs_26'].cumsum()
df['jpy_cum_026_vs_26'] = df['jpy_diff_026_vs_26'].cumsum()

print(f"\n" + "="*70)
print("Cumulative PnL Differences (Total: USD + JPY)")
print("="*70)
print(f"max(0,6) vs max(2,6):   {df['cum_06_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_06_vs_26'].iloc[-1]/1e6:.2f}M)")
print(f"max(0,2,6) vs max(0,6): {df['cum_026_vs_06'].iloc[-1]:>12,.0f} CNH ({df['cum_026_vs_06'].iloc[-1]/1e6:.2f}M)")
print(f"max(0,2,6) vs max(2,6): {df['cum_026_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_026_vs_26'].iloc[-1]/1e6:.2f}M)")

# ============ 绘图 ============
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

dates = pd.to_datetime(df['date'])

# ---- 图1: 三种策略的参照价对比 ----
ax1 = axes[0, 0]
ax1.plot(dates, df['ref_max_0_6'], 'b-', linewidth=2, marker='o', markersize=5, label='max(0,6)')
ax1.plot(dates, df['ref_max_2_6'], 'g-', linewidth=2, marker='s', markersize=5, label='max(2,6)')
ax1.plot(dates, df['ref_max_0_2_6'], 'r-', linewidth=2.5, marker='^', markersize=6, label='max(0,2,6)')
ax1.set_xlabel('日期', fontproperties=chinese_font)
ax1.set_ylabel('USDCNH 参照价', fontproperties=chinese_font)
ax1.set_title('三种策略的USDCNH参照价对比', fontproperties=chinese_font_title)
ax1.legend(['max(0,6)', 'max(2,6)', 'max(0,2,6)'], loc='upper left', prop=chinese_font_legend)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

# ---- 图2: 累计PnL对比 (以max(2,6)为基准) ----
ax2 = axes[0, 1]
ax2.plot(dates, df['cum_06_vs_26']/1e6, 'b-', linewidth=2.5, marker='o', markersize=6)
ax2.plot(dates, df['cum_026_vs_26']/1e6, 'r-', linewidth=2.5, marker='^', markersize=6)
ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
ax2.fill_between(dates, 0, df['cum_026_vs_26']/1e6, where=(df['cum_026_vs_26'] >= 0), color='red', alpha=0.1)

final_06_vs_26 = df['cum_06_vs_26'].iloc[-1]/1e6
final_026_vs_26 = df['cum_026_vs_26'].iloc[-1]/1e6

ax2.annotate(f'max(0,6): {final_06_vs_26:.2f}M', xy=(dates.iloc[-1], final_06_vs_26), xytext=(10, 0),
            textcoords='offset points', fontsize=11, color='blue', fontweight='bold', fontproperties=chinese_font)
ax2.annotate(f'max(0,2,6): {final_026_vs_26:.2f}M', xy=(dates.iloc[-1], final_026_vs_26), xytext=(10, 5),
            textcoords='offset points', fontsize=11, color='red', fontweight='bold', fontproperties=chinese_font,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

ax2.set_xlabel('日期', fontproperties=chinese_font)
ax2.set_ylabel('累计PnL差异 (百万 CNH)', fontproperties=chinese_font)
ax2.set_title('累计PnL对比 (相对于 max(2,6) 基准)\n正值=该策略更优', fontproperties=chinese_font_title)
legend_labels = ['max(0,6) - max(2,6)', 'max(0,2,6) - max(2,6)']
ax2.legend(legend_labels, loc='upper left', prop=chinese_font_legend)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

# ---- 图3: max(0,2,6) vs max(0,6) 累计差异 ----
ax3 = axes[1, 0]
ax3.plot(dates, df['usd_cum_026_vs_06']/1e6, 'b-', linewidth=2.5, marker='o', markersize=5)
ax3.plot(dates, df['jpy_cum_026_vs_06']/1e6, 'g-', linewidth=2.5, marker='s', markersize=5)
ax3.plot(dates, df['cum_026_vs_06']/1e6, 'r-', linewidth=3, marker='^', markersize=6)
ax3.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
ax3.fill_between(dates, 0, df['cum_026_vs_06']/1e6, where=(df['cum_026_vs_06'] >= 0), color='green', alpha=0.1)
ax3.fill_between(dates, 0, df['cum_026_vs_06']/1e6, where=(df['cum_026_vs_06'] < 0), color='red', alpha=0.1)

final_usd = df['usd_cum_026_vs_06'].iloc[-1]/1e6
final_jpy = df['jpy_cum_026_vs_06'].iloc[-1]/1e6
final_total = df['cum_026_vs_06'].iloc[-1]/1e6

ax3.annotate(f'美金: {final_usd:.2f}M', xy=(dates.iloc[-1], final_usd), xytext=(10, 0),
            textcoords='offset points', fontsize=10, color='blue', fontweight='bold', fontproperties=chinese_font)
ax3.annotate(f'日元: {final_jpy:.2f}M', xy=(dates.iloc[-1], final_jpy), xytext=(10, 0),
            textcoords='offset points', fontsize=10, color='green', fontweight='bold', fontproperties=chinese_font)
ax3.annotate(f'合计: {final_total:.2f}M', xy=(dates.iloc[-1], final_total), xytext=(10, 5),
            textcoords='offset points', fontsize=11, color='red', fontweight='bold', fontproperties=chinese_font,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

ax3.set_xlabel('日期', fontproperties=chinese_font)
ax3.set_ylabel('累计PnL差异 (百万 CNH)', fontproperties=chinese_font)
ax3.set_title('max(0,2,6) vs max(0,6) 累计PnL差异\n正值=max(0,2,6)更优', fontproperties=chinese_font_title)
legend_labels3 = ['美金', '日元', '合计']
ax3.legend(legend_labels3, loc='upper left', prop=chinese_font_legend)
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

# ---- 图4: 统计汇总 ----
ax4 = axes[1, 1]
ax4.axis('off')

# 统计信息
stats_text = f"""
策略对比统计汇总
{'='*50}

回测期间: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}
总周数: {len(df)}

交易量:
  美金: 6000万 USD/周
  日元: 40亿 JPY/周

{'='*50}
累计PnL差异 (正值=前者更优)
{'='*50}

1. max(0,6) vs max(2,6):
   美金: {df['usd_cum_06_vs_26'].iloc[-1]:>12,.0f} CNH
   日元: {df['jpy_cum_06_vs_26'].iloc[-1]:>12,.0f} CNH
   合计: {df['cum_06_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_06_vs_26'].iloc[-1]/1e6:.2f}M)

2. max(0,2,6) vs max(0,6):
   美金: {df['usd_cum_026_vs_06'].iloc[-1]:>12,.0f} CNH
   日元: {df['jpy_cum_026_vs_06'].iloc[-1]:>12,.0f} CNH
   合计: {df['cum_026_vs_06'].iloc[-1]:>12,.0f} CNH ({df['cum_026_vs_06'].iloc[-1]/1e6:.2f}M)

3. max(0,2,6) vs max(2,6):
   美金: {df['usd_cum_026_vs_26'].iloc[-1]:>12,.0f} CNH
   日元: {df['jpy_cum_026_vs_26'].iloc[-1]:>12,.0f} CNH
   合计: {df['cum_026_vs_26'].iloc[-1]:>12,.0f} CNH ({df['cum_026_vs_26'].iloc[-1]/1e6:.2f}M)

{'='*50}
结论: max(0,2,6) 策略最优!
  相比 max(0,6): 多赚 {df['cum_026_vs_06'].iloc[-1]:,.0f} CNH
  相比 max(2,6): 多赚 {df['cum_026_vs_26'].iloc[-1]:,.0f} CNH
"""

ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=11,
         verticalalignment='top', fontproperties=chinese_font,
         family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
save_path = os.path.join(OUTPUT_DIR, 'strategy_comparison_3way.png')
plt.savefig(save_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved: {save_path}")
plt.close()

# 保存详细数据
df.to_excel(os.path.join(OUTPUT_DIR, 'strategy_comparison_3way_detail.xlsx'), index=False)
print(f"Data saved: {os.path.join(OUTPUT_DIR, 'strategy_comparison_3way_detail.xlsx')}")

# 打印统计
print(f"\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\nPeriod: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
print(f"Weeks: {len(df)}")

print(f"\n--- Cumulative PnL Difference ---")
print(f"{'Comparison':<25} {'USD':>15} {'JPY':>15} {'Total':>15}")
print("-"*70)
print(f"{'max(0,6) vs max(2,6)':<25} {df['usd_cum_06_vs_26'].iloc[-1]:>12,.0f} {df['jpy_cum_06_vs_26'].iloc[-1]:>12,.0f} {df['cum_06_vs_26'].iloc[-1]:>12,.0f}")
print(f"{'max(0,2,6) vs max(0,6)':<25} {df['usd_cum_026_vs_06'].iloc[-1]:>12,.0f} {df['jpy_cum_026_vs_06'].iloc[-1]:>12,.0f} {df['cum_026_vs_06'].iloc[-1]:>12,.0f}")
print(f"{'max(0,2,6) vs max(2,6)':<25} {df['usd_cum_026_vs_26'].iloc[-1]:>12,.0f} {df['jpy_cum_026_vs_26'].iloc[-1]:>12,.0f} {df['cum_026_vs_26'].iloc[-1]:>12,.0f}")
print("-"*70)

print(f"\nConclusion: max(0,2,6) is the BEST strategy!")
print(f"  vs max(0,6): +{df['cum_026_vs_06'].iloc[-1]:,.0f} CNH ({df['cum_026_vs_06'].iloc[-1]/1e6:.2f}M)")
print(f"  vs max(2,6): +{df['cum_026_vs_26'].iloc[-1]:,.0f} CNH ({df['cum_026_vs_26'].iloc[-1]/1e6:.2f}M)")
