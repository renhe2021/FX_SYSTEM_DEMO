# -*- coding: utf-8 -*-
"""验证脚本：对比原始数据 vs API 结果"""
import sys, os, io

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pnl-analysis'))

import pandas as pd
from data_loader import load_csv, calc_derived_fields

data_dir = os.path.join(os.path.dirname(__file__), 'ddd', '20260310151934', 'data')

# 加载原始数据
df1 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260131.csv')))
df2 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260228.csv')))

print("=" * 80)
print("原始数据验证")
print("=" * 80)

# 按渠道
print("\n=== 2026年1月 - 按渠道 ===")
g1 = df1.groupby('损益实际归属主体')[['损益金额','其中WX','FIT']].sum().round(2)
print(g1.to_string())
print(f"合计: 损益={df1['损益金额'].sum():.2f}  WX={df1['其中WX'].sum():.2f}  FIT={df1['FIT'].sum():.2f}")

print("\n=== 2026年2月 - 按渠道 ===")
g2 = df2.groupby('损益实际归属主体')[['损益金额','其中WX','FIT']].sum().round(2)
print(g2.to_string())
print(f"合计: 损益={df2['损益金额'].sum():.2f}  WX={df2['其中WX'].sum():.2f}  FIT={df2['FIT'].sum():.2f}")

print("\n=== 累计 - 按渠道 ===")
df_all = pd.concat([df1, df2])
g_all = df_all.groupby('损益实际归属主体')[['损益金额','其中WX','FIT']].sum().round(2)
print(g_all.to_string())
print(f"合计: 损益={df_all['损益金额'].sum():.2f}  WX={df_all['其中WX'].sum():.2f}  FIT={df_all['FIT'].sum():.2f}")

# 按业务
print("\n=== 2026年1月 - 按业务 ===")
b1 = df1.groupby('所属业务')[['损益金额','其中WX','FIT']].sum().sort_values('损益金额', ascending=False).round(2)
print(b1.to_string())

print("\n=== 2026年2月 - 按业务 ===")
b2 = df2.groupby('所属业务')[['损益金额','其中WX','FIT']].sum().sort_values('损益金额', ascending=False).round(2)
print(b2.to_string())

# 按币种
print("\n=== 2026年1月 - 按币种 (top 10) ===")
c1 = df1.groupby('原币种')[['损益金额','其中WX','FIT']].sum().sort_values('损益金额', ascending=False).round(2)
print(c1.head(10).to_string())

print("\n=== 2026年2月 - 按币种 (top 10) ===")
c2 = df2.groupby('原币种')[['损益金额','其中WX','FIT']].sum().sort_values('损益金额', ascending=False).round(2)
print(c2.head(10).to_string())

# 记录数
print(f"\n=== 记录数: 1月={len(df1)}, 2月={len(df2)}, 合计={len(df_all)} ===")
