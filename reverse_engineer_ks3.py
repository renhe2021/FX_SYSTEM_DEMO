# -*- coding: utf-8 -*-
"""
关键线索追踪:
1. WXG/FIT 不是CSV的"其中WX"/"FIT" → 那WXG是什么?
2. 截图合计 ≠ CSV全量 → 截图有额外数据?
3. 聚焦FIT列: 也许截图用的是FIT列而非损益金额?
"""
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

def K(v): return round(v / 1000)

biz_set = ['跨境收单', '融合一期', '融合三期', 'SVF平台']

# ===================================================================
# 核心发现: WXG ≈ 20766千 但 CSV的WX ≈ -3千 
# 说明截图的"WXG"和"FIT"不是我们的衍生字段
# 那WXG和FIT是什么含义?
#
# 截图:
#   跨境收单损益 = WXG + FIT侧
#   17744 = 20766 + (-3023)  ← 1月
#  -24274 = -33462 + 9188    ← 2月
#
# 也许WXG/FIT是按渠道归属分的?
# WXG = WPHK归属? FIT = CFT归属?
# ===================================================================

print("=" * 90)
print("假设1: WXG = WPHK归属, FIT = CFT归属 (在跨境收单损益范围内)")
print("=" * 90)

for label, df, scr_wxg, scr_fit, scr_ks in [("1月", df1, 20766, -3023, 17744), ("2月", df2, -33462, 9188, -24274)]:
    ks = df[df['所属业务'].isin(biz_set)]
    wphk = K(ks[ks['损益实际归属主体'] == 'CFT-WPHK']['损益金额'].sum())
    cft = K(ks[ks['损益实际归属主体'] == 'CFT']['损益金额'].sum())
    mso = K(ks[ks['损益实际归属主体'] == 'MSO']['损益金额'].sum())
    mpi = K(ks[ks['损益实际归属主体'] == 'MPI']['损益金额'].sum())
    
    print(f"\n  {label} 跨境收单损益范围内:")
    print(f"    WPHK  = {wphk:>7,}千  (截图WXG = {scr_wxg}千)  差={wphk-scr_wxg}")
    print(f"    CFT   = {cft:>7,}千  (截图FIT = {scr_fit}千)  差={cft-scr_fit}")
    print(f"    MSO   = {mso:>7,}千")
    print(f"    MPI   = {mpi:>7,}千")
    print(f"    WPHK+MSO = {wphk+mso:>7,}千  vs 截图WXG={scr_wxg}")
    print(f"    CFT      = {cft:>7,}千  vs 截图FIT={scr_fit}")
    print(f"    差(WPHK+MSO-WXG)={wphk+mso-scr_wxg}")

# WPHK ≈ 19806(1月), 截图WXG=20766 → 差960
# 不太match...

print("\n\n" + "=" * 90)
print("假设2: 也许截图看的不是'损益金额'而是原始的'折算CNY损益金额/100'(都是元)")
print("  或者截图看的是另一列? 看看期初/期末余额变化")
print("=" * 90)

for label, df, scr_wxg, scr_fit in [("1月", df1, 20766, -3023), ("2月", df2, -33462, 9188)]:
    ks = df[df['所属业务'].isin(biz_set)]
    
    # 各种字段的千元值
    pnl = K(ks['损益金额'].sum())
    bal_change = K((ks['期末余额_元'] - ks['期初余额_元']).sum())
    adv_change = K((ks['期末垫资余额_元'] - ks['期初垫资余额_元']).sum())
    
    print(f"\n  {label}:")
    print(f"    损益金额         = {pnl:>10,}千")
    print(f"    期末-期初余额     = {bal_change:>10,}千")
    print(f"    期末-期初垫资余额  = {adv_change:>10,}千")
    print(f"    截图WXG+FIT       = {scr_wxg+scr_fit:>10,}千")

print("\n\n" + "=" * 90)
print("假设3: WXG = '非白名单'的某种计算, FIT = 余下")
print("  但WX只有-3千/204千, 而WXG=20766千, 不match")
print("  除非WXG的含义是'WeiXin Group'(微信集团)侧?")
print("  FIT = Financial Institution Technology?")
print("=" * 90)

