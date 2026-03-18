# -*- coding: utf-8 -*-
"""Reverse engineer v6: 检查是否存在单位转换差异，以及扩大搜索范围"""
import sys, os, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pnl-analysis'))

import pandas as pd
import numpy as np
from data_loader import load_csv, calc_derived_fields

data_dir = os.path.join(os.path.dirname(__file__), 'ddd', '20260310151934', 'data')
df1 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260131.csv')))
df2 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260228.csv')))

def to_k(v):
    return round(v / 1000)

# 截图 (千元)
S = {
    '跨境收单': (1173, 703), '汇款互联': (532, 534), '留学缴费': (503, 169),
    '企业外汇-境内购汇': (3738, 4063), '企业外汇-境外账户': (443, 226),
    '企业外汇-基础通道': (423, 192), '企业外汇小计': (4603, 4481),
    '业务侧小计': (5777, 5184), '平台侧汇兑损益': (-1300, 10824),
    '税后汇兑损益': (4477, 16008), '跨境收单损益': (17744, -24274),
    'WXG侧损益': (22250, -33462), 'FIT侧损益': (-1521, 9188),
    '平台(不含跨境FIT)': (1723, 1636),
}

print("=" * 90)
print("方法: 尝试按币种/商户号等更细维度拆分")
print("=" * 90)

# 先看看数据里面有哪些独特值
print("\n所有列:", list(df1.columns))
print(f"商户号(1月唯一值): {sorted(df1['商户号'].unique())}")
print(f"原币种(1月唯一值): {sorted(df1['原币种'].unique())}")
print(f"商户类型(1月唯一值): {sorted(df1['商户类型'].unique())}")

# 截图能精确匹配互联汇款(532)和纯汇兑(423), 说明CSV/1000的千元精度是对的
# 但跨境收单之类不匹配, 可能是因为截图用了不同的分类维度

# 新思路: 截图的"跨境收单" 可能是按某个特定维度过滤的
# 也许是按"商户号"? 不同商户号对应不同的业务线?

print("\n" + "=" * 90)
print("看看1月 所属业务=跨境收单 的商户号分布")
print("=" * 90)

for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n--- {label} ---")
    ks = df[df['所属业务'] == '跨境收单']
    ks_detail = ks.groupby(['损益实际归属主体', '商户号', '原币种']).agg(
        损益=('损益金额', 'sum'),
    ).reset_index()
    ks_detail['千元'] = ks_detail['损益'].apply(to_k)
    ks_by_mch = ks.groupby(['损益实际归属主体', '商户号'])['损益金额'].sum().reset_index()
    ks_by_mch['千元'] = ks_by_mch['损益金额'].apply(to_k)
    ks_by_mch = ks_by_mch.sort_values('千元', ascending=False)
    
    for _, r in ks_by_mch.iterrows():
        print(f"  {r['损益实际归属主体']:10s} 商户号={r['商户号']:6s} 千元={r['千元']:>8,}")
    print(f"  总计: {to_k(ks['损益金额'].sum())}")

print("\n" + "=" * 90)
print("截图 '跨境收单'=1173 — 也许排除了某些商户号?")
print("=" * 90)

# 1月跨境收单(损益户)有3个渠道:
# WPHK商户1001=14156, MSO商户1005=1847, CFT商户1002=-927
# 总计=15076
# 截图=1173
# 15076-1173=13903 ≈ WPHK(14156)? 差253
# 如果排除WPHK: MSO+CFT=1847-927=920 ≠ 1173
# 如果排除CFT: MSO+WPHK=1847+14156=16003 ≠ 1173

# 等一下... 也许截图看的不是"所属业务"而是完全不同的分类

# 让我看看按商户号汇总所有业务
print("\n1月 按商户号汇总(千元, 前20):")
by_mch1 = df1.groupby('商户号').agg(
    损益千元=('损益金额', lambda x: to_k(x.sum())),
    业务=('所属业务', 'first'),
    渠道=('损益实际归属主体', 'first'),
    商户类型=('商户类型', 'first'),
    行数=('损益金额', 'count'),
).reset_index()
by_mch1 = by_mch1.sort_values('损益千元', ascending=False)
for _, r in by_mch1.iterrows():
    if abs(r['损益千元']) >= 1:
        print(f"  商户号={r['商户号']:6s} {r['渠道']:10s} {r['业务']:12s} {r['商户类型']:8s} {r['损益千元']:>8,} ({r['行数']}行)")

print("\n" + "=" * 90)
print("关键测试: 截图可能使用FIT而非损益金额!")
print("=" * 90)

# FIT = 损益金额 - 其中WX
# 对于大部分项来说 FIT ≈ 损益金额（因为WX很小）
# 但某些项可能不同

