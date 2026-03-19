"""
快速运行: USD + JPY 累计PnL对比 (中文版)
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import warnings
warnings.filterwarnings('ignore')

# 使用Windows系统字体文件直接加载中文字体
font_path = r'C:\Windows\Fonts\msyh.ttc'  # 微软雅黑
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\simhei.ttf'  # 黑体
if not os.path.exists(font_path):
    font_path = r'C:\Windows\Fonts\simsun.ttc'  # 宋体

chinese_font = FontProperties(fname=font_path, size=12)
chinese_font_title = FontProperties(fname=font_path, size=14)
chinese_font_legend = FontProperties(fname=font_path, size=11)

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

# 交易量
USD_WEEKLY_VOLUME = 60_000_000      
JPY_WEEKLY_VOLUME = 4_000_000_000   

print("="*60)
print("USD + JPY Cumulative PnL: max(0,6) vs max(2,6)")
print("="*60)

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

# 计算每周PnL
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
    
    ref_max_0_6 = max(usdcnh_h0, usdcnh_h6)
    ref_max_2_6 = max(usdcnh_h2, usdcnh_h6)
    
    # USD PnL
    usd_pnl_diff = (ref_max_0_6 - ref_max_2_6) * USD_WEEKLY_VOLUME
    
    # JPY PnL (按比例调整)
    usdcnh_avg = usdcnh_day['mid'].mean()
    jpycnh_for_max_0_6 = jpycnh_per_jpy * (ref_max_0_6 / usdcnh_avg)
    jpycnh_for_max_2_6 = jpycnh_per_jpy * (ref_max_2_6 / usdcnh_avg)
    jpy_pnl_diff = (jpycnh_for_max_0_6 - jpycnh_for_max_2_6) * JPY_WEEKLY_VOLUME
    
    weekly_data.append({
        'date': sat_date,
        'usd_pnl_diff': usd_pnl_diff,
        'jpy_pnl_diff': jpy_pnl_diff,
        'total_pnl_diff': usd_pnl_diff + jpy_pnl_diff,
    })

df = pd.DataFrame(weekly_data)

# 累计
df['usd_cum_diff'] = df['usd_pnl_diff'].cumsum()
df['jpy_cum_diff'] = df['jpy_pnl_diff'].cumsum()
df['total_cum_diff'] = df['total_pnl_diff'].cumsum()

print(f"\nCumulative PnL Difference [max(0,6) - max(2,6)]:")
print(f"  USD:   {df['usd_cum_diff'].iloc[-1]:>12,.0f} CNH ({df['usd_cum_diff'].iloc[-1]/1e6:.2f}M)")
print(f"  JPY:   {df['jpy_cum_diff'].iloc[-1]:>12,.0f} CNH ({df['jpy_cum_diff'].iloc[-1]/1e6:.2f}M)")
print(f"  Total: {df['total_cum_diff'].iloc[-1]:>12,.0f} CNH ({df['total_cum_diff'].iloc[-1]/1e6:.2f}M)")

# 绘图
fig, ax = plt.subplots(figsize=(14, 8))
dates = pd.to_datetime(df['date'])

ax.plot(dates, df['usd_cum_diff']/1e6, 'b-', linewidth=2.5, marker='o', markersize=6, label='USD')
ax.plot(dates, df['jpy_cum_diff']/1e6, 'g-', linewidth=2.5, marker='s', markersize=6, label='JPY')
ax.plot(dates, df['total_cum_diff']/1e6, 'r-', linewidth=3, marker='^', markersize=8, label='Total')

ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
ax.fill_between(dates, 0, df['total_cum_diff']/1e6, where=(df['total_cum_diff'] >= 0), color='green', alpha=0.15)
ax.fill_between(dates, 0, df['total_cum_diff']/1e6, where=(df['total_cum_diff'] < 0), color='red', alpha=0.15)

# 标注
final_usd = df['usd_cum_diff'].iloc[-1]/1e6
final_jpy = df['jpy_cum_diff'].iloc[-1]/1e6
final_total = df['total_cum_diff'].iloc[-1]/1e6

ax.annotate(f'美金: {final_usd:.2f}M', xy=(dates.iloc[-1], final_usd), xytext=(10, 0),
            textcoords='offset points', fontsize=11, color='blue', fontweight='bold', fontproperties=chinese_font)
ax.annotate(f'日元: {final_jpy:.2f}M', xy=(dates.iloc[-1], final_jpy), xytext=(10, 0),
            textcoords='offset points', fontsize=11, color='green', fontweight='bold', fontproperties=chinese_font)
ax.annotate(f'合计: {final_total:.2f}M', xy=(dates.iloc[-1], final_total), xytext=(10, 5),
            textcoords='offset points', fontsize=12, color='red', fontweight='bold', fontproperties=chinese_font,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

ax.set_xlabel('日期', fontproperties=chinese_font)
ax.set_ylabel('累计PnL差异 (百万 CNH)', fontproperties=chinese_font)
ax.set_title('累计PnL对比: max(0,6) - max(2,6)\n(正值表示 max(0,6) 策略更优)', fontproperties=chinese_font_title)

# 创建中文图例
legend_labels = ['美金 (6000万/周)', '日元 (40亿/周)', '合计 (美金+日元)']
legend = ax.legend(legend_labels, loc='upper left', prop=chinese_font_legend)

ax.grid(True, alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

plt.tight_layout()
save_path = os.path.join(OUTPUT_DIR, 'cumulative_pnl_usd_jpy_total.png')
plt.savefig(save_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved: {save_path}")
plt.close()

# 统计
print(f"\n" + "="*60)
print("Summary")
print("="*60)
print(f"Period: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
print(f"Weeks: {len(df)}")
print(f"\nWeekly Average Difference:")
print(f"  USD:   {df['usd_pnl_diff'].mean():>10,.0f} CNH/week")
print(f"  JPY:   {df['jpy_pnl_diff'].mean():>10,.0f} CNH/week")
print(f"  Total: {df['total_pnl_diff'].mean():>10,.0f} CNH/week")
print(f"\nAnnualized (52 weeks):")
print(f"  USD:   {df['usd_pnl_diff'].mean()*52:>12,.0f} CNH ({df['usd_pnl_diff'].mean()*52/1e6:.2f}M)")
print(f"  JPY:   {df['jpy_pnl_diff'].mean()*52:>12,.0f} CNH ({df['jpy_pnl_diff'].mean()*52/1e6:.2f}M)")
print(f"  Total: {df['total_pnl_diff'].mean()*52:>12,.0f} CNH ({df['total_pnl_diff'].mean()*52/1e6:.2f}M)")
print(f"\nConclusion: {'max(0,6) is BETTER!' if df['total_cum_diff'].iloc[-1] > 0 else 'max(2,6) is BETTER!'}")
