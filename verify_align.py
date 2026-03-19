# -*- coding: utf-8 -*-
import sys, os, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pnl-analysis'))

import pandas as pd
from data_loader import load_csv, calc_derived_fields

data_dir = os.path.join(os.path.dirname(__file__), 'ddd', '20260310151934', 'data')
df1 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260131.csv')))
df2 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260228.csv')))

print("=" * 70)
print("按业务 (千元) — 和截图对比")
print("=" * 70)

b1 = df1.groupby('所属业务')[['损益金额','其中WX','FIT']].sum()
b2 = df2.groupby('所属业务')[['损益金额','其中WX','FIT']].sum()

# Merge for side-by-side
merged = b1[['损益金额']].rename(columns={'损益金额':'1月-损益'}).join(
    b2[['损益金额']].rename(columns={'损益金额':'2月-损益'}), how='outer'
).fillna(0)
merged['1月(千元)'] = (merged['1月-损益'] / 1000).round(0).astype(int)
merged['2月(千元)'] = (merged['2月-损益'] / 1000).round(0).astype(int)

print(merged[['1月(千元)','2月(千元)']].sort_values('1月(千元)', ascending=False).to_string())

print()
print("=" * 70)
print("按渠道 (千元)")
print("=" * 70)

e1 = df1.groupby('损益实际归属主体')[['损益金额','其中WX','FIT']].sum()
e2 = df2.groupby('损益实际归属主体')[['损益金额','其中WX','FIT']].sum()

merged_e = pd.DataFrame({
    '1月-损益(千元)': (e1['损益金额']/1000).round(0),
    '1月-WX(千元)': (e1['其中WX']/1000).round(0),
    '1月-FIT(千元)': (e1['FIT']/1000).round(0),
    '2月-损益(千元)': (e2['损益金额']/1000).round(0),
    '2月-WX(千元)': (e2['其中WX']/1000).round(0),
    '2月-FIT(千元)': (e2['FIT']/1000).round(0),
}).fillna(0).astype(int)
print(merged_e.to_string())

print()
print("=" * 70)
print("总量 (千元)")
print("=" * 70)
t1 = df1[['损益金额','其中WX','FIT']].sum()
t2 = df2[['损益金额','其中WX','FIT']].sum()
print(f"1月: 损益={t1['损益金额']/1000:.0f}  WX={t1['其中WX']/1000:.0f}  FIT={t1['FIT']/1000:.0f}")
print(f"2月: 损益={t2['损益金额']/1000:.0f}  WX={t2['其中WX']/1000:.0f}  FIT={t2['FIT']/1000:.0f}")
