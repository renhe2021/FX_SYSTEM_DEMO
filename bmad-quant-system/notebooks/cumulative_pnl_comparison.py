"""
Cumulative PnL Comparison: max(0,6) vs max(2,6)
简单对比：两种USDCNH报价策略的累计收入差异
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

# 每周交易量
USD_WEEKLY_VOLUME = 60_000_000  # 6000万 USD/周

print("="*60)
print("Cumulative PnL: max(0,6) vs max(2,6)")
print("="*60)

# 加载已有的对比数据
df = pd.read_excel(os.path.join(OUTPUT_DIR, 'strategy_comparison_reference_detail.xlsx'))
print(f"Loaded {len(df)} weeks of data")

# 计算每周的CNH收入差异
# 报价差异 = ref_max_0_6 - ref_max_2_6 (USDCNH)
# CNH差异 = 报价差异 × USD交易量
df['weekly_pnl_diff_cnh'] = (df['ref_max_0_6'] - df['ref_max_2_6']) * USD_WEEKLY_VOLUME

# 各策略的CNH收入
df['pnl_max_0_6_cnh'] = df['ref_max_0_6'] * USD_WEEKLY_VOLUME
df['pnl_max_2_6_cnh'] = df['ref_max_2_6'] * USD_WEEKLY_VOLUME

# 累计
df['cumulative_diff_cnh'] = df['weekly_pnl_diff_cnh'].cumsum()
df['cumulative_max_0_6'] = df['pnl_max_0_6_cnh'].cumsum()
df['cumulative_max_2_6'] = df['pnl_max_2_6_cnh'].cumsum()

# 统计
print(f"\nTotal weeks: {len(df)}")
print(f"USD weekly volume: {USD_WEEKLY_VOLUME/1e6:.0f}M USD")
print(f"\nCumulative PnL difference (max(0,6) - max(2,6)):")
print(f"  Total: {df['cumulative_diff_cnh'].iloc[-1]:,.0f} CNH")
print(f"  Weekly avg: {df['weekly_pnl_diff_cnh'].mean():,.0f} CNH")
print(f"\nmax(0,6) wins: {(df['weekly_pnl_diff_cnh'] > 0).sum()} weeks")
print(f"max(2,6) wins: {(df['weekly_pnl_diff_cnh'] < 0).sum()} weeks")
print(f"Tie: {(df['weekly_pnl_diff_cnh'] == 0).sum()} weeks")

# 绘图
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
dates = pd.to_datetime(df['date'])

# 图1: 累计PnL差异 (主图)
ax1 = axes[0, 0]
ax1.fill_between(dates, 0, df['cumulative_diff_cnh'], 
                 where=(df['cumulative_diff_cnh'] >= 0), color='green', alpha=0.5, label='max(0,6) better')
ax1.fill_between(dates, 0, df['cumulative_diff_cnh'], 
                 where=(df['cumulative_diff_cnh'] < 0), color='red', alpha=0.5, label='max(2,6) better')
ax1.plot(dates, df['cumulative_diff_cnh'], 'b-', linewidth=2.5, marker='o', markersize=6)
ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax1.set_xlabel('Date', fontsize=12)
ax1.set_ylabel('Cumulative PnL Diff (CNH)', fontsize=12)
ax1.set_title('Cumulative PnL: max(0,6) - max(2,6)', fontsize=14, fontweight='bold')
ax1.legend(loc='best', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1e3:.0f}K'))

# 最终结果标注
final_diff = df['cumulative_diff_cnh'].iloc[-1]
ax1.annotate(f'Final: {final_diff/1e6:.2f}M CNH', 
             xy=(dates.iloc[-1], final_diff), xytext=(10, 10),
             textcoords='offset points', fontsize=11, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

# 图2: 每周PnL差异
ax2 = axes[0, 1]
colors = ['green' if x >= 0 else 'red' for x in df['weekly_pnl_diff_cnh']]
ax2.bar(range(len(df)), df['weekly_pnl_diff_cnh'], color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.axhline(y=df['weekly_pnl_diff_cnh'].mean(), color='blue', linestyle='--', linewidth=2, 
            label=f'Avg: {df["weekly_pnl_diff_cnh"].mean()/1e3:.0f}K CNH')
ax2.set_xlabel('Week', fontsize=12)
ax2.set_ylabel('Weekly PnL Diff (CNH)', fontsize=12)
ax2.set_title('Weekly PnL Difference: max(0,6) - max(2,6)', fontsize=14, fontweight='bold')
ax2.legend(loc='best', fontsize=10)
ax2.grid(True, alpha=0.3, axis='y')
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e3:.0f}K'))

# 统计文字
pos_count = (df['weekly_pnl_diff_cnh'] > 0).sum()
neg_count = (df['weekly_pnl_diff_cnh'] < 0).sum()
tie_count = (df['weekly_pnl_diff_cnh'] == 0).sum()
ax2.text(0.98, 0.95, f'max(0,6) wins: {pos_count}w\nmax(2,6) wins: {neg_count}w\nTie: {tie_count}w', 
         transform=ax2.transAxes, fontsize=11, va='top', ha='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 图3: 两策略累计收入对比
ax3 = axes[1, 0]
ax3.plot(dates, df['cumulative_max_0_6']/1e9, 'b-', linewidth=2.5, marker='o', markersize=5, label='max(0,6)')
ax3.plot(dates, df['cumulative_max_2_6']/1e9, 'r-', linewidth=2.5, marker='s', markersize=5, label='max(2,6)')
ax3.fill_between(dates, df['cumulative_max_0_6']/1e9, df['cumulative_max_2_6']/1e9, 
                 where=(df['cumulative_max_0_6'] >= df['cumulative_max_2_6']).values, 
                 color='green', alpha=0.3)
ax3.fill_between(dates, df['cumulative_max_0_6']/1e9, df['cumulative_max_2_6']/1e9, 
                 where=(df['cumulative_max_0_6'] < df['cumulative_max_2_6']).values, 
                 color='red', alpha=0.3)
ax3.set_xlabel('Date', fontsize=12)
ax3.set_ylabel('Cumulative Revenue (Billion CNH)', fontsize=12)
ax3.set_title('Cumulative Revenue: Both Strategies', fontsize=14, fontweight='bold')
ax3.legend(loc='best', fontsize=10)
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

# 图4: 汇总统计
ax4 = axes[1, 1]
ax4.axis('off')

summary_text = f'''
Strategy Comparison Summary
{'='*50}

Trading Volume: {USD_WEEKLY_VOLUME/1e6:.0f}M USD per week

Period: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}
Total Weeks: {len(df)}

Cumulative PnL Difference [max(0,6) - max(2,6)]:
  Total: {df['cumulative_diff_cnh'].iloc[-1]:,.0f} CNH ({df['cumulative_diff_cnh'].iloc[-1]/1e6:.2f}M)
  Weekly Average: {df['weekly_pnl_diff_cnh'].mean():,.0f} CNH ({df['weekly_pnl_diff_cnh'].mean()/1e3:.1f}K)
  
Win/Loss Record:
  max(0,6) wins: {pos_count} weeks ({pos_count/len(df)*100:.1f}%)
  max(2,6) wins: {neg_count} weeks ({neg_count/len(df)*100:.1f}%)
  Tie (same ref): {tie_count} weeks ({tie_count/len(df)*100:.1f}%)

Best Week for max(0,6): +{df['weekly_pnl_diff_cnh'].max():,.0f} CNH
Worst Week for max(0,6): {df['weekly_pnl_diff_cnh'].min():,.0f} CNH

Annualized Difference (52 weeks):
  ~{df['weekly_pnl_diff_cnh'].mean() * 52:,.0f} CNH ({df['weekly_pnl_diff_cnh'].mean() * 52/1e6:.2f}M)

CONCLUSION:
  {"max(0,6) is better" if final_diff > 0 else "max(2,6) is better" if final_diff < 0 else "Both strategies equal"}
  Extra revenue: {abs(final_diff):,.0f} CNH over {len(df)} weeks
'''

ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=11, va='top', 
         fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

plt.tight_layout()

# 保存
save_path = os.path.join(OUTPUT_DIR, 'cumulative_pnl_max06_vs_max26.png')
plt.savefig(save_path, dpi=150, bbox_inches='tight')
print(f'\nChart saved: {save_path}')
plt.close()