# 同样用穷举搜索 FIT 版本
from itertools import combinations

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    atoms = df.groupby(['损益实际归属主体', '所属业务', '商户类型']).agg(
        FIT千元=('FIT', lambda x: to_k(x.sum())),
    ).reset_index()
    atoms = atoms[atoms['FIT千元'].abs() >= 1].reset_index(drop=True)
    
    print(f"\nFIT原子单元 ({len(atoms)}个):")
    for i, r in atoms.iterrows():
        lbl = f"{r['损益实际归属主体']}/{r['所属业务']}/{r['商户类型']}"
        print(f"  [{i:2d}] {lbl:45s} FIT={r['FIT千元']:>8,}")
    
    vals = list(atoms['FIT千元'])
    n = len(vals)
    
    # 搜索各个目标
    for target_name in ['跨境收单', '留学缴费', '企业外汇-境内购汇', '企业外汇-境外账户', '业务侧小计', '平台侧汇兑损益']:
        target_val = S[target_name][m_idx]
        found = []
        
        for size in range(1, min(7, n+1)):
            if len(found) >= 5:
                break
            for combo in combinations(range(n), size):
                s = sum(vals[idx] for idx in combo)
                if abs(s - target_val) <= 5:
                    parts = [f"{atoms.loc[idx,'所属业务']}@{atoms.loc[idx,'损益实际归属主体']}/{atoms.loc[idx,'商户类型']}({vals[idx]})" for idx in combo]
                    found.append((size, ' + '.join(parts), s))
        
        if found:
            print(f"\n  搜索 {target_name}(FIT)={target_val}:")
            for size, desc, total in found[:5]:
                print(f"    [{size}项] {desc} = {total}")
        else:
            print(f"\n  搜索 {target_name}(FIT)={target_val}: (无匹配)")

print("\n" + "=" * 90)
print("最终假设: 也许截图的粒度在币种级别 (需要按币种拆开)")
print("=" * 90)

# 也许截图的"跨境收单"只包含某些币种?
for label, df in [("1月", df1)]:
    print(f"\n--- {label} ---")
    
    # MSO 跨境收单(损益户) 按币种
    mso_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO')]
    mso_ks_by_ccy = mso_ks.groupby('原币种')['损益金额'].sum().sort_values(ascending=False)
    print(f"\n  MSO跨境收单 按币种 (总计{to_k(mso_ks['损益金额'].sum())}千):")
    cum = 0
    for ccy, v in mso_ks_by_ccy.items():
        vk = to_k(v)
        cum += vk
        if abs(vk) >= 1:
            print(f"    {ccy:5s}: {vk:>6,}  累计: {cum:>8,}")
    
    # WPHK跨境收单 按币种
    wphk_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT-WPHK')]
    wphk_ks_by_ccy = wphk_ks.groupby('原币种')['损益金额'].sum().sort_values(ascending=False)
    print(f"\n  WPHK跨境收单 按币种 (总计{to_k(wphk_ks['损益金额'].sum())}千):")
    for ccy, v in wphk_ks_by_ccy.items():
        vk = to_k(v)
        if abs(vk) >= 1:
            print(f"    {ccy:5s}: {vk:>6,}")
    
    # CFT跨境收单 按币种
    cft_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT')]
    cft_ks_by_ccy = cft_ks.groupby('原币种')['损益金额'].sum().sort_values(ascending=False)
    print(f"\n  CFT跨境收单 按币种 (总计{to_k(cft_ks['损益金额'].sum())}千):")
    for ccy, v in cft_ks_by_ccy.items():
        vk = to_k(v)
        if abs(vk) >= 1:
            print(f"    {ccy:5s}: {vk:>6,}")

print("\n" + "=" * 90)
print("最后手段: 把1月所有币种级别的明细列出来, 手动检视")
print("=" * 90)

for label, df in [("1月", df1)]:
    # 按 渠道×业务×商户类型×商户号 的汇总
    detail = df.groupby(['损益实际归属主体', '所属业务', '商户类型', '商户号']).agg(
        损益=('损益金额', 'sum'),
        FIT=('FIT', 'sum'),
        行数=('损益金额', 'count'),
        币种数=('原币种', 'nunique'),
    ).reset_index()
    detail['千元'] = detail['损益'].apply(to_k)
    detail['FIT千'] = detail['FIT'].apply(to_k)
    detail = detail.sort_values('千元', ascending=False)
    
    print(f"\n1月 所有商户号汇总 (|千元|>=1):")
    for _, r in detail.iterrows():
        if abs(r['千元']) >= 1:
            print(f"  {r['损益实际归属主体']:10s} {r['所属业务']:12s} {r['商户类型']:8s} 商户={r['商户号']:6s} 损益={r['千元']:>7,} FIT={r['FIT千']:>7,} ({r['行数']}行,{r['币种数']}币种)")

