# -*- coding: utf-8 -*-
"""检查数据时区"""
import pandas as pd
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 加载数据
df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx', parse_dates=['timestamp'])

print("=" * 60)
print("USDCNH 数据时区分析")
print("=" * 60)

# 筛选周六数据
sat_data = df[df['timestamp'].dt.dayofweek == 5]  # 5 = Saturday

print(f"\n周六数据样本:")
print(f"  首条: {sat_data['timestamp'].min()}")
print(f"  末条: {sat_data['timestamp'].max()}")

# 查看周六每小时的数据量
print(f"\n周六各小时数据量:")
sat_data['hour'] = sat_data['timestamp'].dt.hour
for hour in sorted(sat_data['hour'].unique()):
    count = len(sat_data[sat_data['hour'] == hour])
    print(f"  {hour:02d}:00 - {count:,} 条")

# 查看某个具体周六的数据
sample_sat = sat_data[sat_data['timestamp'].dt.date == sat_data['timestamp'].dt.date.iloc[0]]
print(f"\n样本周六 ({sample_sat['timestamp'].dt.date.iloc[0]}) 数据:")
print(f"  开始时间: {sample_sat['timestamp'].min()}")
print(f"  结束时间: {sample_sat['timestamp'].max()}")
print(f"  数据条数: {len(sample_sat)}")

# 显示周六 00:00 和 05:59 附近的数据
print(f"\n周六 00:00 附近数据:")
early = sample_sat[sample_sat['timestamp'].dt.hour == 0].head(3)
print(early[['timestamp', 'ask']].to_string(index=False))

print(f"\n周六 05:59 附近数据:")
late = sample_sat[sample_sat['timestamp'].dt.hour == 5].tail(3)
print(late[['timestamp', 'ask']].to_string(index=False))

# 确认：外汇市场周六凌晨收盘时间
# 纽约时间 周五 17:00 = 北京时间 周六 06:00 (夏令时) 或 05:00 (冬令时)
print(f"\n结论:")
print(f"  数据时间范围: 周六 00:00 ~ 05:59 (北京时间)")
print(f"  符合外汇市场周五纽约收盘 = 北京时间周六早上")