# 也许 WXG = WeiXin Group 的账户, FIT = 第三方/外部
# 按商户号/商户类型来分?
for label, df, scr_wxg, scr_fit in [("1月", df1, 20766, -3023), ("2月", df2, -33462, 9188)]:
    ks = df[df['所属业务'].isin(biz_set)]
    
    # 按商户号分组
    by_merchant = ks.groupby('商户号')['损益金额'].sum().sort_values(ascending=False)
    print(f"\n  {label} 跨境收单损益范围 — 按商户号:")
    for m, v in by_merchant.items():
        if abs(K(v)) >= 10:
            print(f"    商户号={m}: {K(v):>7,}千")
    
    # 商户号1001 vs 其他
    m1001 = K(ks[ks['商户号'] == '1001']['损益金额'].sum())
    m_other = K(ks[ks['商户号'] != '1001']['损益金额'].sum())
    print(f"    商户号=1001: {m1001:>7,}千")
    print(f"    商户号≠1001: {m_other:>7,}千")
    print(f"    截图WXG={scr_wxg}, FIT={scr_fit}")

print("\n\n" + "=" * 90)
print("假设4: WXG/FIT拆分 = 垫资 vs 非垫资?")
print("=" * 90)

for label, df, scr_wxg, scr_fit in [("1月", df1, 20766, -3023), ("2月", df2, -33462, 9188)]:
    ks = df[df['所属业务'].isin(biz_set)]
    
    # 垫资余额 > 0 的为垫资户
    has_adv = ks[(ks['期初垫资余额_元'].abs() > 0) | (ks['期末垫资余额_元'].abs() > 0)]
    no_adv = ks[(ks['期初垫资余额_元'].abs() == 0) & (ks['期末垫资余额_元'].abs() == 0)]
    
    print(f"\n  {label}:")
    print(f"    有垫资: {K(has_adv['损益金额'].sum()):>7,}千")
    print(f"    无垫资: {K(no_adv['损益金额'].sum()):>7,}千")
    print(f"    截图WXG={scr_wxg}, FIT={scr_fit}")

print("\n\n" + "=" * 90)
print("假设5: WXG/FIT = 按主体+业务的交叉分组")
print("=" * 90)

# 也许截图中的WXG包含了截图中其他行(税后)中WPHK部分?
for label, df, scr_wxg, scr_fit, scr_tax, scr_ks in [("1月", df1, 20766, -3023, 4477, 17744), ("2月", df2, -33462, 9188, 16008, -24274)]:
    print(f"\n  {label}:")
    
    # 全量中 WPHK 的全部
    wphk_all = K(df[df['损益实际归属主体'] == 'CFT-WPHK']['损益金额'].sum())
    cft_all = K(df[df['损益实际归属主体'] == 'CFT']['损益金额'].sum())
    
    print(f"    全量WPHK = {wphk_all}千  (截图WXG={scr_wxg})")
    print(f"    全量CFT  = {cft_all}千  (截图FIT={scr_fit})")
    
    # 如果WXG = 全量WPHK, FIT = 全量CFT:
    print(f"    WPHK+CFT = {wphk_all+cft_all}千  (截图跨境收单损益={scr_ks})")
    # WPHK=19806 ≠ WXG=20766, 差960

print("\n\n" + "=" * 90)
print("假设6: 截图的数据可能包含额外的'对冲'或'已实现'数据")
print("  截图合计(税后+跨境收单损益) 与 CSV全量 的差异分析")
print("=" * 90)

for label, df, scr_ks, scr_tax in [("1月", df1, 17744, 4477), ("2月", df2, -24274, 16008)]:
    total = K(df['损益金额'].sum())
    scr_total = scr_ks + scr_tax
    diff = scr_total - total
    print(f"\n  {label}:")
    print(f"    CSV全量              = {total:>10,}千")
    print(f"    截图合计(税后+KS)    = {scr_total:>10,}千")
    print(f"    差(截图-CSV)         = {diff:>10,}千")
    print(f"    也许截图多了(或少了)这些: {diff}千")
    
    # 如果截图有额外数据, 差应该 > 0
    # 1月: 22221-25566 = -3345 → 截图比CSV少3345千
    # 2月: -8266-(-18132) = 9866 → 截图比CSV多9866千
    # 差异大且方向不同... 不像是固定的额外数据集