# 现在让我算一下: 不含垫资余额的损益?
# 也许截图排除了垫资部分?
print("\n" + "=" * 90)
print("检查: 垫资 vs 非垫资")
print("=" * 90)

for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n--- {label} ---")
    # 有垫资余额的记录
    has_dz = df[(df['期初垫资余额'] != 0) | (df['期末垫资余额'] != 0)]
    no_dz = df[(df['期初垫资余额'] == 0) & (df['期末垫资余额'] == 0)]
    
    print(f"  有垫资: {len(has_dz)}行 损益={to_k(has_dz['损益金额'].sum())}千")
    print(f"  无垫资: {len(no_dz)}行 损益={to_k(no_dz['损益金额'].sum())}千")
    
    # 按业务看垫资分布
    dz_by_biz = has_dz.groupby('所属业务')['损益金额'].sum()
    for biz, v in dz_by_biz.items():
        if abs(v) >= 1000:
            print(f"    有垫资-{biz}: {to_k(v)}千")
    
    # 1月 跨境收单(无垫资部分)
    ks_no_dz = df[(df['所属业务'] == '跨境收单') & (df['期初垫资余额'] == 0) & (df['期末垫资余额'] == 0)]
    ks_has_dz = df[(df['所属业务'] == '跨境收单') & ((df['期初垫资余额'] != 0) | (df['期末垫资余额'] != 0))]
    print(f"  跨境收单(无垫资): {to_k(ks_no_dz['损益金额'].sum())}千 ({len(ks_no_dz)}行)")
    print(f"  跨境收单(有垫资): {to_k(ks_has_dz['损益金额'].sum())}千 ({len(ks_has_dz)}行)")
    
    # 出境机酒(无垫资)
    cj_no_dz = df[(df['所属业务'] == '出境机酒') & (df['期初垫资余额'] == 0) & (df['期末垫资余额'] == 0)]
    cj_has_dz = df[(df['所属业务'] == '出境机酒') & ((df['期初垫资余额'] != 0) | (df['期末垫资余额'] != 0))]
    print(f"  出境机酒(无垫资): {to_k(cj_no_dz['损益金额'].sum())}千 ({len(cj_no_dz)}行)")
    print(f"  出境机酒(有垫资): {to_k(cj_has_dz['损益金额'].sum())}千 ({len(cj_has_dz)}行)")

# 最后看看: 截图的业务侧小计 = 5777
# 业务侧各项 = 1173+532+0+503+4603 = 6811
# 差 = 5777 - 6811 = -1034
# 也许有一个隐藏行叫"出境通" 或者某种扣除?
# 或者 "跨境收单" 在截图中并不是1173而是 1173-1034=139?
# 不太对... 

# 等等, 也许截图上面还有我没看到的行?
# 比如 "其他" = -1034?
# 或者截图中的某些行实际包含了负值调整

# 另一种可能: 截图的"跨境收单"实际上不包含融合业务的跨境收单
# 而融合的跨境收单被归入了另一个分类
# 这样业务侧可能还包含一行 "融合" = -1034?

print("\n" + "=" * 90)
print("验证: 如果业务侧有一个隐藏的'其他/融合'行")
print("=" * 90)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n--- {label} ---")
    hidden = S['业务侧小计'][m_idx] - (S['跨境收单'][m_idx] + S['汇款互联'][m_idx] + S['港股汇款'][m_idx] + S['留学缴费'][m_idx] + S['企业外汇小计'][m_idx])
    print(f"  隐藏行 = {hidden}")
    
    # 看看有什么组合 = hidden
    atoms = df.groupby(['损益实际归属主体', '所属业务', '商户类型'])['损益金额'].sum().reset_index()
    atoms['千元'] = atoms['损益金额'].apply(to_k)
    atoms = atoms[atoms['千元'].abs() >= 1].reset_index(drop=True)
    vals = list(atoms['千元'])
    n = len(vals)
    
    print(f"  搜索隐藏行={hidden} (±5):")
    for size in range(1, 4):
        for combo in combinations(range(n), size):
            s = sum(vals[idx] for idx in combo)
            if abs(s - hidden) <= 5:
                parts = [f"{atoms.loc[idx,'所属业务']}@{atoms.loc[idx,'损益实际归属主体']}/{atoms.loc[idx,'商户类型']}({vals[idx]})" for idx in combo]
                print(f"    [{size}项] {' + '.join(parts)} = {s}")
