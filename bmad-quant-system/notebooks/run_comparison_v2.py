"""
Strategy Comparison: max(0,6) vs max(2,6)
正确版本：展示参照物选择对报价质量的影响
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
print("Reference selection impact analysis")
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

# 收集每周的参照物选择数据
weekly_data = []

for sat_date in common_dates:
    jpycnh_day = jpycnh_sat[jpycnh_sat['date'] == sat_date].copy()
    usdcnh_day = usdcnh_sat[usdcnh_sat['date'] == sat_date].copy()
    
    if jpycnh_day.empty or usdcnh_day.empty:
        continue
    
    # 获取各小时USDCNH价格
    usdcnh_h0 = usdcnh_day[usdcnh_day['hour'] == 0]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 0]) > 0 else np.nan
    usdcnh_h2 = usdcnh_day[usdcnh_day['hour'] == 2]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 2]) > 0 else np.nan
    usdcnh_h6 = usdcnh_day[usdcnh_day['hour'] == 6]['mid'].mean() if len(usdcnh_day[usdcnh_day['hour'] == 6]) > 0 else np.nan
    
    if pd.isna(usdcnh_h0) or pd.isna(usdcnh_h2) or pd.isna(usdcnh_h6):
        continue
    
    # 参照物选择
    ref_0_6 = max(usdcnh_h0, usdcnh_h6)
    ref_2_6 = max(usdcnh_h2, usdcnh_h6)
    
    # 参照物来源
    ref_0_6_from = 'h0' if usdcnh_h0 >= usdcnh_h6 else 'h6'
    ref_2_6_from = 'h2' if usdcnh_h2 >= usdcnh_h6 else 'h6'
    
    # 计算USDCNH变化 (bps)
    change_0_to_6 = (usdcnh_h6 - usdcnh_h0) / usdcnh_h0 * 10000
    change_2_to_6 = (usdcnh_h6 - usdcnh_h2) / usdcnh_h2 * 10000
    
    weekly_data.append({
        'date': sat_date,
        'usdcnh_h0': usdcnh_h0,
        'usdcnh_h2': usdcnh_h2,
        'usdcnh_h6': usdcnh_h6,
        'ref_max_0_6': ref_0_6,
        'ref_max_2_6': ref_2_6,
        'ref_0_6_from': ref_0_6_from,
        'ref_2_6_from': ref_2_6_from,
        'change_0_to_6_bps': change_0_to_6,
        'change_2_to_6_bps': change_2_to_6,
        'diff_ref': ref_0_6 - ref_2_6,  # 参照物差异
        'diff_ref_bps': (ref_0_6 - ref_2_6) / ref_2_6 * 10000 if ref_2_6 != 0 else 0,
    })

df_weekly = pd.DataFrame(weekly_data)

print(f"\nAnalyzed {len(df_weekly)} weeks of data")

# Reference selection statistics
print("\n" + "="*60)
print("Reference Selection Statistics")
print("="*60)

# max(0,6) strategy stats
h0_count = (df_weekly['ref_0_6_from'] == 'h0').sum()
h6_count_0_6 = (df_weekly['ref_0_6_from'] == 'h6').sum()
print(f"\nmax(0,6) Strategy:")
print(f"  Choose hour_0: {h0_count} weeks ({h0_count/len(df_weekly)*100:.1f}%)")
print(f"  Choose hour_6: {h6_count_0_6} weeks ({h6_count_0_6/len(df_weekly)*100:.1f}%)")

# max(2,6) strategy stats
h2_count = (df_weekly['ref_2_6_from'] == 'h2').sum()
h6_count_2_6 = (df_weekly['ref_2_6_from'] == 'h6').sum()
print(f"\nmax(2,6) Strategy:")
print(f"  Choose hour_2: {h2_count} weeks ({h2_count/len(df_weekly)*100:.1f}%)")
print(f"  Choose hour_6: {h6_count_2_6} weeks ({h6_count_2_6/len(df_weekly)*100:.1f}%)")

# Different reference selection comparison
diff_choice = (df_weekly['ref_0_6_from'] != df_weekly['ref_2_6_from']).sum()
same_choice = (df_weekly['ref_0_6_from'] == df_weekly['ref_2_6_from']).sum()
print(f"\nStrategy Choice Comparison:")
print(f"  Same reference: {same_choice} weeks ({same_choice/len(df_weekly)*100:.1f}%)")
print(f"  Different reference: {diff_choice} weeks ({diff_choice/len(df_weekly)*100:.1f}%)")

# Reference value difference stats
print(f"\nReference Value Difference:")
print(f"  Average diff: {df_weekly['diff_ref'].mean():.6f} USDCNH")
print(f"  Average diff: {df_weekly['diff_ref_bps'].mean():.2f} bps")
print(f"  max(0,6) ref higher: {(df_weekly['diff_ref'] > 0).sum()} weeks")
print(f"  max(2,6) ref higher: {(df_weekly['diff_ref'] < 0).sum()} weeks")
print(f"  Same reference: {(df_weekly['diff_ref'] == 0).sum()} weeks")

# 绘图
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
dates = pd.to_datetime(df_weekly['date'])

# 图1: USDCNH各小时价格比较
ax1 = axes[0, 0]
ax1.plot(dates, df_weekly['usdcnh_h0'], 'b-', linewidth=2, marker='o', markersize=5, label='Hour 0')
ax1.plot(dates, df_weekly['usdcnh_h2'], 'g-', linewidth=2, marker='s', markersize=5, label='Hour 2')
ax1.plot(dates, df_weekly['usdcnh_h6'], 'r-', linewidth=2, marker='^', markersize=5, label='Hour 6')
ax1.set_xlabel('Date', fontsize=12)
ax1.set_ylabel('USDCNH', fontsize=12)
ax1.set_title('USDCNH at Different Hours (Saturday)', fontsize=14, fontweight='bold')
ax1.legend(loc='best', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

# 图2: 参照物对比
ax2 = axes[0, 1]
ax2.plot(dates, df_weekly['ref_max_0_6'], 'b-', linewidth=2.5, marker='o', markersize=5, label='max(0,6) Ref')
ax2.plot(dates, df_weekly['ref_max_2_6'], 'r-', linewidth=2.5, marker='s', markersize=5, label='max(2,6) Ref')
ax2.fill_between(dates, df_weekly['ref_max_0_6'], df_weekly['ref_max_2_6'], 
                 where=(df_weekly['ref_max_0_6'].values >= df_weekly['ref_max_2_6'].values), 
                 color='blue', alpha=0.3, label='max(0,6) higher')
ax2.fill_between(dates, df_weekly['ref_max_0_6'], df_weekly['ref_max_2_6'], 
                 where=(df_weekly['ref_max_0_6'].values < df_weekly['ref_max_2_6'].values), 
                 color='red', alpha=0.3, label='max(2,6) higher')
ax2.set_xlabel('Date', fontsize=12)
ax2.set_ylabel('Reference USDCNH', fontsize=12)
ax2.set_title('Reference Price Comparison', fontsize=14, fontweight='bold')
ax2.legend(loc='best', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

# 图3: 参照物差异 (bps)
ax3 = axes[1, 0]
diff_bps = df_weekly['diff_ref_bps']
colors = ['blue' if x >= 0 else 'red' for x in diff_bps]
ax3.bar(range(len(diff_bps)), diff_bps, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax3.axhline(y=diff_bps.mean(), color='green', linestyle='--', linewidth=2, label=f'Avg: {diff_bps.mean():.2f} bps')
ax3.set_xlabel('Week', fontsize=12)
ax3.set_ylabel('Reference Difference (bps)', fontsize=12)
ax3.set_title('Reference Price Difference [max(0,6) - max(2,6)]', fontsize=14, fontweight='bold')
ax3.legend(loc='best', fontsize=10)
ax3.grid(True, alpha=0.3, axis='y')

# 统计文字
pos_count = (diff_bps >= 0).sum()
neg_count = (diff_bps < 0).sum()
ax3.text(0.98, 0.95, f'max(0,6) higher: {pos_count}w\nmax(2,6) higher: {neg_count}w', 
         transform=ax3.transAxes, fontsize=11, va='top', ha='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 图4: 参照物选择分布
ax4 = axes[1, 1]

# 创建饼图数据
labels_0_6 = ['Hour 0', 'Hour 6']
sizes_0_6 = [h0_count, h6_count_0_6]
labels_2_6 = ['Hour 2', 'Hour 6']
sizes_2_6 = [h2_count, h6_count_2_6]

# 子图
ax4_1 = fig.add_axes([0.55, 0.1, 0.18, 0.35])
ax4_2 = fig.add_axes([0.77, 0.1, 0.18, 0.35])

colors_pie = ['steelblue', 'coral']
ax4_1.pie(sizes_0_6, labels=labels_0_6, autopct='%1.1f%%', colors=colors_pie, startangle=90)
ax4_1.set_title('max(0,6) Selection', fontsize=11, fontweight='bold')

ax4_2.pie(sizes_2_6, labels=labels_2_6, autopct='%1.1f%%', colors=['green', 'coral'], startangle=90)
ax4_2.set_title('max(2,6) Selection', fontsize=11, fontweight='bold')

ax4.axis('off')

# 添加汇总文字
summary = f'''
Reference Selection Summary
{'='*40}

max(0,6) Strategy:
  - Chooses Hour 0: {h0_count} weeks ({h0_count/len(df_weekly)*100:.1f}%)
  - Chooses Hour 6: {h6_count_0_6} weeks ({h6_count_0_6/len(df_weekly)*100:.1f}%)

max(2,6) Strategy:
  - Chooses Hour 2: {h2_count} weeks ({h2_count/len(df_weekly)*100:.1f}%)
  - Chooses Hour 6: {h6_count_2_6} weeks ({h6_count_2_6/len(df_weekly)*100:.1f}%)

Reference Difference:
  - Avg diff: {df_weekly['diff_ref_bps'].mean():.2f} bps
  - max(0,6) higher: {(df_weekly['diff_ref'] > 0).sum()} weeks
  - max(2,6) higher: {(df_weekly['diff_ref'] < 0).sum()} weeks
'''
ax4.text(0.02, 0.95, summary, transform=ax4.transAxes, fontsize=10, va='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

plt.tight_layout()
save_path = os.path.join(OUTPUT_DIR, 'strategy_comparison_max06_vs_max26_reference.png')
plt.savefig(save_path, dpi=150, bbox_inches='tight')
print(f'\nChart saved: {save_path}')
plt.close()

# 保存详细数据
df_weekly.to_excel(os.path.join(OUTPUT_DIR, 'strategy_comparison_reference_detail.xlsx'), index=False)
print(f'Detail saved: strategy_comparison_reference_detail.xlsx')