# ===================================================================
# 也许整个思路需要反转：
# 也许税后不是"全量减去跨境收单损益"
# 而是截图的报表有两个独立的数据区：
#   区A: 税后(业务侧+平台侧) — 某个数据子集
#   区B: 跨境收单损益(WXG+FIT) — 另一个数据子集
# 两个区可能有重叠、也可能没有!
# ===================================================================
print("\n\n" + "=" * 90)
print("关键假设7: 税后和跨境收单损益是独立的报表区域,不一定互补!")
print("=" * 90)

# 税后 = 业务侧 + 平台侧
# 业务侧包含: 跨境汇款(1173), 互联汇款(532), 留学缴费(641), 
#             企业外汇-境内(3738), 境外(443), 隐藏行(-1172)
# 平台侧包含: 平台不含FiT(1723) + FIT(-3023) = -1300

# 税后合计: 4477千(1月)
# 如果只看MSO渠道:
for label, df, scr_tax in [("1月", df1, 4477), ("2月", df2, 16008)]:
    print(f"\n  {label}:")
    
    # 排列组合不同渠道
    entities = df['损益实际归属主体'].unique()
    for ent in sorted(entities):
        sub = df[df['损益实际归属主体'] == ent]
        # 按所属业务看
        for biz in sorted(sub['所属业务'].unique()):
            biz_sub = sub[sub['所属业务'] == biz]
            v = K(biz_sub['损益金额'].sum())
            if abs(v) >= 1:
                print(f"    {ent:10s} × {biz:12s}: {v:>7,}千")
    print(f"\n    截图税后 = {scr_tax}千")

# ===================================================================
# 穷举: 哪些(渠道×业务)组合加起来=截图税后?
# ===================================================================
print("\n\n" + "=" * 90)
print("穷举: 寻找组合 → 税后=4477千(1月)")
print("=" * 90)

from itertools import combinations

# 1月的原子项 (渠道×业务)
atoms = df1.groupby(['损益实际归属主体','所属业务'])['损益金额'].sum()
atoms_list = [(idx, K(val)) for idx, val in atoms.items() if abs(K(val)) >= 1]
print(f"  非零(≥1千)原子项: {len(atoms_list)}个")
for idx, val in atoms_list:
    print(f"    {idx[0]:10s} × {idx[1]:12s}: {val:>7,}千")

target = 4477
print(f"\n  目标: 税后 = {target}千")
print(f"  搜索1-{len(atoms_list)}项组合...")

found = []
for size in range(1, len(atoms_list)+1):
    for combo in combinations(range(len(atoms_list)), size):
        s = sum(atoms_list[i][1] for i in combo)
        if abs(s - target) <= 2:  # 允许±2千的误差(四舍五入)
            found.append((size, combo, s))
    if found:
        break  # 找到最小组合就停

if found:
    print(f"  找到 {len(found)} 个组合:")
    for size, combo, s in found[:15]:
        names = [f"{atoms_list[i][0][0]}×{atoms_list[i][0][1]}({atoms_list[i][1]})" for i in combo]
        print(f"    [{size}项] sum={s}: {', '.join(names)}")
else:
    print("  未找到精确组合, 扩大搜索范围 ±50千...")
    for size in range(1, min(len(atoms_list)+1, 8)):
        for combo in combinations(range(len(atoms_list)), size):
            s = sum(atoms_list[i][1] for i in combo)
            if abs(s - target) <= 50:
                found.append((size, combo, s))
        if len(found) > 20:
            break
    
    if found:
        found.sort(key=lambda x: (abs(x[2] - target), x[0]))
        print(f"  找到 {len(found)} 个近似组合 (±50千):")
        for size, combo, s in found[:15]:
            names = [f"{atoms_list[i][0][0]}×{atoms_list[i][0][1]}({atoms_list[i][1]})" for i in combo]
            print(f"    [{size}项] sum={s} (差{s-target}): {', '.join(names)}")

# 同时验证2月
print(f"\n  对找到的组合验证2月...")
atoms2 = df2.groupby(['损益实际归属主体','所属业务'])['损益金额'].sum()
atoms2_dict = {idx: K(val) for idx, val in atoms2.items()}

if found:
    for size, combo, s in found[:5]:
        keys = [atoms_list[i][0] for i in combo]
        s2 = sum(atoms2_dict.get(k, 0) for k in keys)
        names = [f"{k[0]}×{k[1]}" for k in keys]
        match_str = "✅" if abs(s2 - 16008) <= 2 else f"❌差{s2-16008}"
        print(f"    {', '.join(names)}: 1月={s}, 2月={s2} (截图16008) {match_str}")
